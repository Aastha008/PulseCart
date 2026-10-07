package com.pulsecart.backend.dto;

import com.pulsecart.backend.entity.Order;

import java.math.BigDecimal;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

public record OperationalOrderAnalyticsDto(
        String orderId,
        String sessionId,
        String userId,
        String orderDate,
        String orderTimestamp,
        BigDecimal subtotal,
        BigDecimal taxAmount,
        BigDecimal shippingFee,
        BigDecimal discountAmount,
        BigDecimal totalAmount,
        String paymentMethod,
        String status,
        String abVariant,
        String dataSource
) {
    private static final DateTimeFormatter DATE_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd").withZone(ZoneOffset.UTC);
    private static final DateTimeFormatter TS_FMT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss").withZone(ZoneOffset.UTC);

    public static OperationalOrderAnalyticsDto from(Order order) {
        return new OperationalOrderAnalyticsDto(
                "OP-" + order.getOrderNumber(),
                null, // Explicitly null: transactional backend orders do not originate from synthetic web tracking
                "OP-USR-" + order.getUser().getId(),
                DATE_FMT.format(order.getCreatedAt()),
                TS_FMT.format(order.getCreatedAt()),
                order.getSubtotal(),
                order.getTaxAmount(),
                order.getShippingFee(),
                order.getDiscountAmount(),
                order.getTotalAmount(),
                order.getPaymentMethod(),
                order.getStatus().name(),
                null, // Explicitly null: operational data is segregated from A/B experiment variants
                "operational_backend"
        );
    }
}
