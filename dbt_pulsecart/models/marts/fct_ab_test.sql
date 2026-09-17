{{
  config(
    materialized = 'table',
    partition_by = {
      'field': 'session_date',
      'data_type': 'date',
      'granularity': 'day'
    } if target.type == 'bigquery' else none,
    cluster_by = ['ab_variant', 'device_type', 'country']
  )
}}

WITH ab_conversions AS (
    SELECT * FROM {{ ref('int_ab_session_conversions') }}
),
users AS (
    SELECT user_id, customer_segment, signup_date FROM {{ ref('stg_users') }}
)
SELECT
    ab.session_id,
    ab.user_id,
    ab.session_date,
    ab.session_start,
    ab.ab_variant,
    ab.device_type,
    ab.country,
    COALESCE(users.customer_segment, 'Regular') AS customer_segment,
    ab.traffic_source,
    1 AS entered_checkout,
    1 AS started_checkout,
    ab.completed_payment,
    ab.completed_purchase,
    CASE WHEN ab.completed_purchase = 1 THEN 1 ELSE 0 END AS converted_to_purchase,
    ab.order_id,
    ab.order_revenue,
    {{ datediff_cross('CAST(users.signup_date AS TIMESTAMP)', 'CAST(ab.session_date AS TIMESTAMP)', 'DAY') }} AS days_since_user_signup
FROM ab_conversions ab
LEFT JOIN users ON ab.user_id = users.user_id
