package com.pulsecart.backend;

import com.pulsecart.backend.dto.CreateOrderRequest;
import com.pulsecart.backend.dto.OrderDto;
import com.pulsecart.backend.dto.OrderItemRequest;
import com.pulsecart.backend.entity.*;
import com.pulsecart.backend.exception.InsufficientStockException;
import com.pulsecart.backend.exception.InvalidOrderStateException;
import com.pulsecart.backend.exception.UnauthorizedAccessException;
import com.pulsecart.backend.repository.IdempotencyRecordRepository;
import com.pulsecart.backend.repository.InventoryRepository;
import com.pulsecart.backend.repository.OrderRepository;
import com.pulsecart.backend.repository.ProductRepository;
import com.pulsecart.backend.repository.UserRepository;
import com.pulsecart.backend.service.OrderService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
public class OrderServiceIntegrationTest {

    @Autowired
    private OrderService orderService;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private ProductRepository productRepository;

    @Autowired
    private InventoryRepository inventoryRepository;

    @Autowired
    private OrderRepository orderRepository;

    @Autowired
    private IdempotencyRecordRepository idempotencyRecordRepository;

    private User customerA;
    private User customerB;
    private Product testProduct;
    private Product scarceProduct;

    @BeforeEach
    void setUp() {
        idempotencyRecordRepository.deleteAll();
        orderRepository.deleteAll();

        customerA = userRepository.findByEmail("customer-a@example.com")
                .orElseGet(() -> userRepository.save(new User("customer-a@example.com", "hash", "Cust", "A", Role.ROLE_CUSTOMER)));

        customerB = userRepository.findByEmail("customer-b@example.com")
                .orElseGet(() -> userRepository.save(new User("customer-b@example.com", "hash", "Cust", "B", Role.ROLE_CUSTOMER)));

        testProduct = productRepository.findBySku("TEST-SKU-100").orElseGet(() -> {
            Product p = new Product("TEST-SKU-100", "Wireless Mouse", "Tech", "Electronics", new BigDecimal("50.00"), new BigDecimal("25.00"), ProductStatus.ACTIVE);
            Inventory inv = new Inventory(p, 20);
            p.setInventory(inv);
            return productRepository.save(p);
        });

        // Reset stock to 20
        Inventory testInv = inventoryRepository.findByProductId(testProduct.getId()).orElseThrow();
        testInv.setStock(20);
        inventoryRepository.save(testInv);

        scarceProduct = productRepository.findBySku("TEST-SKU-SCARCE").orElseGet(() -> {
            Product p = new Product("TEST-SKU-SCARCE", "Limited Edition GPU", "Tech", "Electronics", new BigDecimal("999.00"), new BigDecimal("500.00"), ProductStatus.ACTIVE);
            Inventory inv = new Inventory(p, 1);
            p.setInventory(inv);
            return productRepository.save(p);
        });

        // Reset scarce product stock to 1
        Inventory scarceInv = inventoryRepository.findByProductId(scarceProduct.getId()).orElseThrow();
        scarceInv.setStock(1);
        inventoryRepository.save(scarceInv);
    }

    @Test
    @DisplayName("1. Successful Order Creation: preserves price snapshot, calculates totals, decrements stock")
    void testSuccessfulOrderCreation() {
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 2)),
                "CREDIT_CARD"
        );

        OrderDto order = orderService.createOrder(customerA, request, null);

        assertNotNull(order.id());
        assertNotNull(order.orderNumber());
        assertEquals(OrderStatus.CONFIRMED, order.status());
        // 2 items * $50.00 = $100.00 subtotal
        assertEquals(new BigDecimal("100.00"), order.subtotal());
        // Tax 8% = $8.00
        assertEquals(new BigDecimal("8.00"), order.taxAmount());
        // Shipping free >= $100.00 = $0.00
        assertEquals(new BigDecimal("0.00"), order.shippingFee());
        // Total = $108.00
        assertEquals(new BigDecimal("108.00"), order.totalAmount());

        // Price snapshot verified
        assertEquals(1, order.items().size());
        assertEquals(new BigDecimal("50.00"), order.items().get(0).unitPrice());
        assertEquals(2, order.items().get(0).quantity());

        // Inventory stock decremented from 20 to 18
        Inventory updatedInv = inventoryRepository.findByProductId(testProduct.getId()).orElseThrow();
        assertEquals(18, updatedInv.getStock());
    }

    @Test
    @DisplayName("2. Insufficient Stock: rolls back transaction, stock remains unchanged, no order created")
    void testInsufficientStockRejectionAndRollback() {
        int initialOrderCount = orderRepository.findAll().size();
        Inventory invBefore = inventoryRepository.findByProductId(testProduct.getId()).orElseThrow();
        int stockBefore = invBefore.getStock();

        // Request 100 items when only 20 are available
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 100)),
                "CREDIT_CARD"
        );

        assertThrows(InsufficientStockException.class, () ->
                orderService.createOrder(customerA, request, null)
        );

        // Verify stock is preserved (rollback)
        Inventory invAfter = inventoryRepository.findByProductId(testProduct.getId()).orElseThrow();
        assertEquals(stockBefore, invAfter.getStock());

        // Verify no order was committed
        assertEquals(initialOrderCount, orderRepository.findAll().size());
    }

    @Test
    @DisplayName("3. Concurrency Stress Test: 10 simultaneous threads competing for 1 last item -> exactly 1 succeeds, 9 fail, stock ends at 0 (NO overselling)")
    void testSimultaneousPurchasesOfLastItemPreventOverselling() throws InterruptedException {
        int threadCount = 10;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch readyLatch = new CountDownLatch(threadCount);
        CountDownLatch startLatch = new CountDownLatch(1);

        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failureCount = new AtomicInteger(0);
        List<Exception> errors = Collections.synchronizedList(new ArrayList<>());

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                readyLatch.countDown();
                try {
                    startLatch.await(); // Synchronize all threads to fire simultaneously
                    CreateOrderRequest request = new CreateOrderRequest(
                            List.of(new OrderItemRequest(scarceProduct.getId(), 1)),
                            "CREDIT_CARD"
                    );
                    orderService.createOrder(customerA, request, null);
                    successCount.incrementAndGet();
                } catch (InsufficientStockException e) {
                    failureCount.incrementAndGet();
                } catch (Exception e) {
                    errors.add(e);
                }
            });
        }

        readyLatch.await(5, TimeUnit.SECONDS);
        startLatch.countDown(); // Release the hounds!
        executor.shutdown();
        assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS));

        // Strict Concurrency Invariants
        assertEquals(1, successCount.get(), "Exactly one purchase must succeed for the single available item");
        assertEquals(9, failureCount.get(), "Exactly 9 threads must be rejected due to insufficient stock");
        assertTrue(errors.isEmpty(), "No unexpected errors should occur: " + errors);

        // Final inventory check: stock must be exactly 0, never negative
        Inventory scarceInv = inventoryRepository.findByProductId(scarceProduct.getId()).orElseThrow();
        assertEquals(0, scarceInv.getStock(), "Inventory stock must be exactly 0 (no overselling)");
    }

    @Test
    @DisplayName("4. Idempotency Key Handling: safe retry returns original order without double-charging or re-debiting stock")
    void testDuplicateRequestHandlingWithIdempotencyKey() {
        String idempotencyKey = "IDEMP-" + UUID.randomUUID();
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 2)),
                "CREDIT_CARD"
        );

        // First attempt
        OrderDto firstOrder = orderService.createOrder(customerA, request, idempotencyKey);
        assertNotNull(firstOrder);
        assertEquals(18, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock());

        // Duplicate retry with exact same idempotency key
        OrderDto secondOrder = orderService.createOrder(customerA, request, idempotencyKey);

        // Verify identical response returned
        assertEquals(firstOrder.id(), secondOrder.id());
        assertEquals(firstOrder.orderNumber(), secondOrder.orderNumber());
        assertEquals(firstOrder.totalAmount(), secondOrder.totalAmount());

        // CRITICAL: Stock must NOT be deducted a second time (must remain 18, not 16)
        assertEquals(18, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock());
    }

    @Test
    @DisplayName("5. Order Cancellation: restores inventory exactly once, subsequent cancellation rejected")
    void testOrderCancellationRestoresInventoryExactlyOnce() {
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 3)),
                "CREDIT_CARD"
        );

        OrderDto order = orderService.createOrder(customerA, request, null);
        assertEquals(17, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock());

        // Cancel order
        OrderDto cancelled = orderService.cancelOrder(customerA, order.id());
        assertEquals(OrderStatus.CANCELLED, cancelled.status());

        // Stock restored from 17 back to 20
        assertEquals(20, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock());

        // Second cancellation attempt must be rejected
        assertThrows(InvalidOrderStateException.class, () ->
                orderService.cancelOrder(customerA, order.id())
        );

        // Stock must not be restored twice
        assertEquals(20, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock());
    }

    @Test
    @DisplayName("6. Multi-Tenant Authorization: Customer B cannot view or cancel Customer A's order")
    void testAccessToAnotherCustomersOrdersForbidden() {
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 1)),
                "CREDIT_CARD"
        );
        OrderDto orderA = orderService.createOrder(customerA, request, null);

        // Customer B attempts to read Customer A's order -> 403 Forbidden
        assertThrows(UnauthorizedAccessException.class, () ->
                orderService.getOrderById(customerB, orderA.id())
        );

        // Customer B attempts to cancel Customer A's order -> 403 Forbidden
        assertThrows(UnauthorizedAccessException.class, () ->
                orderService.cancelOrder(customerB, orderA.id())
        );
    }

    @Test
    @DisplayName("7. Simultaneous Cancellation Stress Test: 10 concurrent threads attempting to cancel the same order -> exactly 1 succeeds, stock restored EXACTLY ONCE")
    void testSimultaneousOrderCancellationRestoresInventoryExactlyOnce() throws InterruptedException {
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 2)),
                "CREDIT_CARD"
        );
        OrderDto order = orderService.createOrder(customerA, request, null);
        assertEquals(18, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock());

        int threadCount = 10;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch readyLatch = new CountDownLatch(threadCount);
        CountDownLatch startLatch = new CountDownLatch(1);

        AtomicInteger successCount = new AtomicInteger(0);
        AtomicInteger failureCount = new AtomicInteger(0);
        List<Exception> errors = Collections.synchronizedList(new ArrayList<>());

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                readyLatch.countDown();
                try {
                    startLatch.await();
                    orderService.cancelOrder(customerA, order.id());
                    successCount.incrementAndGet();
                } catch (InvalidOrderStateException e) {
                    failureCount.incrementAndGet();
                } catch (Exception e) {
                    errors.add(e);
                }
            });
        }

        readyLatch.await(5, TimeUnit.SECONDS);
        startLatch.countDown();
        executor.shutdown();
        assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS));

        // Strict Concurrency Invariants
        assertEquals(1, successCount.get(), "Exactly one cancellation transaction must succeed");
        assertEquals(9, failureCount.get(), "Exactly 9 concurrent cancellation attempts must be rejected");
        assertTrue(errors.isEmpty(), "No unexpected errors should occur: " + errors);

        // Inventory check: stock was 18, must be restored by +2 to exactly 20 (NEVER double-restored to 22, 24, etc.)
        Inventory updatedInv = inventoryRepository.findByProductId(testProduct.getId()).orElseThrow();
        assertEquals(20, updatedInv.getStock(), "Stock must be restored exactly once (20), no double restoration");
    }

    @Test
    @DisplayName("8. Idempotency Payload Validation: reusing key with a different request payload is strictly rejected")
    void testIdempotencyKeyReuseWithDifferentPayloadRejected() {
        String idempotencyKey = "IDEMP-PAYLOAD-" + UUID.randomUUID();
        CreateOrderRequest req1 = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 1)),
                "CREDIT_CARD"
        );
        CreateOrderRequest req2 = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 5)),
                "CREDIT_CARD"
        );

        // First order with payload 1 succeeds
        OrderDto order1 = orderService.createOrder(customerA, req1, idempotencyKey);
        assertNotNull(order1);

        // Reusing the same key with different payload 2 must be rejected
        IllegalArgumentException ex = assertThrows(IllegalArgumentException.class, () ->
                orderService.createOrder(customerA, req2, idempotencyKey)
        );
        assertTrue(ex.getMessage().contains("different request payload"));
    }

    @Test
    @DisplayName("9. Customer-Scoped Idempotency: distinct customers can safely use identical key strings without collision")
    void testIdempotencyKeyScopedToCustomer() {
        String commonKey = "SHARED-KEY-" + UUID.randomUUID();
        CreateOrderRequest reqA = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 1)),
                "CREDIT_CARD"
        );
        CreateOrderRequest reqB = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 1)),
                "CREDIT_CARD"
        );

        // Customer A uses the key
        OrderDto orderA = orderService.createOrder(customerA, reqA, commonKey);
        // Customer B uses the identical key string -> must succeed independently
        OrderDto orderB = orderService.createOrder(customerB, reqB, commonKey);

        assertNotNull(orderA);
        assertNotNull(orderB);
        assertNotEquals(orderA.id(), orderB.id(), "Customer A and Customer B must have distinct orders");
        assertEquals(customerA.getId(), orderA.userId());
        assertEquals(customerB.getId(), orderB.userId());
    }

    @Test
    @DisplayName("10. Simultaneous Duplicate Requests: concurrent checkout clicks with identical key deduplicate safely")
    void testSimultaneousDuplicateRequestsSafeDeduplication() throws InterruptedException {
        String idempotencyKey = "IDEMP-RACE-" + UUID.randomUUID();
        CreateOrderRequest request = new CreateOrderRequest(
                List.of(new OrderItemRequest(testProduct.getId(), 2)),
                "CREDIT_CARD"
        );

        int threadCount = 5;
        ExecutorService executor = Executors.newFixedThreadPool(threadCount);
        CountDownLatch readyLatch = new CountDownLatch(threadCount);
        CountDownLatch startLatch = new CountDownLatch(1);

        List<OrderDto> responses = Collections.synchronizedList(new ArrayList<>());
        List<Exception> errors = Collections.synchronizedList(new ArrayList<>());

        for (int i = 0; i < threadCount; i++) {
            executor.submit(() -> {
                readyLatch.countDown();
                try {
                    startLatch.await();
                    OrderDto result = orderService.createOrder(customerA, request, idempotencyKey);
                    responses.add(result);
                } catch (Exception e) {
                    errors.add(e);
                }
            });
        }

        readyLatch.await(5, TimeUnit.SECONDS);
        startLatch.countDown();
        executor.shutdown();
        assertTrue(executor.awaitTermination(10, TimeUnit.SECONDS));

        // Invariants:
        assertTrue(errors.isEmpty(), "Concurrent duplicate clicks should be safely handled without unexpected errors: " + errors);
        assertFalse(responses.isEmpty());
        // All responses must share the exact same order number
        String expectedOrderNumber = responses.get(0).orderNumber();
        for (OrderDto res : responses) {
            assertEquals(expectedOrderNumber, res.orderNumber());
        }

        // Only ONE order must exist in database for this idempotency key
        assertEquals(18, inventoryRepository.findByProductId(testProduct.getId()).orElseThrow().getStock(),
                "Stock must only be deducted once (-2) from 20 to 18, never multiple times");
    }
}
