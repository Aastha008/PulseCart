package com.pulsecart.backend.controller;

import com.pulsecart.backend.dto.OperationalOrderAnalyticsDto;
import com.pulsecart.backend.repository.OrderRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/v1/admin/analytics")
@PreAuthorize("hasRole('ADMIN')")
@Tag(name = "Analytics Export", description = "Admin Data Extraction Pipeline for Data Warehouse Ingestion")
@SecurityRequirement(name = "bearerAuth")
public class AdminAnalyticsController {

    private final OrderRepository orderRepository;

    public AdminAnalyticsController(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    @GetMapping("/export-orders")
    @Operation(summary = "Export operational backend orders into analytics-compatible schema")
    public ResponseEntity<List<OperationalOrderAnalyticsDto>> exportOperationalOrders() {
        List<OperationalOrderAnalyticsDto> exportList = orderRepository.findAll().stream()
                .map(OperationalOrderAnalyticsDto::from)
                .toList();

        return ResponseEntity.ok(exportList);
    }
}
