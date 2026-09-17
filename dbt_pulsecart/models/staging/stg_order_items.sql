{{ config(materialized='view') }}

WITH source AS (
    SELECT * FROM {{ source('raw_pulsecart', 'raw_order_items') }}
),
cleaned AS (
    SELECT
        CAST(TRIM(order_item_id) AS STRING) AS order_item_id,
        CAST(TRIM(order_id) AS STRING) AS order_id,
        CAST(TRIM(product_id) AS STRING) AS product_id,
        CAST(quantity AS INTEGER) AS quantity,
        CAST(unit_price AS NUMERIC) AS unit_price,
        CAST(unit_cost AS NUMERIC) AS unit_cost,
        CAST(line_total AS NUMERIC) AS line_total,
        CAST(COALESCE(total_item_price, line_total) AS NUMERIC) AS total_item_price,
        CAST(line_profit AS NUMERIC) AS line_profit
    FROM source
    WHERE order_item_id IS NOT NULL
)
SELECT * FROM cleaned
