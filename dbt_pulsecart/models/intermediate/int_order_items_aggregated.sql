{{ config(materialized='view') }}

WITH items AS (
    SELECT * FROM {{ ref('stg_order_items') }}
),
products AS (
    SELECT * FROM {{ ref('stg_products') }}
)
SELECT
    items.order_id,
    SUM(items.quantity) AS total_items_count,
    SUM(items.quantity) AS item_count,
    COUNT(DISTINCT items.product_id) AS distinct_products_count,
    SUM(items.line_total) AS gross_items_revenue,
    SUM(items.line_total) AS subtotal_sum,
    SUM(items.quantity * items.unit_cost) AS total_cogs,
    SUM(items.quantity * items.unit_cost) AS total_cost,
    SUM(items.line_profit) AS gross_profit,
    SUM(items.line_profit) AS gross_margin_amount,
    SAFE_DIVIDE(SUM(items.line_profit), SUM(items.line_total)) AS margin_rate,
    MAX(products.category) AS primary_product_category
FROM items
LEFT JOIN products ON items.product_id = products.product_id
GROUP BY items.order_id
