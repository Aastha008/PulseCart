{{
  config(
    materialized = 'table'
  )
}}

WITH date_spine AS (
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2026-12-31', INTERVAL 1 DAY)) AS date_day
)
SELECT
    date_day,
    EXTRACT(YEAR FROM date_day) AS year,
    EXTRACT(QUARTER FROM date_day) AS quarter,
    CONCAT('Q', CAST(EXTRACT(QUARTER FROM date_day) AS STRING), ' ', CAST(EXTRACT(YEAR FROM date_day) AS STRING)) AS quarter_name,
    EXTRACT(MONTH FROM date_day) AS month,
    FORMAT_DATE('%B', date_day) AS month_name,
    FORMAT_DATE('%b', date_day) AS month_short,
    FORMAT_DATE('%Y-%m', date_day) AS year_month,
    EXTRACT(ISOWEEK FROM date_day) AS week_of_year,
    EXTRACT(DAY FROM date_day) AS day_of_month,
    EXTRACT(DAYOFWEEK FROM date_day) AS day_of_week,
    FORMAT_DATE('%A', date_day) AS day_name,
    FORMAT_DATE('%a', date_day) AS day_short,
    CASE WHEN FORMAT_DATE('%A', date_day) IN ('Saturday', 'Sunday') THEN TRUE ELSE FALSE END AS is_weekend
FROM date_spine
