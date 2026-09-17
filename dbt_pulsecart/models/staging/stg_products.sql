{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw_pulsecart', 'raw_products') }}
),
cleaned AS (
    SELECT
        CAST(TRIM(product_id) AS STRING) AS product_id,
        TRIM(product_name) AS product_name,
        TRIM(category) AS category,
        CAST(cost AS NUMERIC) AS cost,
        CAST(price AS NUMERIC) AS price,
        CAST(margin AS NUMERIC) AS margin,
        CAST(price - cost AS NUMERIC) AS unit_margin,
        {{ safe_divide_cross('price - cost', 'price') }} AS margin_rate,
        CAST(inventory_count AS INTEGER) AS inventory_count,
        CAST(created_at AS DATE) AS created_at
    FROM source
    WHERE product_id IS NOT NULL
)
SELECT * FROM cleaned
