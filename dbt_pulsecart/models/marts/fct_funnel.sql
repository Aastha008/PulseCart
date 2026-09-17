{{
  config(
    materialized = 'incremental',
    unique_key = 'session_id',
    on_schema_change = 'sync_all_columns',
    partition_by = {
      'field': 'session_date',
      'data_type': 'date',
      'granularity': 'day'
    } if target.type == 'bigquery' else none,
    cluster_by = ['device_type', 'country', 'traffic_source', 'ab_variant']
  )
}}

WITH sessions AS (
    SELECT * FROM {{ ref('stg_sessions') }}
    {% if is_incremental() %}
      WHERE session_start >= (SELECT {{ date_sub_days_cross('MAX(session_start)', 3) }} FROM {{ this }})
    {% endif %}
),
users AS (
    SELECT user_id, country, customer_segment, acquisition_channel FROM {{ ref('stg_users') }}
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
    sessions.session_start,
    sessions.session_end,
    sessions.session_date,
    sessions.session_duration_seconds,
    sessions.device_type,
    sessions.traffic_source,
    COALESCE(users.country, sessions.country) AS country,
    COALESCE(users.customer_segment, 'Regular') AS customer_segment,
    sessions.ab_variant,
    sessions.is_returning_user,
    
    -- Funnel milestone flags (both boolean and binary representations)
    COALESCE(funnel.has_landing_page, FALSE) AS has_landing_page,
    COALESCE(funnel.has_product_view, FALSE) AS has_product_view,
    COALESCE(funnel.has_add_to_cart, FALSE) AS has_add_to_cart,
    COALESCE(funnel.has_checkout_started, FALSE) AS has_checkout_started,
    COALESCE(funnel.has_payment_started, FALSE) AS has_payment_started,
    COALESCE(funnel.has_purchase, FALSE) AS has_purchase,

    COALESCE(funnel.reached_landing_page, 0) AS reached_landing_page,
    COALESCE(funnel.reached_product_view, 0) AS reached_product_view,
    COALESCE(funnel.reached_add_to_cart, 0) AS reached_add_to_cart,
    COALESCE(funnel.reached_checkout_started, 0) AS reached_checkout_started,
    COALESCE(funnel.reached_payment_started, 0) AS reached_payment_started,
    COALESCE(funnel.reached_purchase, 0) AS reached_purchase,
    
    COALESCE(funnel.furthest_step_reached, 0) AS furthest_step_reached,
    COALESCE(funnel.funnel_stage_order, 0) AS funnel_stage_order,
    COALESCE(funnel.funnel_stage_reached, '0_none') AS funnel_stage_reached,
    COALESCE(funnel.total_events_count, 0) AS total_events_count,
    
    -- Order metrics
    orders.order_id,
    COALESCE(orders.total_amount, 0.0) AS order_revenue,
    CASE WHEN orders.order_id IS NOT NULL THEN 1 ELSE 0 END AS is_converting_session
FROM sessions
LEFT JOIN users ON sessions.user_id = users.user_id
LEFT JOIN funnel ON sessions.session_id = funnel.session_id
LEFT JOIN orders ON sessions.session_id = orders.session_id
