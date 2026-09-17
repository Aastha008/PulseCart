{{
  config(
    materialized = 'table',
    partition_by = {
      'field': 'activity_month',
      'data_type': 'date',
      'granularity': 'month'
    } if target.type == 'bigquery' else none,
    cluster_by = ['cohort_month', 'customer_segment', 'country']
  )
}}

WITH cohort_base AS (
    SELECT
        user_id,
        customer_segment,
        country,
        acquisition_channel,
        cohort_month,
        signup_cohort_month,
        activity_month,
        month_number,
        month_offset,
        monthly_orders,
        orders_in_month,
        monthly_revenue,
        revenue_in_month,
        monthly_gross_profit,
        is_retained,
        is_active
    FROM {{ ref('int_user_cohort_monthly') }}
),
cumulative AS (
    SELECT
        user_id,
        cohort_month,
        activity_month,
        month_number,
        month_offset,
        customer_segment,
        country,
        acquisition_channel,
        signup_cohort_month,
        monthly_orders,
        orders_in_month,
        monthly_revenue,
        revenue_in_month,
        monthly_gross_profit,
        is_retained,
        is_active,
        SUM(monthly_orders) OVER (
            PARTITION BY user_id 
            ORDER BY activity_month 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_orders,
        SUM(monthly_revenue) OVER (
            PARTITION BY user_id 
            ORDER BY activity_month 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_revenue,
        SUM(monthly_gross_profit) OVER (
            PARTITION BY user_id 
            ORDER BY activity_month 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_gross_profit
    FROM cohort_base
)
SELECT * FROM cumulative
