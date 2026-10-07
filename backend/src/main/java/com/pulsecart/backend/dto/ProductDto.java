package com.pulsecart.backend.dto;

import com.pulsecart.backend.entity.Product;
import com.pulsecart.backend.entity.ProductStatus;

import java.math.BigDecimal;
import java.time.Instant;

public record ProductDto(
        Long id,
        String sku,
        String name,
        String description,
        String category,
        BigDecimal price,
        BigDecimal cost,
        ProductStatus status,
        int stock,
        Instant createdAt,
        Instant updatedAt
) {
    public static ProductDto from(Product product) {
        int availableStock = product.getInventory() != null ? product.getInventory().getStock() : 0;
        return new ProductDto(
                product.getId(),
                product.getSku(),
                product.getName(),
                product.getDescription(),
                product.getCategory(),
                product.getPrice(),
                product.getCost(),
                product.getStatus(),
                availableStock,
                product.getCreatedAt(),
                product.getUpdatedAt()
        );
    }
}
