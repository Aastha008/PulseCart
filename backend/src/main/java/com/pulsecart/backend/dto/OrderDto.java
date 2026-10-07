package com.pulsecart.backend.dto;

import com.pulsecart.backend.entity.Order;
import com.pulsecart.backend.entity.OrderStatus;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

public record OrderDto(
        Long id,
        String orderNumber,
        Long userId,
        String customerEmail,
        OrderStatus status,
        BigDecimal subtotal,
        BigDecimal taxAmount,
        BigDecimal shippingFee,
        BigDecimal discountAmount,
        BigDecimal totalAmount,
        String paymentMethod,
        List<OrderItemDto> items,
        Instant createdAt,
        Instant updatedAt
) {
    public static OrderDto from(Order order) {
        List<OrderItemDto> items = order.getItems().stream()
                .map(OrderItemDto::from)
                .toList();

        return new OrderDto(
                order.getId(),
                order.getOrderNumber(),
                order.getUser().getId(),
                order.getUser().getEmail(),
                order.getStatus(),
                order.getSubtotal(),
                order.getTaxAmount(),
                order.getShippingFee(),
                order.getDiscountAmount(),
                order.getTotalAmount(),
                order.getPaymentMethod(),
                items,
                order.getCreatedAt(),
                order.getUpdatedAt()
        );
    }
}
