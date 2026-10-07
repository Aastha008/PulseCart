package com.pulsecart.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.pulsecart.backend.dto.CreateOrderRequest;
import com.pulsecart.backend.dto.OrderDto;
import com.pulsecart.backend.dto.OrderItemRequest;
import com.pulsecart.backend.entity.*;
import com.pulsecart.backend.exception.InsufficientStockException;
import com.pulsecart.backend.exception.InvalidOrderStateException;
import com.pulsecart.backend.exception.ResourceNotFoundException;
import com.pulsecart.backend.exception.UnauthorizedAccessException;
import com.pulsecart.backend.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    private final OrderRepository orderRepository;
    private final InventoryRepository inventoryRepository;
    private final OrderCreationProcessor orderCreationProcessor;
    private final ObjectMapper objectMapper;
    private final java.util.concurrent.ConcurrentHashMap<String, Object> lockMap = new java.util.concurrent.ConcurrentHashMap<>();

    public OrderService(
            OrderRepository orderRepository,
            InventoryRepository inventoryRepository,
            OrderCreationProcessor orderCreationProcessor,
            ObjectMapper objectMapper
    ) {
        this.orderRepository = orderRepository;
        this.inventoryRepository = inventoryRepository;
        this.orderCreationProcessor = orderCreationProcessor;
        this.objectMapper = objectMapper;
    }

    /**
     * Creates an order with atomic conditional updates on inventory to prevent overselling.
     * Enforces client-scoped idempotency keys, rejects reuse with mismatched payloads,
     * and safely deduplicates simultaneous concurrent checkout submissions.
     */
    public OrderDto createOrder(User user, CreateOrderRequest request, String idempotencyKey) {
        if (request.items() == null || request.items().isEmpty()) {
            throw new IllegalArgumentException("Order must contain at least one item");
        }

        String requestHash = computeRequestHash(request);

        if (idempotencyKey != null && !idempotencyKey.isBlank()) {
            String lockKey = user.getId() + ":" + idempotencyKey;
            Object lock = lockMap.computeIfAbsent(lockKey, k -> new Object());
            synchronized (lock) {
                try {
                    return orderCreationProcessor.processOrderTransaction(user, request, idempotencyKey, requestHash);
                } finally {
                    lockMap.remove(lockKey, lock);
                }
            }
        }

        return orderCreationProcessor.processOrderTransaction(user, request, null, requestHash);
    }

    @Transactional(readOnly = true)
    public Page<OrderDto> getCustomerOrders(User user, Pageable pageable) {
        return orderRepository.findByUserId(user.getId(), pageable).map(OrderDto::from);
    }

    @Transactional(readOnly = true)
    public OrderDto getOrderById(User user, Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new ResourceNotFoundException("Order not found with id: " + orderId));

        if (!order.getUser().getId().equals(user.getId()) && user.getRole() != Role.ROLE_ADMIN) {
            throw new UnauthorizedAccessException("Access denied to order " + orderId);
        }

        return OrderDto.from(order);
    }

    /**
     * Cancels an eligible order and restores inventory exactly once.
     * Uses atomic status transition at the database level to strictly prevent double restorations
     * even under simultaneous concurrent cancellation requests.
     */
    @Transactional
    public OrderDto cancelOrder(User user, Long orderId) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> new ResourceNotFoundException("Order not found with id: " + orderId));

        if (!order.getUser().getId().equals(user.getId()) && user.getRole() != Role.ROLE_ADMIN) {
            throw new UnauthorizedAccessException("Access denied to order " + orderId);
        }

        // Atomic status transition from CONFIRMED -> CANCELLED:
        // The database engine guarantees only ONE concurrent transaction receives updated == 1
        int transitioned = orderRepository.transitionStatus(orderId, OrderStatus.CONFIRMED, OrderStatus.CANCELLED);
        if (transitioned == 0) {
            Order current = orderRepository.findById(orderId).orElseThrow();
            if (current.getStatus() == OrderStatus.CANCELLED) {
                throw new InvalidOrderStateException("Order " + orderId + " is already cancelled");
            }
            if (current.getStatus() == OrderStatus.COMPLETED) {
                throw new InvalidOrderStateException("Completed order cannot be cancelled");
            }
            throw new InvalidOrderStateException("Order " + orderId + " cannot be cancelled from state " + current.getStatus());
        }

        // ONLY the single thread that successfully updated the status is authorized to restore inventory
        for (OrderItem item : order.getItems()) {
            inventoryRepository.incrementStock(item.getProduct().getId(), item.getQuantity());
        }

        order.setStatus(OrderStatus.CANCELLED);
        log.info("Order {} successfully cancelled and stock restored exactly once.", order.getOrderNumber());

        return OrderDto.from(order);
    }

    private String computeRequestHash(CreateOrderRequest request) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            String serialized = objectMapper.writeValueAsString(request);
            byte[] hash = digest.digest(serialized.getBytes(StandardCharsets.UTF_8));
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                String hex = Integer.toHexString(0xff & b);
                if (hex.length() == 1) hexString.append('0');
                hexString.append(hex);
            }
            return hexString.toString();
        } catch (Exception e) {
            return String.valueOf(request.hashCode());
        }
    }
}
