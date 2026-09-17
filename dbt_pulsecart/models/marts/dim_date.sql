{{
  config(
    materialized = 'table'
  )
}}

WITH date_spine AS (
    {% if target.type == 'snowflake' %}
    SELECT DATEADD(day, SEQ4(), '2024-01-01'::DATE) AS date_day
    FROM TABLE(GENERATOR(ROWCOUNT => 1096))
    {% elif target.type == 'bigquery' %}
    SELECT date_day
    FROM UNNEST(GENERATE_DATE_ARRAY('2024-01-01', '2026-12-31', INTERVAL 1 DAY)) AS date_day
    {% else %}
    SELECT CAST(range AS DATE) AS date_day
    FROM range(DATE '2024-01-01', DATE '2027-01-01', INTERVAL 1 DAY)
    {% endif %}
)
SELECT
    date_day,
    EXTRACT(YEAR FROM date_day) AS year,
    EXTRACT(QUARTER FROM date_day) AS quarter,
    CONCAT('Q', CAST(EXTRACT(QUARTER FROM date_day) AS STRING), ' ', CAST(EXTRACT(YEAR FROM date_day) AS STRING)) AS quarter_name,
    EXTRACT(MONTH FROM date_day) AS month,
    {% if target.type == 'snowflake' %}
    TO_CHAR(date_day, 'MMMM') AS month_name,
    TO_CHAR(date_day, 'Mon') AS month_short,
    TO_CHAR(date_day, 'YYYY-MM') AS year_month,
    EXTRACT(WEEK FROM date_day) AS week_of_year,
    EXTRACT(DAY FROM date_day) AS day_of_month,
    EXTRACT(DAYOFWEEK FROM date_day) AS day_of_week,
    TO_CHAR(date_day, 'DY') AS day_name,
    TO_CHAR(date_day, 'DY') AS day_short,
    CASE WHEN DAYNAME(date_day) IN ('Sat', 'Sun') THEN TRUE ELSE FALSE END AS is_weekend
    {% elif target.type == 'bigquery' %}
    FORMAT_DATE('%B', date_day) AS month_name,
    FORMAT_DATE('%b', date_day) AS month_short,
    FORMAT_DATE('%Y-%m', date_day) AS year_month,
    EXTRACT(ISOWEEK FROM date_day) AS week_of_year,
    EXTRACT(DAY FROM date_day) AS day_of_month,
    EXTRACT(DAYOFWEEK FROM date_day) AS day_of_week,
    FORMAT_DATE('%A', date_day) AS day_name,
    FORMAT_DATE('%a', date_day) AS day_short,
    CASE WHEN FORMAT_DATE('%A', date_day) IN ('Saturday', 'Sunday') THEN TRUE ELSE FALSE END AS is_weekend
    {% else %}
    strftime(date_day, '%B') AS month_name,
    strftime(date_day, '%b') AS month_short,
    strftime(date_day, '%Y-%m') AS year_month,
    EXTRACT(WEEK FROM date_day) AS week_of_year,
    EXTRACT(DAY FROM date_day) AS day_of_month,
    EXTRACT(DAYOFWEEK FROM date_day) AS day_of_week,
    strftime(date_day, '%A') AS day_name,
    strftime(date_day, '%a') AS day_short,
    CASE WHEN strftime(date_day, '%A') IN ('Saturday', 'Sunday') THEN TRUE ELSE FALSE END AS is_weekend
    {% endif %}
FROM date_spine
