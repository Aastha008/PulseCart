-- =============================================================================
-- PulseCart Analytics Engineering Infrastructure
-- Script: sql/retention_analysis.sql
-- Dialect: Google BigQuery Standard SQL
-- Description: Monthly customer cohort analysis, Month 0 to Month 6+ retention
--              matrices, repeat purchase rates, and segment LTV profiling.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. MONTHLY COHORT RETENTION MATRIX (Month 0 to Month 6+)
-- Anchored on maiden order (first purchase) month.
-- Computes initial cohort size, active user count, and percentage retained.
-- -----------------------------------------------------------------------------
WITH cohort_sizes AS (
  SELECT
    cohort_month,
    COUNT(DISTINCT user_id) AS cohort_initial_users
  FROM `pulsecart-prod.analytics_pulsecart.fct_user_retention`
  WHERE month_offset = 0
  GROUP BY cohort_month
),

cohort_activity AS (
  SELECT
    r.cohort_month,
    r.month_offset,
    COUNT(DISTINCT r.user_id) AS active_users,
    SUM(r.orders_in_month) AS total_orders,
    SUM(r.revenue_in_month) AS total_revenue
  FROM `pulsecart-prod.analytics_pulsecart.fct_user_retention` r
  GROUP BY r.cohort_month, r.month_offset
),

retention_matrix AS (
  SELECT
    ca.cohort_month,
    cs.cohort_initial_users,
    ca.month_offset,
    ca.active_users,
    ROUND(ca.active_users * 100.0 / cs.cohort_initial_users, 2) AS retention_rate_pct,
    ca.total_revenue,
    ROUND(ca.total_revenue / cs.cohort_initial_users, 2) AS ltv_per_cohort_user
  FROM cohort_activity ca
  JOIN cohort_sizes cs ON ca.cohort_month = cs.cohort_month
)
SELECT
  cohort_month,
  cohort_initial_users,
  MAX(CASE WHEN month_offset = 0 THEN retention_rate_pct END) AS m0_retention_pct,
  MAX(CASE WHEN month_offset = 1 THEN retention_rate_pct END) AS m1_retention_pct,
  MAX(CASE WHEN month_offset = 2 THEN retention_rate_pct END) AS m2_retention_pct,
  MAX(CASE WHEN month_offset = 3 THEN retention_rate_pct END) AS m3_retention_pct,
  MAX(CASE WHEN month_offset = 4 THEN retention_rate_pct END) AS m4_retention_pct,
  MAX(CASE WHEN month_offset = 5 THEN retention_rate_pct END) AS m5_retention_pct,
  MAX(CASE WHEN month_offset = 6 THEN retention_rate_pct END) AS m6_retention_pct,
  ROUND(AVG(CASE WHEN month_offset = 1 THEN retention_rate_pct END), 2) AS avg_m1_retention
FROM retention_matrix
GROUP BY cohort_month, cohort_initial_users
ORDER BY cohort_month;


-- -----------------------------------------------------------------------------
-- 2. REPEAT PURCHASE RATE ANALYSIS
-- Evaluates the percentage of customers who convert >= 2 times.
-- -----------------------------------------------------------------------------
WITH customer_orders AS (
  SELECT
    user_id,
    customer_segment,
    acquisition_channel,
    country,
    lifetime_orders,
    lifetime_revenue
  FROM `pulsecart-prod.analytics_pulsecart.dim_users`
  WHERE lifetime_orders > 0
)
SELECT
  COUNT(user_id) AS total_purchasing_customers,
  COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END) AS repeat_customers,
  COUNT(CASE WHEN lifetime_orders = 1 THEN user_id END) AS one_time_buyers,
  ROUND(COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END) * 100.0 / COUNT(user_id), 2) AS repeat_purchase_rate_pct,
  ROUND(SAFE_DIVIDE(SUM(lifetime_revenue), COUNT(user_id)), 2) AS overall_customer_aov,
  ROUND(SAFE_DIVIDE(SUM(CASE WHEN lifetime_orders >= 2 THEN lifetime_revenue END), COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END)), 2) AS repeat_customer_arpu
FROM customer_orders;


-- -----------------------------------------------------------------------------
-- 3. RETENTION & REPEAT PURCHASES BY CUSTOMER SEGMENT
-- Identifies highest-retention vs high-churn segments.
-- -----------------------------------------------------------------------------
SELECT
  customer_segment,
  COUNT(user_id) AS total_customers,
  COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END) AS repeat_customers,
  ROUND(COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END) * 100.0 / COUNT(user_id), 2) AS repeat_purchase_rate_pct,
  ROUND(AVG(lifetime_orders), 2) AS avg_orders_per_customer,
  ROUND(AVG(lifetime_revenue), 2) AS avg_lifetime_revenue
FROM `pulsecart-prod.analytics_pulsecart.dim_users`
WHERE lifetime_orders > 0
GROUP BY customer_segment
ORDER BY avg_lifetime_revenue DESC;


-- -----------------------------------------------------------------------------
-- 4. RETENTION & REPEAT PURCHASES BY ACQUISITION CHANNEL
-- -----------------------------------------------------------------------------
SELECT
  acquisition_channel,
  COUNT(user_id) AS total_customers,
  COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END) AS repeat_customers,
  ROUND(COUNT(CASE WHEN lifetime_orders >= 2 THEN user_id END) * 100.0 / COUNT(user_id), 2) AS repeat_purchase_rate_pct,
  ROUND(AVG(lifetime_revenue), 2) AS avg_ltv,
  ROUND(SUM(lifetime_revenue), 2) AS channel_total_revenue
FROM `pulsecart-prod.analytics_pulsecart.dim_users`
WHERE lifetime_orders > 0
GROUP BY acquisition_channel
ORDER BY channel_total_revenue DESC;


-- -----------------------------------------------------------------------------
-- 5. CUMULATIVE CUSTOMER LIFETIME VALUE (LTV) BY COHORT
-- -----------------------------------------------------------------------------
WITH cohort_sizes AS (
  SELECT
    cohort_month,
    COUNT(DISTINCT user_id) AS cohort_size
  FROM `pulsecart-prod.analytics_pulsecart.fct_user_retention`
  WHERE month_offset = 0
  GROUP BY cohort_month
),

monthly_revenue AS (
  SELECT
    cohort_month,
    month_offset,
    SUM(revenue_in_month) AS month_revenue
  FROM `pulsecart-prod.analytics_pulsecart.fct_user_retention`
  GROUP BY cohort_month, month_offset
)
SELECT
  mr.cohort_month,
  cs.cohort_size,
  mr.month_offset,
  mr.month_revenue,
  SUM(mr.month_revenue) OVER (
    PARTITION BY mr.cohort_month 
    ORDER BY mr.month_offset 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_cohort_revenue,
  ROUND(
    SUM(mr.month_revenue) OVER (
      PARTITION BY mr.cohort_month 
      ORDER BY mr.month_offset 
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) / cs.cohort_size, 
    2
  ) AS cumulative_ltv_per_user
FROM monthly_revenue mr
JOIN cohort_sizes cs ON mr.cohort_month = cs.cohort_month
ORDER BY mr.cohort_month, mr.month_offset;
