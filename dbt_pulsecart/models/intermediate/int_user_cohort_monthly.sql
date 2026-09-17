{{ config(materialized='view') }}

WITH users AS (
    SELECT
        user_id,
        customer_segment,
        country,
        acquisition_channel,
        signup_cohort_month
    FROM {{ ref('stg_users') }}
),
user_summary AS (
    SELECT
        user_id,
        first_order_cohort_month
    FROM {{ ref('int_user_order_summary') }}
),
orders AS (
    SELECT
        order_id,
        user_id,
        order_date,
        {{ date_trunc_cross('order_date', 'MONTH') }} AS order_month,
        total_amount
    FROM {{ ref('stg_orders') }}
    WHERE status = 'completed'
),
items_agg AS (
    SELECT
        order_id,
        gross_profit
    FROM {{ ref('int_order_items_aggregated') }}
)
SELECT
    users.user_id,
    users.customer_segment,
    users.country,
    users.acquisition_channel,
    users.signup_cohort_month,
    user_summary.first_order_cohort_month AS cohort_month,
    orders.order_month AS activity_month,
    CAST((EXTRACT(YEAR FROM orders.order_month) - EXTRACT(YEAR FROM user_summary.first_order_cohort_month)) * 12 + 
         (EXTRACT(MONTH FROM orders.order_month) - EXTRACT(MONTH FROM user_summary.first_order_cohort_month)) AS INTEGER) AS month_number,
    CAST((EXTRACT(YEAR FROM orders.order_month) - EXTRACT(YEAR FROM user_summary.first_order_cohort_month)) * 12 + 
         (EXTRACT(MONTH FROM orders.order_month) - EXTRACT(MONTH FROM user_summary.first_order_cohort_month)) AS INTEGER) AS month_offset,
    COUNT(DISTINCT orders.order_id) AS monthly_orders,
    COUNT(DISTINCT orders.order_id) AS orders_in_month,
    SUM(orders.total_amount) AS monthly_revenue,
    SUM(orders.total_amount) AS revenue_in_month,
    SUM(COALESCE(items_agg.gross_profit, orders.total_amount * 0.4)) AS monthly_gross_profit,
    1 AS is_retained,
    1 AS is_active
FROM users
JOIN user_summary ON users.user_id = user_summary.user_id
JOIN orders ON users.user_id = orders.user_id
LEFT JOIN items_agg ON orders.order_id = items_agg.order_id
GROUP BY
    users.user_id,
    users.customer_segment,
    users.country,
    users.acquisition_channel,
    users.signup_cohort_month,
    user_summary.first_order_cohort_month,
    orders.order_month
