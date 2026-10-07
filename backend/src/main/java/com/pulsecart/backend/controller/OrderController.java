package com.pulsecart.backend.controller;

import com.pulsecart.backend.dto.CreateOrderRequest;
import com.pulsecart.backend.dto.OrderDto;
import com.pulsecart.backend.dto.PageResponse;
import com.pulsecart.backend.security.CustomUserDetails;
import com.pulsecart.backend.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/orders")
@Tag(name = "Orders", description = "Customer Order Placement, History and Cancellation APIs")
@SecurityRequirement(name = "bearerAuth")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @PostMapping
    @Operation(summary = "Place an order with server-calculated prices and pessimistic stock locking")
    public ResponseEntity<OrderDto> createOrder(
            @AuthenticationPrincipal CustomUserDetails userDetails,
            @Parameter(description = "Optional idempotency key to prevent duplicate orders on retry")
            @RequestHeader(value = "Idempotency-Key", required = false) String idempotencyKey,
            @Valid @RequestBody CreateOrderRequest request
    ) {
        OrderDto order = orderService.createOrder(userDetails.getUser(), request, idempotencyKey);
        return ResponseEntity.status(HttpStatus.CREATED).body(order);
    }

    @GetMapping
    @Operation(summary = "Get paginated order history for the authenticated customer")
    public ResponseEntity<PageResponse<OrderDto>> getOrders(
            @AuthenticationPrincipal CustomUserDetails userDetails,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size
    ) {
        Pageable pageable = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createdAt"));
        return ResponseEntity.ok(PageResponse.from(orderService.getCustomerOrders(userDetails.getUser(), pageable)));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get order details by ID (enforces customer ownership)")
    public ResponseEntity<OrderDto> getOrderById(
            @AuthenticationPrincipal CustomUserDetails userDetails,
            @PathVariable Long id
    ) {
        return ResponseEntity.ok(orderService.getOrderById(userDetails.getUser(), id));
    }

    @PostMapping("/{id}/cancel")
    @Operation(summary = "Cancel an order and restore inventory exactly once")
    public ResponseEntity<OrderDto> cancelOrder(
            @AuthenticationPrincipal CustomUserDetails userDetails,
            @PathVariable Long id
    ) {
        return ResponseEntity.ok(orderService.cancelOrder(userDetails.getUser(), id));
    }
}
