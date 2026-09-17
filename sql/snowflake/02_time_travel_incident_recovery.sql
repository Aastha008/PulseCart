-- ==============================================================================
-- PulseCart — Snowflake Time Travel & Disaster Recovery Architecture
-- Stage 5: Accidental Corruption & Sub-Second RTO Recovery Scenario
-- ==============================================================================
--
-- INCIDENT SCENARIO:
-- During a schema migration or rogue operational maintenance run, an unconstrained
-- UPDATE query is executed on `MARTS.FCT_ORDERS`, zeroing out total_amount and subtotal
-- across all orders. Downstream Power BI reports show $0 revenue, triggering a P1 incident.
--
-- RECOVERY COMPARISON:
-- Traditional RDBMS / BigQuery without partition snapshots:
-- - Requires restoring full table from cold backups or replaying days of raw event logs.
-- - High RTO (Recovery Time Objective): hours of pipeline downtime.
-- Snowflake Time Travel:
-- - Queries the immutable micro-partition state prior to the offending query ID.
-- - Sub-second RTO via zero-copy clone or statement-level Time Travel rewind.
-- ==============================================================================

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;

-- 1. BASELINE AUDIT CHECK (Pre-Incident State)
SELECT 
    COUNT(*) AS total_orders,
    ROUND(SUM(total_amount), 2) AS baseline_revenue,
    ROUND(AVG(total_amount), 2) AS baseline_aov
FROM MARTS.FCT_ORDERS;

-- 2. SIMULATED DISASTER: Malformed Update / Corruption
-- (Simulates a buggy ETL pipeline setting revenue to 0)
UPDATE MARTS.FCT_ORDERS
SET 
    total_amount = 0.0,
    subtotal = 0.0,
    tax_amount = 0.0,
    shipping_fee = 0.0
WHERE order_date >= '2025-01-01';

-- 3. AUDIT THE CORRUPTION (Post-Incident Verification)
SELECT 
    COUNT(*) AS total_orders,
    ROUND(SUM(total_amount), 2) AS corrupted_revenue,
    ROUND(AVG(total_amount), 2) AS corrupted_aov
FROM MARTS.FCT_ORDERS;
-- Output: corrupted_revenue = 0.00! Downstream dashboards broken.

-- 4. LOCATE THE OFFENDING QUERY_ID IN ACCOUNT_USAGE / QUERY_HISTORY
-- SET bad_query_id = (SELECT QUERY_ID FROM TABLE(INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION()) 
--                     WHERE QUERY_TEXT LIKE '%UPDATE MARTS.FCT_ORDERS SET total_amount = 0.0%' 
--                     ORDER BY START_TIME DESC LIMIT 1);

-- 5. TIME TRAVEL INSPECTION (Query state BEFORE corruption)
-- SELECT 
--     COUNT(*) AS pre_corrupt_count,
--     ROUND(SUM(total_amount), 2) AS pre_corrupt_revenue
-- FROM MARTS.FCT_ORDERS BEFORE(STATEMENT => $bad_query_id);

-- 6. DISASTER RECOVERY: Zero-Copy Instantaneous Table Restoration
-- CREATE OR REPLACE TABLE MARTS.FCT_ORDERS AS 
-- SELECT * FROM MARTS.FCT_ORDERS BEFORE(STATEMENT => $bad_query_id);

-- 7. POST-RECOVERY VALIDATION AUDIT
-- SELECT 
--     COUNT(*) AS restored_orders,
--     ROUND(SUM(total_amount), 2) AS restored_revenue,
--     ROUND(AVG(total_amount), 2) AS restored_aov
-- FROM MARTS.FCT_ORDERS;
