{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw_pulsecart', 'raw_orders') }}
),
cleaned AS (
    SELECT
        CAST(TRIM(order_id) AS STRING) AS order_id,
        CAST(TRIM(session_id) AS STRING) AS session_id,
        CAST(TRIM(user_id) AS STRING) AS user_id,
        CAST(order_date AS DATE) AS order_date,
        CAST(order_timestamp AS TIMESTAMP) AS order_timestamp,
        CAST(COALESCE(subtotal, 0.0) AS NUMERIC) AS subtotal,
        CAST(COALESCE(subtotal, 0.0) AS NUMERIC) AS subtotal_amount,
        CAST(COALESCE(tax_amount, 0.0) AS NUMERIC) AS tax_amount,
        CAST(COALESCE(shipping_fee, 0.0) AS NUMERIC) AS shipping_fee,
        CAST(COALESCE(shipping_fee, 0.0) AS NUMERIC) AS shipping_amount,
        CAST(COALESCE(discount_amount, 0.0) AS NUMERIC) AS discount_amount,
        CAST(COALESCE(total_amount, 0.0) AS NUMERIC) AS total_amount,
        TRIM(payment_method) AS payment_method,
        LOWER(TRIM(status)) AS status,
        LOWER(TRIM(ab_variant)) AS ab_variant
    FROM source
    WHERE order_id IS NOT NULL
)
SELECT * FROM cleaned
