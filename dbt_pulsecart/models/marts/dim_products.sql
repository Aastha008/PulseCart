{{
  config(
    materialized = 'table',
    cluster_by = ['category']
  )
}}

WITH products AS (
    SELECT * FROM {{ ref('stg_products') }}
),
item_stats AS (
    SELECT
        product_id,
        COUNT(DISTINCT order_id) AS total_orders_count,
        SUM(quantity) AS total_units_sold,
        SUM(line_total) AS total_revenue_generated,
        SUM(line_profit) AS total_profit_generated
    FROM {{ ref('stg_order_items') }}
    GROUP BY product_id
)
SELECT
    products.product_id,
    products.product_name,
    products.category,
    products.cost,
    products.price,
    ROUND(CAST(products.price - products.cost AS NUMERIC), 2) AS margin_amount,
    ROUND({{ safe_divide_cross('products.price - products.cost', 'products.price') }} * 100.0, 2) AS margin_percentage,
    products.margin,
    products.unit_margin,
    products.margin_rate,
    products.inventory_count,
    products.created_at,
    COALESCE(item_stats.total_orders_count, 0) AS total_orders_count,
    COALESCE(item_stats.total_units_sold, 0) AS total_units_sold,
    COALESCE(item_stats.total_revenue_generated, 0.0) AS total_revenue_generated,
    COALESCE(item_stats.total_profit_generated, 0.0) AS total_profit_generated,
    {{ safe_divide_cross('item_stats.total_revenue_generated', 'item_stats.total_units_sold') }} AS realized_avg_selling_price
FROM products
LEFT JOIN item_stats ON products.product_id = item_stats.product_id
