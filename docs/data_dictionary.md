# PulseCart Complete Warehouse Data Dictionary

Comprehensive documentation of all datasets, tables, columns, constraints, and data types across the 4 architectural layers.

---

## 1. Raw Ingestion Layer (`data/raw/`)

### 1.1 `raw_users`
| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `user_id` | STRING / UUID | PRIMARY KEY | Unique user account identifier. |
| `created_at` | TIMESTAMP | NOT NULL | UTC timestamp when account was registered. |
| `country` | STRING | NOT NULL | Two-letter ISO country code (US, UK, CA, DE, FR, AU). |
| `acquisition_channel` | STRING | NOT NULL | Marketing channel (Organic Search, Paid Search, Direct, Social, Email, Referral). |
| `customer_segment` | STRING | NOT NULL | Customer segment (VIP, Regular, Bargain). |

### 1.2 `raw_sessions`
| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `session_id` | STRING / UUID | PRIMARY KEY | Unique browsing session identifier. |
| `user_id` | STRING / UUID | FOREIGN KEY -> `raw_users.user_id` | User associated with session. |
| `session_start` | TIMESTAMP | NOT NULL | UTC start time of session. |
| `session_end` | TIMESTAMP | NOT NULL | UTC end time of session. |
| `device_type` | STRING | NOT NULL | Device platform (Mobile, Desktop, Tablet). |
| `country` | STRING | NOT NULL | Geographic location of session. |
| `traffic_source` | STRING | NOT NULL | Traffic acquisition source. |
| `is_bounce` | BOOLEAN | NOT NULL | TRUE if session only generated 1 event. |
| `is_returning_user` | BOOLEAN | NOT NULL | TRUE if user had a prior session before `session_start`. |
| `ab_variant` | STRING | NOT NULL | Checkout variant assignment ('control' or 'treatment'). |

### 1.3 `raw_events`
| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `event_id` | STRING / UUID | PRIMARY KEY | Unique event identifier. |
| `session_id` | STRING / UUID | FOREIGN KEY -> `raw_sessions.session_id` | Session during which event occurred. |
| `user_id` | STRING / UUID | FOREIGN KEY -> `raw_users.user_id` | User triggering event. |
| `event_timestamp` | TIMESTAMP | NOT NULL | UTC event timestamp. Monotonically increasing within session. |
| `event_name` | STRING | NOT NULL | Event name (landing_page, product_view, add_to_cart, checkout_started, payment_started, purchase). |
| `step_number` | INTEGER | NOT NULL | Funnel progression index (1 to 6). |
| `page_url` | STRING | NOT NULL | Page URL path visited. |
| `product_id` | STRING | FOREIGN KEY (Nullable) -> `raw_products.product_id` | Product interacted with (populated on view, cart, purchase). |

### 1.4 `raw_orders`
| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `order_id` | STRING / UUID | PRIMARY KEY | Unique completed transaction identifier. |
| `session_id` | STRING / UUID | FOREIGN KEY -> `raw_sessions.session_id` | Session culminating in this order. |
| `user_id` | STRING / UUID | FOREIGN KEY -> `raw_users.user_id` | Customer placing order. |
| `order_timestamp` | TIMESTAMP | NOT NULL | Exact purchase completion timestamp. |
| `order_date` | DATE | NOT NULL | Calendar date of transaction. |
| `subtotal` | FLOAT | NOT NULL | Sum of product item revenues before tax/shipping/discounts. |
| `tax_amount` | FLOAT | NOT NULL | Sales tax charged. |
| `shipping_fee` | FLOAT | NOT NULL | Shipping charge applied. |
| `discount_amount` | FLOAT | NOT NULL | Promotional discount deduction. |
| `total_amount` | FLOAT | NOT NULL | Net total charged: `subtotal + tax + shipping - discount`. |
| `payment_method` | STRING | NOT NULL | Payment tender (Credit Card, PayPal, Apple Pay, Klarna). |
| `status` | STRING | NOT NULL | Order status ('completed'). |

### 1.5 `raw_order_items`
| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `order_item_id` | STRING / UUID | PRIMARY KEY | Unique line-item identifier. |
| `order_id` | STRING / UUID | FOREIGN KEY -> `raw_orders.order_id` | Parent order identifier. |
| `product_id` | STRING | FOREIGN KEY -> `raw_products.product_id` | Purchased product identifier. |
| `quantity` | INTEGER | NOT NULL | Units purchased (>= 1). |
| `unit_price` | FLOAT | NOT NULL | Price per unit at time of purchase. |
| `unit_cost` | FLOAT | NOT NULL | Cost of goods per unit. |
| `line_total` | FLOAT | NOT NULL | `quantity * unit_price`. |
| `line_profit` | FLOAT | NOT NULL | `quantity * (unit_price - unit_cost)`. |

### 1.6 `raw_products`
| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `product_id` | STRING | PRIMARY KEY | Catalog SKU identifier (PRD-00001 to PRD-00100). |
| `product_name` | STRING | NOT NULL | Conformed product name. |
| `category` | STRING | NOT NULL | Merchandising category (Electronics, Apparel, Home & Kitchen, Beauty, Sports). |
| `cost` | FLOAT | NOT NULL | Base unit cost of goods sold (COGS). |
| `price` | FLOAT | NOT NULL | Base retail selling price (`price > cost`). |
| `margin` | FLOAT | NOT NULL | Profit margin per unit (`price - cost`). |
| `inventory_count` | INTEGER | NOT NULL | Current inventory stock level. |

---

## 2. Consumption Marts Layer (`data/marts/`)

### 2.1 `fct_funnel`
- **Granularity:** One row per browsing session (`session_id`).
- **Partitioning:** Daily on `session_date`.
- **Clustering:** `device_type`, `country`, `traffic_source`, `ab_variant`.

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `session_id` | STRING | PRIMARY KEY | Unique session identifier. |
| `user_id` | STRING | FOREIGN KEY -> `dim_users.user_id` | User identifier. |
| `session_date` | DATE | PARTITION KEY | Date of session. |
| `session_start` | TIMESTAMP | NOT NULL | UTC session initiation timestamp. |
| `session_end` | TIMESTAMP | NOT NULL | UTC session termination timestamp. |
| `session_duration_seconds` | INTEGER | NOT NULL | Elapsed duration in seconds. |
| `device_type` | STRING | NOT NULL | Device category (Mobile, Desktop, Tablet). |
| `country` | STRING | NOT NULL | Geographic country. |
| `traffic_source` | STRING | NOT NULL | Inbound traffic channel. |
| `customer_segment` | STRING | NOT NULL | Customer segment (VIP, Regular, Bargain). |
| `ab_variant` | STRING | NOT NULL | Experiment cohort (control, treatment). |
| `is_returning_user` | BOOLEAN | NOT NULL | Repeat visitor flag. |
| `reached_landing_page` | INTEGER | NOT NULL | 1 if session reached landing page, 0 otherwise. |
| `reached_product_view` | INTEGER | NOT NULL | 1 if session reached product view, 0 otherwise. |
| `reached_add_to_cart` | INTEGER | NOT NULL | 1 if session added item to cart, 0 otherwise. |
| `reached_checkout_started` | INTEGER | NOT NULL | 1 if session entered checkout, 0 otherwise. |
| `reached_payment_started` | INTEGER | NOT NULL | 1 if session initiated payment, 0 otherwise. |
| `reached_purchase` | INTEGER | NOT NULL | 1 if session culminated in purchase, 0 otherwise. |
| `furthest_step_reached` | INTEGER | NOT NULL | Highest step index attained (1 to 6). |
| `funnel_stage_reached` | STRING | NOT NULL | Name of furthest milestone reached. |
| `order_id` | STRING | FOREIGN KEY (Nullable) -> `fct_orders.order_id` | Resulting order ID if converted. |
| `order_revenue` | FLOAT | NOT NULL | Revenue generated by session (0.0 if not converted). |
| `is_converting_session` | INTEGER | NOT NULL | Binary conversion indicator (1=converted, 0=not converted). |

### 2.2 `fct_orders`
- **Granularity:** One row per completed transaction (`order_id`).
- **Partitioning:** Daily on `order_date`.
- **Clustering:** `customer_segment`, `country`, `traffic_source`.

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `order_id` | STRING | PRIMARY KEY | Unique transaction identifier. |
| `session_id` | STRING | FOREIGN KEY -> `fct_funnel.session_id` | Associated browsing session. |
| `user_id` | STRING | FOREIGN KEY -> `dim_users.user_id` | Purchasing customer identifier. |
| `order_date` | DATE | PARTITION KEY | Calendar date of order. |
| `order_timestamp` | TIMESTAMP | NOT NULL | Timestamp of purchase completion. |
| `device_type` | STRING | NOT NULL | Platform used for order. |
| `country` | STRING | NOT NULL | Shipping/billing destination country. |
| `traffic_source` | STRING | NOT NULL | Inbound marketing channel. |
| `customer_segment` | STRING | NOT NULL | Customer demographic tier. |
| `ab_variant` | STRING | NOT NULL | Checkout variant during transaction. |
| `item_count` | INTEGER | NOT NULL | Total product units in order. |
| `subtotal` | FLOAT | NOT NULL | Gross item total before taxes/shipping. |
| `tax_amount` | FLOAT | NOT NULL | Tax charged. |
| `shipping_fee` | FLOAT | NOT NULL | Shipping fee collected. |
| `discount_amount` | FLOAT | NOT NULL | Promotional discounts applied. |
| `total_amount` | FLOAT | NOT NULL | Total charged amount (reconciled). |
| `total_cost` | FLOAT | NOT NULL | Total Cost of Goods Sold (COGS). |
| `gross_margin_amount` | FLOAT | NOT NULL | Gross profit: `subtotal - total_cost`. |
| `is_first_order` | BOOLEAN | NOT NULL | TRUE if this was user's maiden purchase. |

### 2.3 `fct_user_retention`
- **Granularity:** One row per user per active calendar month (`user_id`, `activity_month`).
- **Partitioning:** Monthly on `activity_month`.
- **Clustering:** `customer_segment`, `country`.

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `user_id` | STRING | FOREIGN KEY -> `dim_users.user_id` | Customer identifier. |
| `customer_segment` | STRING | NOT NULL | Customer segment tier. |
| `country` | STRING | NOT NULL | Customer country. |
| `acquisition_channel` | STRING | NOT NULL | Acquisition channel. |
| `cohort_month` | DATE | NOT NULL | Customer's maiden order month (e.g. 2025-01-01). |
| `activity_month` | DATE | PARTITION KEY | Calendar month of transaction activity. |
| `month_offset` | INTEGER | NOT NULL | Elapsed months from first purchase (0=M0, 1=M1, etc.). |
| `orders_in_month` | INTEGER | NOT NULL | Completed orders in this month. |
| `revenue_in_month` | FLOAT | NOT NULL | Total spend in this month. |
| `is_retained` | INTEGER | NOT NULL | Constant 1 for active months. |

### 2.4 `fct_ab_test`
- **Granularity:** One row per checkout session (`session_id`).
- **Partitioning:** Daily on `session_date`.
- **Clustering:** `device_type`, `ab_variant`.

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `session_id` | STRING | PRIMARY KEY | Checkout session identifier. |
| `user_id` | STRING | FOREIGN KEY -> `dim_users.user_id` | User identifier. |
| `session_date` | DATE | PARTITION KEY | Calendar date session began checkout. |
| `ab_variant` | STRING | NOT NULL | Assigned experiment variant ('control' or 'treatment'). |
| `device_type` | STRING | NOT NULL | Device platform. |
| `country` | STRING | NOT NULL | Geographic location. |
| `started_checkout` | INTEGER | NOT NULL | Constant 1 (qualifying condition). |
| `completed_payment` | INTEGER | NOT NULL | 1 if payment was initiated, 0 otherwise. |
| `completed_purchase` | INTEGER | NOT NULL | 1 if purchase was completed, 0 otherwise. |
| `order_revenue` | FLOAT | NOT NULL | Order revenue if converted, 0.0 otherwise. |

### 2.5 `dim_users`
- **Granularity:** One row per registered customer (`user_id`).

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `user_id` | STRING | PRIMARY KEY | Unique customer identifier. |
| `first_seen_at` | TIMESTAMP | NOT NULL | Timestamp account was created. |
| `country` | STRING | NOT NULL | Customer country. |
| `acquisition_channel` | STRING | NOT NULL | First-touch marketing channel. |
| `customer_segment` | STRING | NOT NULL | Segment tier (VIP, Regular, Bargain). |
| `lifetime_sessions` | INTEGER | NOT NULL | Total browsing sessions initiated. |
| `lifetime_orders` | INTEGER | NOT NULL | Total completed purchases placed. |
| `lifetime_revenue` | FLOAT | NOT NULL | Cumulative gross spend to date. |
| `first_order_date` | DATE | NULLABLE | Date of maiden transaction. |
| `last_order_date` | DATE | NULLABLE | Date of most recent transaction. |

### 2.6 `dim_products`
- **Granularity:** One row per catalog SKU (`product_id`).

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `product_id` | STRING | PRIMARY KEY | Unique catalog SKU. |
| `product_name` | STRING | NOT NULL | Cleaned product display name. |
| `category` | STRING | NOT NULL | Product category. |
| `cost` | FLOAT | NOT NULL | Unit Cost of Goods Sold. |
| `price` | FLOAT | NOT NULL | Unit retail selling price. |
| `margin_amount` | FLOAT | NOT NULL | Unit profit: `price - cost`. |
| `margin_percentage` | FLOAT | NOT NULL | Markup percentage: `(price - cost) / price * 100`. |

### 2.7 `dim_date`
- **Granularity:** One row per calendar date (`date_day`).

| Column Name | Data Type | Constraint | Description |
|---|---|---|---|
| `date_day` | DATE | PRIMARY KEY | Standard ISO calendar date. |
| `year` | INTEGER | NOT NULL | 4-digit calendar year. |
| `quarter` | INTEGER | NOT NULL | Calendar quarter (1 to 4). |
| `month` | INTEGER | NOT NULL | Month number (1 to 12). |
| `month_name` | STRING | NOT NULL | Full month name (January, February, etc.). |
| `week_of_year` | INTEGER | NOT NULL | ISO week number (1 to 53). |
| `day_of_week` | INTEGER | NOT NULL | Day of week index (1 to 7). |
| `day_name` | STRING | NOT NULL | Day name (Monday, Tuesday, etc.). |
| `is_weekend` | BOOLEAN | NOT NULL | TRUE for Saturday/Sunday, FALSE otherwise. |
