-- =============================================================================
-- PulseCart Analytics Engineering Infrastructure
-- Script: sql/ab_test.sql
-- Dialect: Google BigQuery Standard SQL
-- Description: Rigorous A/B test statistical analysis for checkout optimization.
--              Evaluates SRM Chi-Square test, Two-Proportion Z-Test, 95% CIs,
--              and dimensional covariate balance.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. EXPERIMENT OVERVIEW: SAMPLE SIZES & CONVERSIONS
-- Tests: Control (Standard Multi-Step Checkout) vs Treatment (1-Page Checkout)
-- -----------------------------------------------------------------------------
WITH exp_summary AS (
  SELECT
    ab_variant,
    COUNT(DISTINCT session_id) AS sample_size,
    COUNT(DISTINCT CASE WHEN completed_purchase = 1 THEN session_id END) AS conversions,
    ROUND(
      COUNT(DISTINCT CASE WHEN completed_purchase = 1 THEN session_id END) * 1.0 / COUNT(DISTINCT session_id), 
      6
    ) AS conversion_rate
  FROM `pulsecart-prod.analytics_pulsecart.fct_ab_test`
  GROUP BY ab_variant
)
SELECT
  ab_variant,
  sample_size,
  conversions,
  conversion_rate,
  ROUND(conversion_rate * 100.0, 2) AS conversion_rate_pct
FROM exp_summary
ORDER BY ab_variant;


-- -----------------------------------------------------------------------------
-- 2. SAMPLE RATIO MISMATCH (SRM) CHI-SQUARE GOODNESS-OF-FIT TEST
-- Verifies 50/50 allocation balance.
-- Threshold: Chi2 p-value > 0.01 indicates SRM check PASSED.
-- -----------------------------------------------------------------------------
WITH variant_counts AS (
  SELECT
    COUNT(CASE WHEN ab_variant = 'control' THEN 1 END) AS n_control,
    COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END) AS n_treatment,
    COUNT(*) AS n_total,
    COUNT(*) / 2.0 AS expected_count
  FROM `pulsecart-prod.analytics_pulsecart.fct_ab_test`
),

srm_calculation AS (
  SELECT
    n_control,
    n_treatment,
    n_total,
    expected_count,
    ROUND(POW(n_control - expected_count, 2) / expected_count + 
          POW(n_treatment - expected_count, 2) / expected_count, 4) AS chi2_statistic
  FROM variant_counts
)
SELECT
  n_control,
  n_treatment,
  n_total,
  chi2_statistic,
  -- Critical value for Chi-Square df=1 at alpha=0.01 is 6.635
  CASE 
    WHEN chi2_statistic < 6.635 THEN 'PASS: No SRM Detected (Allocation Balanced)'
    ELSE 'FAIL: Sample Ratio Mismatch Detected (Invalid Experiment)'
  END AS srm_verdict
FROM srm_calculation;


-- -----------------------------------------------------------------------------
-- 3. TWO-PROPORTION Z-TEST & 95% CONFIDENCE INTERVALS (BIGQUERY SQL)
-- Hypothesis:
--   H0: p_treatment = p_control
--   H1: p_treatment != p_control
-- -----------------------------------------------------------------------------
WITH metrics AS (
  SELECT
    COUNT(CASE WHEN ab_variant = 'control' THEN 1 END) AS n_c,
    COUNT(CASE WHEN ab_variant = 'control' AND completed_purchase = 1 THEN 1 END) AS x_c,
    COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END) AS n_t,
    COUNT(CASE WHEN ab_variant = 'treatment' AND completed_purchase = 1 THEN 1 END) AS x_t
  FROM `pulsecart-prod.analytics_pulsecart.fct_ab_test`
),

rates AS (
  SELECT
    n_c,
    x_c,
    x_c * 1.0 / n_c AS p_c,
    n_t,
    x_t,
    x_t * 1.0 / n_t AS p_t,
    (x_c + x_t) * 1.0 / (n_c + n_t) AS p_pooled
  FROM metrics
),

test_stats AS (
  SELECT
    n_c,
    x_c,
    p_c,
    n_t,
    x_t,
    p_t,
    (p_t - p_c) AS absolute_lift,
    (p_t - p_c) / p_c AS relative_lift,
    -- Pooled Standard Error for Hypothesis Testing
    SQRT(p_pooled * (1.0 - p_pooled) * (1.0 / n_c + 1.0 / n_t)) AS se_pooled,
    -- Unpooled Standard Error for Confidence Intervals
    SQRT((p_c * (1.0 - p_c) / n_c) + (p_t * (1.0 - p_t) / n_t)) AS se_unpooled
  FROM rates
)
SELECT
  n_c AS control_sessions,
  x_c AS control_conversions,
  ROUND(p_c * 100.0, 2) AS control_conversion_rate_pct,
  n_t AS treatment_sessions,
  x_t AS treatment_conversions,
  ROUND(p_t * 100.0, 2) AS treatment_conversion_rate_pct,
  
  -- Effect Sizes
  ROUND(absolute_lift * 100.0, 2) AS absolute_lift_pct_pts,
  ROUND(relative_lift * 100.0, 2) AS relative_lift_pct,
  
  -- Test Statistic
  ROUND(absolute_lift / se_pooled, 4) AS z_score,
  
  -- 95% Confidence Interval for Absolute Lift (z_crit = 1.95996)
  ROUND((absolute_lift - 1.95996 * se_unpooled) * 100.0, 2) AS ci_abs_lower_pct,
  ROUND((absolute_lift + 1.95996 * se_unpooled) * 100.0, 2) AS ci_abs_upper_pct,
  
  -- 95% Confidence Interval for Relative Lift (Delta Method: SE_rel = SE_unpooled / p_c)
  ROUND(((p_t - p_c) / p_c - 1.95996 * (se_unpooled / p_c)) * 100.0, 2) AS ci_rel_lower_pct,
  ROUND(((p_t - p_c) / p_c + 1.95996 * (se_unpooled / p_c)) * 100.0, 2) AS ci_rel_upper_pct,
  
  -- Statistical Decision (alpha = 0.05, critical z = 1.96)
  CASE 
    WHEN ABS(absolute_lift / se_pooled) >= 1.96 THEN 'REJECT H0: Statistically Significant (p < 0.05)'
    ELSE 'FAIL TO REJECT H0: Not Statistically Significant'
  END AS statistical_conclusion
FROM test_stats;


-- -----------------------------------------------------------------------------
-- 4. COVARIATE BALANCE CHECK: DEVICE DISTRIBUTION
-- Verifies no confounding bias between control and treatment across devices.
-- -----------------------------------------------------------------------------
SELECT
  device_type,
  COUNT(CASE WHEN ab_variant = 'control' THEN 1 END) AS control_sessions,
  COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END) AS treatment_sessions,
  ROUND(COUNT(CASE WHEN ab_variant = 'control' THEN 1 END) * 100.0 / SUM(COUNT(CASE WHEN ab_variant = 'control' THEN 1 END)) OVER (), 2) AS control_device_share_pct,
  ROUND(COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END) * 100.0 / SUM(COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END)) OVER (), 2) AS treatment_device_share_pct,
  
  -- Subgroup conversion rates
  ROUND(SAFE_DIVIDE(COUNT(CASE WHEN ab_variant = 'control' AND completed_purchase = 1 THEN 1 END) * 100.0, COUNT(CASE WHEN ab_variant = 'control' THEN 1 END)), 2) AS control_conv_rate_pct,
  ROUND(SAFE_DIVIDE(COUNT(CASE WHEN ab_variant = 'treatment' AND completed_purchase = 1 THEN 1 END) * 100.0, COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END)), 2) AS treatment_conv_rate_pct
FROM `pulsecart-prod.analytics_pulsecart.fct_ab_test`
GROUP BY device_type
ORDER BY device_type;


-- -----------------------------------------------------------------------------
-- 5. TEMPORAL STABILITY: DAILY CONVERSION RATE AND CUMULATIVE LIFT
-- -----------------------------------------------------------------------------
WITH daily_rates AS (
  SELECT
    session_date,
    COUNT(CASE WHEN ab_variant = 'control' THEN 1 END) AS daily_control_n,
    COUNT(CASE WHEN ab_variant = 'control' AND completed_purchase = 1 THEN 1 END) AS daily_control_conv,
    COUNT(CASE WHEN ab_variant = 'treatment' THEN 1 END) AS daily_treatment_n,
    COUNT(CASE WHEN ab_variant = 'treatment' AND completed_purchase = 1 THEN 1 END) AS daily_treatment_conv
  FROM `pulsecart-prod.analytics_pulsecart.fct_ab_test`
  GROUP BY session_date
)
SELECT
  session_date,
  daily_control_n,
  daily_control_conv,
  ROUND(daily_control_conv * 100.0 / daily_control_n, 2) AS daily_control_conv_rate,
  daily_treatment_n,
  daily_treatment_conv,
  ROUND(daily_treatment_conv * 100.0 / daily_treatment_n, 2) AS daily_treatment_conv_rate,
  ROUND((daily_treatment_conv * 1.0 / daily_treatment_n - daily_control_conv * 1.0 / daily_control_n) * 100.0 / (daily_control_conv * 1.0 / daily_control_n), 2) AS daily_relative_lift_pct
FROM daily_rates
ORDER BY session_date;
