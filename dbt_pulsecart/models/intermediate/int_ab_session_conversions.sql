{{ config(materialized='view') }}

WITH sessions AS (
    SELECT * FROM {{ ref('stg_sessions') }}
),
funnel AS (
    SELECT * FROM {{ ref('int_session_funnel_events') }}
),
orders AS (
    SELECT session_id, order_id, total_amount, status FROM {{ ref('stg_orders') }}
    WHERE status = 'completed'
)
SELECT
    sessions.session_id,
    sessions.user_id,
    sessions.session_date,
    sessions.session_start,
    sessions.ab_variant,
    sessions.device_type,
    sessions.country,
    sessions.traffic_source,
    funnel.has_checkout_started,
    funnel.has_payment_started,
    funnel.has_purchase,
    1 AS started_checkout,
    CASE WHEN funnel.has_payment_started THEN 1 ELSE 0 END AS completed_payment,
    CASE WHEN funnel.has_purchase THEN 1 ELSE 0 END AS completed_purchase,
    orders.order_id,
    COALESCE(orders.total_amount, 0.0) AS order_revenue
FROM sessions
JOIN funnel ON sessions.session_id = funnel.session_id
LEFT JOIN orders ON sessions.session_id = orders.session_id
WHERE funnel.has_checkout_started = TRUE
