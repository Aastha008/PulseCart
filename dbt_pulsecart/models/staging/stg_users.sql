{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw_pulsecart', 'raw_users') }}
),
cleaned AS (
    SELECT
        CAST(TRIM(user_id) AS STRING) AS user_id,
        CAST(created_at AS TIMESTAMP) AS signup_timestamp,
        DATE(CAST(created_at AS TIMESTAMP)) AS signup_date,
        {{ date_trunc_cross('DATE(CAST(created_at AS TIMESTAMP))', 'MONTH') }} AS signup_cohort_month,
        {{ date_trunc_cross('DATE(CAST(created_at AS TIMESTAMP))', 'MONTH') }} AS cohort_month,
        UPPER(TRIM(country)) AS country,
        TRIM(acquisition_channel) AS acquisition_channel,
        TRIM(customer_segment) AS customer_segment,
        TRIM(device_preference) AS device_preference
    FROM source
    WHERE user_id IS NOT NULL
)
SELECT * FROM cleaned
