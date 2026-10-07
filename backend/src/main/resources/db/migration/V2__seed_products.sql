-- PulseCart V2 Seed Data
-- Initial Product Catalog and Inventory Setup

INSERT INTO products (sku, name, description, category, price, cost, status, created_at, updated_at)
VALUES
('SKU-PRD-00001', 'AeroPulse Wireless Headphones', 'Active noise cancelling Bluetooth over-ear headphones', 'Electronics', 320.99, 176.63, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00002', 'ProStream HD Webcam', '1080p 60fps auto-focus streaming webcam with ring light', 'Electronics', 203.99, 113.88, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00003', 'OmniCharge 65W GaN Charger', 'Compact dual USB-C rapid charging power adapter', 'Electronics', 350.49, 212.61, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00004', 'SoundSphere Bluetooth Speaker', '360-degree spatial audio waterproof portable speaker', 'Electronics', 294.49, 168.07, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00005', 'KeyCraft Mechanical Keyboard', 'Hot-swappable RGB mechanical gaming keyboard', 'Electronics', 391.99, 223.93, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00006', 'Veloce Breathable Running Tee', 'Moisture-wicking athletic performance t-shirt', 'Apparel', 45.00, 18.50, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00007', 'HydroSteel Insulated Bottle 1L', 'Double-wall vacuum insulated stainless steel water bottle', 'Home & Kitchen', 34.99, 12.20, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('SKU-PRD-00008', 'ErgoPro Orthopedic Lumbar Pillow', 'Memory foam ergonomic support cushion for office chairs', 'Home & Kitchen', 58.50, 24.00, 'ACTIVE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

INSERT INTO inventory (product_id, stock, reserved_stock, version, updated_at)
SELECT id, 100, 0, 0, CURRENT_TIMESTAMP
FROM products;
