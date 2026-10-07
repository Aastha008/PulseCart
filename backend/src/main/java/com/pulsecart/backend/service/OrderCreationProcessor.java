package com.pulsecart.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pulsecart.backend.dto.CreateOrderRequest;
import com.pulsecart.backend.dto.OrderDto;
import com.pulsecart.backend.dto.OrderItemRequest;
import com.pulsecart.backend.entity.*;
import com.pulsecart.backend.exception.InsufficientStockException;
import com.pulsecart.backend.exception.ResourceNotFoundException;
import com.pulsecart.backend.repository.IdempotencyRecordRepository;
import com.pulsecart.backend.repository.InventoryRepository;
import com.pulsecart.backend.repository.OrderRepository;
import com.pulsecart.backend.repository.ProductRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.*;

@Service
public class OrderCreationProcessor {

    private static final Logger log = LoggerFactory.getLogger(OrderCreationProcessor.class);
    private static final BigDecimal TAX_RATE = new BigDecimal("0.08");
    private static final BigDecimal FREE_SHIPPING_THRESHOLD = new BigDecimal("100.00");
    private static final BigDecimal STANDARD_SHIPPING_FEE = new BigDecimal("5.00");

    private final OrderRepository orderRepository;
    private final ProductRepository productRepository;
    private final InventoryRepository inventoryRepository;
    private final IdempotencyRecordRepository idempotencyRecordRepository;
    private final ObjectMapper objectMapper;

    public OrderCreationProcessor(
            OrderRepository orderRepository,
            ProductRepository productRepository,
            InventoryRepository inventoryRepository,
            IdempotencyRecordRepository idempotencyRecordRepository,
            ObjectMapper objectMapper
    ) {
        this.orderRepository = orderRepository;
        this.productRepository = productRepository;
        this.inventoryRepository = inventoryRepository;
        this.idempotencyRecordRepository = idempotencyRecordRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public OrderDto processOrderTransaction(User user, CreateOrderRequest request, String idempotencyKey, String requestHash) {
        // 1. Double-check idempotency inside the transaction under fresh READ COMMITTED snapshot
        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            Optional<IdempotencyRecord> existing = idempotencyRecordRepository
                    .findByIdempotencyKeyAndUserId(idempotencyKey, user.getId());

            if (existing.isPresent()) {
                IdempotencyRecord record = existing.get();
                if (!record.getRequestHash().isBlank() && !record.getRequestHash().equals(requestHash)) {
                    throw new IllegalArgumentException(String.format(
                            "Idempotency key '%s' was already used with a different request payload",
                            idempotencyKey
                    ));
                }

                log.info("Idempotent request detected for key: {}. Returning cached order response.", idempotencyKey);
                try {
                    return objectMapper.readValue(record.getResponseBody(), OrderDto.class);
                } catch (JsonProcessingException e) {
                    log.error("Failed to deserialize cached idempotency payload", e);
                }
            }
        }

        // 2. Sort item requests by Product ID to prevent database deadlocks under high concurrency
        List<OrderItemRequest> sortedItems = new ArrayList<>(request.items());
        sortedItems.sort(Comparator.comparing(OrderItemRequest::productId));

        BigDecimal subtotal = BigDecimal.ZERO;
        List<OrderItem> orderItems = new ArrayList<>();
        String orderNumber = "ORD-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase() + "-" + (System.currentTimeMillis() % 100000);

        Order order = new Order();
        order.setOrderNumber(orderNumber);
        order.setUser(user);
        order.setStatus(OrderStatus.CONFIRMED);
        order.setPaymentMethod(request.paymentMethod() != null ? request.paymentMethod() : "CREDIT_CARD");

        // 3. Process each item: atomic conditional stock decrement to strictly prevent overselling
        for (OrderItemRequest itemReq : sortedItems) {
            Product product = productRepository.findById(itemReq.productId())
                    .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + itemReq.productId()));

            int updated = inventoryRepository.decrementStockIfSufficient(product.getId(), itemReq.quantity());
            if (updated == 0) {
                Inventory currentInv = inventoryRepository.findByProductId(product.getId())
                        .orElseThrow(() -> new ResourceNotFoundException("Inventory record not found for product: " + product.getId()));
                throw new InsufficientStockException(String.format(
                        "Insufficient stock for product '%s' (SKU: %s). Requested: %d, Available: %d",
                        product.getName(), product.getSku(), itemReq.quantity(), currentInv.getStock()
                ));
            }

            // Server-side price snapshotting (preserving the exact purchase price)
            BigDecimal itemPrice = product.getPrice();
            BigDecimal itemTotal = itemPrice.multiply(BigDecimal.valueOf(itemReq.quantity()));
            subtotal = subtotal.add(itemTotal);

            OrderItem orderItem = new OrderItem(
                    order,
                    product,
                    product.getName(),
                    itemPrice,
                    itemReq.quantity(),
                    itemTotal
            );
            orderItems.add(orderItem);
        }

        // 4. Calculate Taxes and Shipping
        BigDecimal taxAmount = subtotal.multiply(TAX_RATE).setScale(2, RoundingMode.HALF_UP);
        BigDecimal shippingFee = subtotal.compareTo(FREE_SHIPPING_THRESHOLD) >= 0 ? BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP) : STANDARD_SHIPPING_FEE;
        BigDecimal discountAmount = BigDecimal.ZERO.setScale(2, RoundingMode.HALF_UP);
        BigDecimal totalAmount = subtotal.add(taxAmount).add(shippingFee).subtract(discountAmount);

        order.setSubtotal(subtotal);
        order.setTaxAmount(taxAmount);
        order.setShippingFee(shippingFee);
        order.setDiscountAmount(discountAmount);
        order.setTotalAmount(totalAmount);
        order.setItems(orderItems);

        Order savedOrder = orderRepository.save(order);
        OrderDto orderDto = OrderDto.from(savedOrder);

        // 5. Save Idempotency Record (scoped by user_id and idempotency_key)
        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            try {
                String responseBodyJson = objectMapper.writeValueAsString(orderDto);
                IdempotencyRecord record = new IdempotencyRecord(
                        idempotencyKey,
                        user,
                        savedOrder,
                        requestHash,
                        201,
                        responseBodyJson
                );
                idempotencyRecordRepository.save(record);
            } catch (JsonProcessingException e) {
                log.error("Failed to serialize order response for idempotency storage", e);
            }
        }

        return orderDto;
    }
}
