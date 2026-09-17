{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw_pulsecart', 'raw_events') }}
),
cleaned AS (
    SELECT
        CAST(TRIM(event_id) AS STRING) AS event_id,
        CAST(TRIM(session_id) AS STRING) AS session_id,
        CAST(TRIM(user_id) AS STRING) AS user_id,
        CAST(event_timestamp AS TIMESTAMP) AS event_timestamp,
        DATE(CAST(event_timestamp AS TIMESTAMP)) AS event_date,
        LOWER(TRIM(event_name)) AS event_name,
        LOWER(TRIM(event_type)) AS event_type,
        CAST(step_number AS INTEGER) AS step_number,
        TRIM(page_url) AS page_url,
        NULLIF(TRIM(product_id), '') AS product_id,
        CAST(COALESCE(cart_value, 0.0) AS NUMERIC) AS cart_value
    FROM source
    WHERE event_id IS NOT NULL
)
SELECT * FROM cleaned
