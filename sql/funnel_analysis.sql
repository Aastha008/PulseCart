-- =============================================================================
-- PulseCart Analytics Engineering Infrastructure
-- Script: sql/funnel_analysis.sql
-- Dialect: Google BigQuery Standard SQL
-- Description: Multi-stage behavioral funnel progression, drop-off analysis,
--              dimensional slicing, and friction point diagnostics.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. OVERALL 6-STAGE FUNNEL PROGRESSION & DROP-OFF METRICS
-- Evaluates session progression across:
-- Sessions -> Product View -> Add to Cart -> Checkout -> Payment -> Purchase
-- -----------------------------------------------------------------------------
WITH stage_counts AS (
  SELECT
    COUNT(DISTINCT session_id) AS s1_sessions,
    COUNT(DISTINCT CASE WHEN reached_product_view = 1 THEN session_id END) AS s2_product_views,
    COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) AS s3_add_to_cart,
    COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END) AS s4_checkout_started,
    COUNT(DISTINCT CASE WHEN reached_payment_started = 1 THEN session_id END) AS s5_payment_started,
    COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) AS s6_purchases
  FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
),

unpivoted_stages AS (
  SELECT 1 AS stage_order, '1_sessions' AS stage_name, s1_sessions AS sessions_entered, s1_sessions AS base_sessions FROM stage_counts UNION ALL
  SELECT 2, '2_product_view', s2_product_views, s1_sessions FROM stage_counts UNION ALL
  SELECT 3, '3_add_to_cart', s3_add_to_cart, s1_sessions FROM stage_counts UNION ALL
  SELECT 4, '4_checkout_started', s4_checkout_started, s1_sessions FROM stage_counts UNION ALL
  SELECT 5, '5_payment_started', s5_payment_started, s1_sessions FROM stage_counts UNION ALL
  SELECT 6, '6_purchase', s6_purchases, s1_sessions FROM stage_counts
),

funnel_calculations AS (
  SELECT
    stage_order,
    stage_name,
    sessions_entered,
    LAG(sessions_entered) OVER (ORDER BY stage_order) AS prior_stage_sessions,
    base_sessions,
    -- Absolute drop-off from previous step
    COALESCE(LAG(sessions_entered) OVER (ORDER BY stage_order) - sessions_entered, 0) AS absolute_drop_off,
    -- Stage conversion rate (step-to-step)
    ROUND(
      SAFE_DIVIDE(sessions_entered * 100.0, LAG(sessions_entered) OVER (ORDER BY stage_order)), 
      2
    ) AS stage_conversion_rate_pct,
    -- Stage drop-off rate (% of users leaving at this step)
    ROUND(
      SAFE_DIVIDE(
        (LAG(sessions_entered) OVER (ORDER BY stage_order) - sessions_entered) * 100.0, 
        LAG(sessions_entered) OVER (ORDER BY stage_order)
      ), 
      2
    ) AS stage_drop_off_rate_pct,
    -- Overall conversion rate (relative to top of funnel)
    ROUND(
      SAFE_DIVIDE(sessions_entered * 100.0, base_sessions), 
      2
    ) AS overall_conversion_rate_pct
  FROM unpivoted_stages
)
SELECT
  stage_order,
  stage_name,
  sessions_entered,
  absolute_drop_off,
  COALESCE(stage_conversion_rate_pct, 100.0) AS stage_conversion_rate_pct,
  COALESCE(stage_drop_off_rate_pct, 0.0) AS stage_drop_off_rate_pct,
  overall_conversion_rate_pct
FROM funnel_calculations
ORDER BY stage_order;


-- -----------------------------------------------------------------------------
-- 2. FUNNEL PERFORMANCE BY DEVICE TYPE (Mobile vs Desktop vs Tablet)
-- Reveals critical mobile friction points.
-- -----------------------------------------------------------------------------
SELECT
  device_type,
  COUNT(DISTINCT session_id) AS total_sessions,
  COUNT(DISTINCT CASE WHEN reached_product_view = 1 THEN session_id END) AS product_views,
  COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) AS cart_additions,
  COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END) AS checkout_starts,
  COUNT(DISTINCT CASE WHEN reached_payment_started = 1 THEN session_id END) AS payment_starts,
  COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) AS purchases,
  
  -- Key Step Rates
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_product_view = 1 THEN session_id END) * 100.0, COUNT(DISTINCT session_id)), 2) AS view_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) * 100.0, COUNT(DISTINCT CASE WHEN reached_product_view = 1 THEN session_id END)), 2) AS cart_conversion_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END) * 100.0, COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END)), 2) AS checkout_initiation_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END)), 2) AS checkout_completion_rate_pct,
  
  -- Overall Conversion Rate
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT session_id)), 2) AS overall_conversion_rate_pct
FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
GROUP BY device_type
ORDER BY total_sessions DESC;


-- -----------------------------------------------------------------------------
-- 3. FUNNEL PERFORMANCE BY ACQUISITION CHANNEL
-- Evaluates traffic quality across Organic, Paid Search, Direct, Social, etc.
-- -----------------------------------------------------------------------------
SELECT
  traffic_source,
  COUNT(DISTINCT session_id) AS total_sessions,
  COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) AS cart_sessions,
  COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END) AS checkout_sessions,
  COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) AS purchasing_sessions,
  
  -- Conversion Rates
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) * 100.0, COUNT(DISTINCT session_id)), 2) AS add_to_cart_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END)), 2) AS checkout_to_purchase_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT session_id)), 2) AS overall_conversion_rate_pct
FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
GROUP BY traffic_source
ORDER BY overall_conversion_rate_pct DESC;


-- -----------------------------------------------------------------------------
-- 4. FUNNEL PERFORMANCE BY CUSTOMER SEGMENT (VIP vs Regular vs Bargain)
-- -----------------------------------------------------------------------------
SELECT
  customer_segment,
  COUNT(DISTINCT session_id) AS total_sessions,
  COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) AS cart_sessions,
  COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END) AS checkout_sessions,
  COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) AS purchasing_sessions,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT session_id)), 2) AS overall_conversion_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END)), 2) AS checkout_completion_rate_pct
FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
GROUP BY customer_segment
ORDER BY overall_conversion_rate_pct DESC;


-- -----------------------------------------------------------------------------
-- 5. NEW VS RETURNING USERS FUNNEL COMPARISON
-- -----------------------------------------------------------------------------
SELECT
  CASE WHEN is_returning_user THEN 'Returning User' ELSE 'New User' END AS user_type,
  COUNT(DISTINCT session_id) AS total_sessions,
  COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END) AS cart_sessions,
  COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END) AS checkout_sessions,
  COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) AS purchase_sessions,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT session_id)), 2) AS overall_conversion_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END) * 100.0, COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END)), 2) AS checkout_conversion_rate_pct
FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
GROUP BY 1
ORDER BY 2 DESC;


-- -----------------------------------------------------------------------------
-- 6. TOP FRICTION POINT DIAGNOSTICS: STAGE DROP-OFF RANKING
-- Identifies the single biggest leak in the customer journey.
-- -----------------------------------------------------------------------------
WITH step_pairs AS (
  SELECT
    '1. Landing Page -> Product View' AS stage_transition,
    COUNT(DISTINCT session_id) AS entered_sessions,
    COUNT(DISTINCT CASE WHEN reached_product_view = 1 THEN session_id END) AS completed_sessions
  FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
  UNION ALL
  SELECT
    '2. Product View -> Add to Cart',
    COUNT(DISTINCT CASE WHEN reached_product_view = 1 THEN session_id END),
    COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END)
  FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
  UNION ALL
  SELECT
    '3. Add to Cart -> Checkout Started',
    COUNT(DISTINCT CASE WHEN reached_add_to_cart = 1 THEN session_id END),
    COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END)
  FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
  UNION ALL
  SELECT
    '4. Checkout Started -> Payment Started',
    COUNT(DISTINCT CASE WHEN reached_checkout_started = 1 THEN session_id END),
    COUNT(DISTINCT CASE WHEN reached_payment_started = 1 THEN session_id END)
  FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
  UNION ALL
  SELECT
    '5. Payment Started -> Purchase Completed',
    COUNT(DISTINCT CASE WHEN reached_payment_started = 1 THEN session_id END),
    COUNT(DISTINCT CASE WHEN reached_purchase = 1 THEN session_id END)
  FROM `pulsecart-prod.analytics_pulsecart.fct_funnel`
)
SELECT
  stage_transition,
  entered_sessions,
  completed_sessions,
  (entered_sessions - completed_sessions) AS lost_sessions,
  ROUND((entered_sessions - completed_sessions) * 100.0 / entered_sessions, 2) AS drop_off_pct,
  DENSE_RANK() OVER (ORDER BY (entered_sessions - completed_sessions) DESC) AS leak_severity_rank
FROM step_pairs
ORDER BY leak_severity_rank;
