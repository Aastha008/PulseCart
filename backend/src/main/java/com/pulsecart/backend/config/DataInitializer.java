package com.pulsecart.backend.config;

import com.pulsecart.backend.entity.*;
import com.pulsecart.backend.repository.InventoryRepository;
import com.pulsecart.backend.repository.ProductRepository;
import com.pulsecart.backend.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final UserRepository userRepository;
    private final ProductRepository productRepository;
    private final InventoryRepository inventoryRepository;
    private final PasswordEncoder passwordEncoder;

    public DataInitializer(
            UserRepository userRepository,
            ProductRepository productRepository,
            InventoryRepository inventoryRepository,
            PasswordEncoder passwordEncoder
    ) {
        this.userRepository = userRepository;
        this.productRepository = productRepository;
        this.inventoryRepository = inventoryRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    @Transactional
    public void run(String... args) {
        initUsers();
        initProducts();
    }

    private void initUsers() {
        if (!userRepository.existsByEmail("admin@pulsecart.io")) {
            User admin = new User(
                    "admin@pulsecart.io",
                    passwordEncoder.encode("Admin123!"),
                    "System",
                    "Admin",
                    Role.ROLE_ADMIN
            );
            userRepository.save(admin);
            log.info("Initialized default admin user: admin@pulsecart.io");
        }

        if (!userRepository.existsByEmail("customer@pulsecart.io")) {
            User customer = new User(
                    "customer@pulsecart.io",
                    passwordEncoder.encode("Customer123!"),
                    "Demo",
                    "Customer",
                    Role.ROLE_CUSTOMER
            );
            userRepository.save(customer);
            log.info("Initialized default customer user: customer@pulsecart.io");
        }
    }

    private void initProducts() {
        if (productRepository.count() == 0) {
            log.info("Initializing default product catalog and stock...");
            List<Product> products = List.of(
                    new Product("SKU-PRD-00001", "AeroPulse Wireless Headphones", "Active noise cancelling Bluetooth over-ear headphones", "Electronics", new BigDecimal("320.99"), new BigDecimal("176.63"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00002", "ProStream HD Webcam", "1080p 60fps auto-focus streaming webcam with ring light", "Electronics", new BigDecimal("203.99"), new BigDecimal("113.88"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00003", "OmniCharge 65W GaN Charger", "Compact dual USB-C rapid charging power adapter", "Electronics", new BigDecimal("350.49"), new BigDecimal("212.61"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00004", "SoundSphere Bluetooth Speaker", "360-degree spatial audio waterproof portable speaker", "Electronics", new BigDecimal("294.49"), new BigDecimal("168.07"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00005", "KeyCraft Mechanical Keyboard", "Hot-swappable RGB mechanical gaming keyboard", "Electronics", new BigDecimal("391.99"), new BigDecimal("223.93"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00006", "Veloce Breathable Running Tee", "Moisture-wicking athletic performance t-shirt", "Apparel", new BigDecimal("45.00"), new BigDecimal("18.50"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00007", "HydroSteel Insulated Bottle 1L", "Double-wall vacuum insulated stainless steel water bottle", "Home & Kitchen", new BigDecimal("34.99"), new BigDecimal("12.20"), ProductStatus.ACTIVE),
                    new Product("SKU-PRD-00008", "ErgoPro Orthopedic Lumbar Pillow", "Memory foam ergonomic support cushion for office chairs", "Home & Kitchen", new BigDecimal("58.50"), new BigDecimal("24.00"), ProductStatus.ACTIVE)
            );

            for (Product p : products) {
                Inventory inv = new Inventory(p, 100);
                p.setInventory(inv);
                productRepository.save(p);
            }
            log.info("Product catalog and inventory initialized successfully.");
        }
    }
}
