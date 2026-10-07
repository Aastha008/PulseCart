package com.pulsecart.backend.service;

import com.pulsecart.backend.dto.CreateProductRequest;
import com.pulsecart.backend.dto.ProductDto;
import com.pulsecart.backend.dto.UpdateProductRequest;
import com.pulsecart.backend.entity.Inventory;
import com.pulsecart.backend.entity.Product;
import com.pulsecart.backend.entity.ProductStatus;
import com.pulsecart.backend.exception.DuplicateResourceException;
import com.pulsecart.backend.exception.ResourceNotFoundException;
import com.pulsecart.backend.repository.InventoryRepository;
import com.pulsecart.backend.repository.ProductRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

@Service
public class ProductService {

    private final ProductRepository productRepository;
    private final InventoryRepository inventoryRepository;

    public ProductService(ProductRepository productRepository, InventoryRepository inventoryRepository) {
        this.productRepository = productRepository;
        this.inventoryRepository = inventoryRepository;
    }

    @Transactional(readOnly = true)
    public Page<ProductDto> getProducts(String category, BigDecimal minPrice, BigDecimal maxPrice, String search, Pageable pageable) {
        return productRepository.searchProducts(ProductStatus.ACTIVE, category, minPrice, maxPrice, search, pageable)
                .map(ProductDto::from);
    }

    @Transactional(readOnly = true)
    public ProductDto getProductById(Long id) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));
        return ProductDto.from(product);
    }

    @Transactional
    public ProductDto createProduct(CreateProductRequest request) {
        if (productRepository.existsBySku(request.sku())) {
            throw new DuplicateResourceException("Product with SKU already exists: " + request.sku());
        }

        Product product = new Product(
                request.sku(),
                request.name(),
                request.description(),
                request.category(),
                request.price(),
                request.cost(),
                ProductStatus.ACTIVE
        );

        Inventory inventory = new Inventory(product, request.initialStock());
        product.setInventory(inventory);
        Product savedProduct = productRepository.save(product);

        return ProductDto.from(savedProduct);
    }

    @Transactional
    public ProductDto updateProduct(Long id, UpdateProductRequest request) {
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + id));

        product.setName(request.name());
        product.setDescription(request.description());
        product.setCategory(request.category());
        product.setPrice(request.price());
        product.setCost(request.cost());
        if (request.status() != null) {
            product.setStatus(request.status());
        }

        Product updated = productRepository.save(product);
        return ProductDto.from(updated);
    }

    @Transactional
    public ProductDto updateStock(Long productId, Integer newStock) {
        Product product = productRepository.findById(productId)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found with id: " + productId));

        Inventory inventory = inventoryRepository.findByProductId(productId)
                .orElseGet(() -> {
                    Inventory inv = new Inventory(product, 0);
                    return inventoryRepository.save(inv);
                });

        inventory.setStock(newStock);
        inventoryRepository.save(inventory);
        product.setInventory(inventory);

        return ProductDto.from(product);
    }
}
