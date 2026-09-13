{{
  config(
    materialized = 'incremental',
    unique_key = 'order_id',
    on_schema_change = 'sync_all_columns',
    partition_by = {
      'field': 'order_date',
      'data_type': 'date',
      'granularity': 'day'
    },
    cluster_by = ['user_id', 'status', 'ab_variant']
  )
}}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    {% if is_incremental() %}
      WHERE order_timestamp >= (SELECT TIMESTAMP_SUB(MAX(order_timestamp), INTERVAL 3 DAY) FROM {{ this }})
    {% endif %}
),
sessions AS (
    SELECT session_id, device_type, traffic_source FROM {{ ref('stg_sessions') }}
),
users AS (
    SELECT user_id, country, customer_segment, acquisition_channel, signup_date FROM {{ ref('stg_users') }}
),
items_agg AS (
    SELECT * FROM {{ ref('int_order_items_aggregated') }}
),
sequenced AS (
    SELECT
        order_id,
        user_id,
        ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY order_timestamp, order_id) AS user_order_sequence,
        LAG(order_timestamp) OVER (PARTITION BY user_id ORDER BY order_timestamp, order_id) AS prior_order_timestamp
    FROM {{ ref('stg_orders') }}
)
SELECT
    orders.order_id,
    orders.session_id,
    orders.user_id,
    orders.order_timestamp,
    orders.order_date,
    orders.status,
    orders.subtotal_amount AS subtotal,
    orders.subtotal_amount,
    orders.shipping_amount AS shipping_fee,
    orders.shipping_amount,
    orders.tax_amount,
    orders.discount_amount,
    orders.total_amount,
    orders.payment_method,
    orders.ab_variant,
    
    -- Items & Profitability
    COALESCE(items_agg.item_count, items_agg.total_items_count, 1) AS item_count,
    COALESCE(items_agg.total_items_count, 1) AS total_items_count,
    COALESCE(items_agg.distinct_products_count, 1) AS distinct_products_count,
    COALESCE(items_agg.total_cost, items_agg.total_cogs, 0.0) AS total_cost,
    COALESCE(items_agg.total_cogs, 0.0) AS total_cogs,
    COALESCE(items_agg.gross_margin_amount, items_agg.gross_profit, orders.total_amount * 0.4) AS gross_margin_amount,
    COALESCE(items_agg.gross_profit, orders.total_amount * 0.4) AS gross_profit,
    COALESCE(items_agg.margin_rate, 0.40) AS margin_rate,
    items_agg.primary_product_category,
    
    -- Order Sequence & Frequency
    sequenced.user_order_sequence,
    CASE WHEN sequenced.user_order_sequence = 1 THEN TRUE ELSE FALSE END AS is_first_order,
    CASE WHEN sequenced.user_order_sequence > 1 THEN TRUE ELSE FALSE END AS is_repeat_order,
    TIMESTAMP_DIFF(orders.order_timestamp, sequenced.prior_order_timestamp, DAY) AS days_since_prior_order,
    TIMESTAMP_DIFF(orders.order_timestamp, CAST(users.signup_date AS TIMESTAMP), DAY) AS days_since_user_signup,
    
    -- Contextual dimensions
    sessions.device_type,
    sessions.traffic_source,
    COALESCE(users.country, 'Unknown') AS country,
    COALESCE(users.customer_segment, 'Regular') AS customer_segment
FROM orders
LEFT JOIN sessions ON orders.session_id = sessions.session_id
LEFT JOIN users ON orders.user_id = users.user_id
LEFT JOIN items_agg ON orders.order_id = items_agg.order_id
LEFT JOIN sequenced ON orders.order_id = sequenced.order_id
