{{
  config(
    materialized = 'table',
    cluster_by = ['customer_segment', 'country', 'device_preference']
  )
}}

WITH users AS (
    SELECT * FROM {{ ref('stg_users') }}
),
user_sessions AS (
    SELECT
        user_id,
        COUNT(session_id) AS lifetime_sessions
    FROM {{ ref('stg_sessions') }}
    WHERE user_id IS NOT NULL
    GROUP BY user_id
),
summary AS (
    SELECT * FROM {{ ref('int_user_order_summary') }}
)
SELECT
    users.user_id,
    users.signup_timestamp AS first_seen_at,
    users.signup_timestamp,
    users.signup_date,
    users.cohort_month,
    users.signup_cohort_month,
    users.country,
    users.device_preference,
    users.customer_segment,
    users.acquisition_channel,
    
    -- Order activity metrics
    summary.first_order_timestamp,
    summary.first_order_date,
    summary.most_recent_order_timestamp,
    summary.most_recent_order_date AS last_order_date,
    summary.most_recent_order_date,
    COALESCE(user_sessions.lifetime_sessions, 0) AS lifetime_sessions,
    COALESCE(summary.lifetime_orders, 0) AS lifetime_orders,
    COALESCE(summary.lifetime_revenue, 0.0) AS lifetime_revenue,
    COALESCE(summary.lifetime_gross_profit, 0.0) AS lifetime_gross_profit,
    COALESCE(summary.avg_order_value, 0.0) AS avg_order_value,
    COALESCE(summary.avg_days_between_orders, 0.0) AS avg_days_between_orders,
    
    -- RFM Behavioral Segmentation
    {{ datediff_cross('CAST(COALESCE(summary.most_recent_order_date, users.signup_date) AS TIMESTAMP)', 'CURRENT_TIMESTAMP()', 'DAY') }} AS recency_days,
    CASE
        WHEN summary.lifetime_orders IS NULL OR summary.lifetime_orders = 0 THEN '0 Orders'
        WHEN summary.lifetime_orders = 1 THEN '1 Order'
        WHEN summary.lifetime_orders BETWEEN 2 AND 3 THEN '2-3 Orders'
        ELSE '4+ Orders'
    END AS frequency_band,
    CASE
        WHEN COALESCE(summary.lifetime_revenue, 0.0) = 0.0 THEN 'Tier 0: Non-Buyer'
        WHEN summary.lifetime_revenue < 100 THEN 'Tier 1: Low Value'
        WHEN summary.lifetime_revenue < 300 THEN 'Tier 2: Mid Value'
        WHEN summary.lifetime_revenue < 750 THEN 'Tier 3: High Value'
        ELSE 'Tier 4: VIP'
    END AS monetary_tier,
    CASE
        WHEN summary.lifetime_orders IS NULL OR summary.lifetime_orders = 0 THEN 'Registered Non-Purchaser'
        WHEN summary.lifetime_orders = 1 THEN 'Single Purchaser'
        WHEN summary.lifetime_orders > 1 AND {{ datediff_cross('summary.most_recent_order_timestamp', 'CURRENT_TIMESTAMP()', 'DAY') }} <= 60 THEN 'Active Repeat'
        WHEN summary.lifetime_orders > 1 AND {{ datediff_cross('summary.most_recent_order_timestamp', 'CURRENT_TIMESTAMP()', 'DAY') }} <= 120 THEN 'Dormant Repeat'
        ELSE 'Churned Repeat'
    END AS customer_lifecycle_status
FROM users
LEFT JOIN user_sessions ON users.user_id = user_sessions.user_id
LEFT JOIN summary ON users.user_id = summary.user_id
