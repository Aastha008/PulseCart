{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw_pulsecart', 'raw_sessions') }}
),
cleaned AS (
    SELECT
        CAST(TRIM(session_id) AS STRING) AS session_id,
        CAST(TRIM(user_id) AS STRING) AS user_id,
        CAST(session_start AS TIMESTAMP) AS session_start,
        CAST(session_end AS TIMESTAMP) AS session_end,
        DATE(CAST(session_start AS TIMESTAMP)) AS session_date,
        GREATEST(0, TIMESTAMP_DIFF(CAST(session_end AS TIMESTAMP), CAST(session_start AS TIMESTAMP), SECOND)) AS session_duration_seconds,
        TRIM(device_type) AS device_type,
        UPPER(TRIM(country)) AS country,
        TRIM(traffic_source) AS traffic_source,
        TRIM(channel) AS channel,
        CAST(is_bounce AS BOOLEAN) AS is_bounce,
        CAST(is_returning_user AS BOOLEAN) AS is_returning_user,
        CAST(is_new_user AS BOOLEAN) AS is_new_user,
        LOWER(TRIM(ab_variant)) AS ab_variant,
        TRIM(experiment_id) AS experiment_id
    FROM source
    WHERE session_id IS NOT NULL
)
SELECT * FROM cleaned
