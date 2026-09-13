{{ config(materialized='view') }}

WITH orders AS (
    SELECT * FROM {{ ref('stg_orders') }}
    WHERE status = 'completed'
),
items_agg AS (
    SELECT * FROM {{ ref('int_order_items_aggregated') }}
),
orders_sequenced AS (
    SELECT
        orders.order_id,
        orders.user_id,
        orders.order_timestamp,
        orders.order_date,
        orders.total_amount,
        COALESCE(items_agg.gross_profit, orders.total_amount * 0.4) AS gross_profit,
        ROW_NUMBER() OVER (
            PARTITION BY orders.user_id 
            ORDER BY orders.order_timestamp, orders.order_id
        ) AS user_order_sequence,
        LAG(orders.order_timestamp) OVER (
            PARTITION BY orders.user_id 
            ORDER BY orders.order_timestamp, orders.order_id
        ) AS prior_order_timestamp
    FROM orders
    LEFT JOIN items_agg ON orders.order_id = items_agg.order_id
)
SELECT
    user_id,
    COUNT(order_id) AS lifetime_orders,
    COUNT(order_id) AS lifetime_completed_orders,
    MIN(order_timestamp) AS first_order_timestamp,
    MIN(order_timestamp) AS first_order_at,
    MIN(order_date) AS first_order_date,
    DATE_TRUNC(MIN(order_date), MONTH) AS first_order_cohort_month,
    DATE_TRUNC(MIN(order_date), MONTH) AS cohort_month,
    MAX(order_timestamp) AS most_recent_order_timestamp,
    MAX(order_timestamp) AS last_order_at,
    MAX(order_date) AS most_recent_order_date,
    MAX(order_date) AS last_order_date,
    SUM(total_amount) AS lifetime_revenue,
    SUM(gross_profit) AS lifetime_gross_profit,
    SAFE_DIVIDE(SUM(total_amount), COUNT(order_id)) AS lifetime_aov,
    SAFE_DIVIDE(SUM(total_amount), COUNT(order_id)) AS avg_order_value,
    AVG(TIMESTAMP_DIFF(order_timestamp, prior_order_timestamp, DAY)) AS avg_days_between_orders
FROM orders_sequenced
GROUP BY user_id
