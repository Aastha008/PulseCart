{{ config(materialized='view') }}

WITH events AS (
    SELECT * FROM {{ ref('stg_events') }}
)
SELECT
    session_id,
    user_id,
    COUNT(event_id) AS total_events_count,
    
    -- Event counts per stage
    COUNT(CASE WHEN event_type = 'landing_page' THEN 1 END) AS landing_page_events,
    COUNT(CASE WHEN event_type = 'product_view' THEN 1 END) AS product_view_events,
    COUNT(CASE WHEN event_type = 'add_to_cart' THEN 1 END) AS add_to_cart_events,
    COUNT(CASE WHEN event_type = 'checkout_started' THEN 1 END) AS checkout_started_events,
    COUNT(CASE WHEN event_type = 'payment_started' THEN 1 END) AS payment_started_events,
    COUNT(CASE WHEN event_type = 'purchase' THEN 1 END) AS purchase_events,
    
    -- Boolean flags
    LOGICAL_OR(event_type = 'landing_page') AS has_landing_page,
    LOGICAL_OR(event_type = 'product_view') AS has_product_view,
    LOGICAL_OR(event_type = 'add_to_cart') AS has_add_to_cart,
    LOGICAL_OR(event_type = 'checkout_started') AS has_checkout_started,
    LOGICAL_OR(event_type = 'payment_started') AS has_payment_started,
    LOGICAL_OR(event_type = 'purchase') AS has_purchase,
    
    -- Numeric reached flags (1/0)
    MAX(CASE WHEN event_type = 'landing_page' THEN 1 ELSE 0 END) AS reached_landing_page,
    MAX(CASE WHEN event_type = 'product_view' THEN 1 ELSE 0 END) AS reached_product_view,
    MAX(CASE WHEN event_type = 'add_to_cart' THEN 1 ELSE 0 END) AS reached_add_to_cart,
    MAX(CASE WHEN event_type = 'checkout_started' THEN 1 ELSE 0 END) AS reached_checkout_started,
    MAX(CASE WHEN event_type = 'payment_started' THEN 1 ELSE 0 END) AS reached_payment_started,
    MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS reached_purchase,
    
    -- Funnel stage rank & label
    COALESCE(MAX(step_number), 0) AS furthest_step_reached,
    COALESCE(MAX(step_number), 0) AS funnel_stage_order,
    CASE
        WHEN MAX(step_number) = 6 THEN '6_purchase'
        WHEN MAX(step_number) = 5 THEN '5_payment_started'
        WHEN MAX(step_number) = 4 THEN '4_checkout_started'
        WHEN MAX(step_number) = 3 THEN '3_add_to_cart'
        WHEN MAX(step_number) = 2 THEN '2_product_view'
        WHEN MAX(step_number) = 1 THEN '1_landing_page'
        ELSE '0_none'
    END AS funnel_stage_reached,
    
    -- Earliest timestamp per stage
    MIN(CASE WHEN event_type = 'landing_page' THEN event_timestamp END) AS first_landing_at,
    MIN(CASE WHEN event_type = 'product_view' THEN event_timestamp END) AS first_product_view_at,
    MIN(CASE WHEN event_type = 'add_to_cart' THEN event_timestamp END) AS first_add_to_cart_at,
    MIN(CASE WHEN event_type = 'checkout_started' THEN event_timestamp END) AS first_checkout_at,
    MIN(CASE WHEN event_type = 'payment_started' THEN event_timestamp END) AS first_payment_at,
    MIN(CASE WHEN event_type = 'purchase' THEN event_timestamp END) AS first_purchase_at,
    
    MAX(cart_value) AS final_cart_value
FROM events
GROUP BY session_id, user_id
