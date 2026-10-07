package com.pulsecart.backend.controller;

import com.pulsecart.backend.dto.CreateProductRequest;
import com.pulsecart.backend.dto.ProductDto;
import com.pulsecart.backend.dto.UpdateProductRequest;
import com.pulsecart.backend.dto.UpdateStockRequest;
import com.pulsecart.backend.service.ProductService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/admin")
@PreAuthorize("hasRole('ADMIN')")
@Tag(name = "Admin Catalog", description = "Admin-Only Product and Inventory Management")
@SecurityRequirement(name = "bearerAuth")
public class AdminProductController {

    private final ProductService productService;

    public AdminProductController(ProductService productService) {
        this.productService = productService;
    }

    @PostMapping("/products")
    @Operation(summary = "Create a new product with initial inventory (Admin only)")
    public ResponseEntity<ProductDto> createProduct(@Valid @RequestBody CreateProductRequest request) {
        ProductDto created = productService.createProduct(request);
        return ResponseEntity.status(HttpStatus.CREATED).body(created);
    }

    @PutMapping("/products/{id}")
    @Operation(summary = "Update an existing product (Admin only)")
    public ResponseEntity<ProductDto> updateProduct(
            @PathVariable Long id,
            @Valid @RequestBody UpdateProductRequest request
    ) {
        return ResponseEntity.ok(productService.updateProduct(id, request));
    }

    @PutMapping("/inventory/{productId}")
    @Operation(summary = "Update inventory stock for a product (Admin only)")
    public ResponseEntity<ProductDto> updateStock(
            @PathVariable Long productId,
            @Valid @RequestBody UpdateStockRequest request
    ) {
        return ResponseEntity.ok(productService.updateStock(productId, request.stock()));
    }
}
