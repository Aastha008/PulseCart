-- ==============================================================================
-- PulseCart — Snowflake Real-Time CDC Pipeline via Streams & Tasks
-- Stage 4: Incremental Event Ingestion & Change Data Capture
-- ==============================================================================
-- 
-- TECHNICAL PROBLEM SOLVED:
-- 1. High-Watermark Batch Limitations:
--    Traditional dbt models use `WHERE event_timestamp > (SELECT MAX(...) FROM {{ this }})`.
--    This fails when:
--    - Events arrive late (network lag, offline mobile caching), permanently dropping data.
--    - Hard deletes or updates occur in the source (timestamp filter only detects new rows).
-- 2. Compute Efficiency:
--    Scanning 230K+ events on every scheduled batch run wastes warehouse credits even when
--    no new events arrived.
-- 3. The Snowflake Solution:
--    - STREAMS track change delta (CDC) via micro-partition metadata without duplicating table data.
--    - TASKS evaluate `SYSTEM$STREAM_HAS_DATA()` at sub-second intervals with ZERO compute cost
--      when idle (the warehouse only spins up if actual data is buffered).
-- ==============================================================================

USE DATABASE SNOWFLAKE_LEARNING_DB;
USE WAREHOUSE SNOWFLAKE_LEARNING_WH;

-- 1. CREATE APPEND-ONLY STREAM ON RAW CLICKSTREAM EVENTS
CREATE OR REPLACE STREAM RAW_PULSECART.STREAM_RAW_EVENTS 
ON TABLE RAW_PULSECART.RAW_EVENTS
APPEND_ONLY = TRUE
COMMENT = 'Tracks newly appended clickstream interaction events from external ingestion layer';

-- 2. CREATE TARGET INCREMENTAL STAGING TABLE
CREATE OR REPLACE TABLE STAGING.STG_EVENTS_CDC (
    event_id STRING PRIMARY KEY,
    session_id STRING,
    user_id STRING,
    event_timestamp TIMESTAMP_NTZ,
    event_date DATE,
    event_name STRING,
    event_type STRING,
    step_number INTEGER,
    page_url STRING,
    product_id STRING,
    cart_value NUMERIC(10,2),
    cdc_action STRING,
    ingested_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY (event_date, event_name)
COMMENT = 'Continuously hydrated staging table populated by Snowflake Task from Stream';

-- 3. INITIAL SEED (Backfill existing historical records from RAW_EVENTS)
INSERT INTO STAGING.STG_EVENTS_CDC (
    event_id, session_id, user_id, event_timestamp, event_date,
    event_name, event_type, step_number, page_url, product_id,
    cart_value, cdc_action, ingested_at
)
SELECT 
    TRIM(event_id) AS event_id,
    TRIM(session_id) AS session_id,
    TRIM(user_id) AS user_id,
    CAST(event_timestamp AS TIMESTAMP_NTZ) AS event_timestamp,
    CAST(event_timestamp AS DATE) AS event_date,
    LOWER(TRIM(event_name)) AS event_name,
    LOWER(TRIM(event_type)) AS event_type,
    CAST(step_number AS INTEGER) AS step_number,
    TRIM(page_url) AS page_url,
    NULLIF(TRIM(product_id), '') AS product_id,
    CAST(COALESCE(cart_value, 0.0) AS NUMERIC(10,2)) AS cart_value,
    'BACKFILL' AS cdc_action,
    CURRENT_TIMESTAMP() AS ingested_at
FROM RAW_PULSECART.RAW_EVENTS;

-- 4. CREATE SERVERLESS / WAREHOUSE AUTOMATION TASK
CREATE OR REPLACE TASK STAGING.TSK_INGEST_STG_EVENTS
    WAREHOUSE = 'SNOWFLAKE_LEARNING_WH'
    SCHEDULE = '1 MINUTE'
    WHEN SYSTEM$STREAM_HAS_DATA('RAW_PULSECART.STREAM_RAW_EVENTS')
AS
MERGE INTO STAGING.STG_EVENTS_CDC AS target
USING (
    SELECT 
        TRIM(event_id) AS event_id,
        TRIM(session_id) AS session_id,
        TRIM(user_id) AS user_id,
        CAST(event_timestamp AS TIMESTAMP_NTZ) AS event_timestamp,
        CAST(event_timestamp AS DATE) AS event_date,
        LOWER(TRIM(event_name)) AS event_name,
        LOWER(TRIM(event_type)) AS event_type,
        CAST(step_number AS INTEGER) AS step_number,
        TRIM(page_url) AS page_url,
        NULLIF(TRIM(product_id), '') AS product_id,
        CAST(COALESCE(cart_value, 0.0) AS NUMERIC(10,2)) AS cart_value,
        METADATA$ACTION AS cdc_action
    FROM RAW_PULSECART.STREAM_RAW_EVENTS
    WHERE METADATA$ACTION = 'INSERT'
) AS src
ON target.event_id = src.event_id
WHEN MATCHED THEN
    UPDATE SET 
        target.session_id = src.session_id,
        target.user_id = src.user_id,
        target.event_timestamp = src.event_timestamp,
        target.event_date = src.event_date,
        target.event_name = src.event_name,
        target.event_type = src.event_type,
        target.step_number = src.step_number,
        target.page_url = src.page_url,
        target.product_id = src.product_id,
        target.cart_value = src.cart_value,
        target.cdc_action = src.cdc_action,
        target.ingested_at = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
    INSERT (
        event_id, session_id, user_id, event_timestamp, event_date,
        event_name, event_type, step_number, page_url, product_id,
        cart_value, cdc_action, ingested_at
    )
    VALUES (
        src.event_id, src.session_id, src.user_id, src.event_timestamp, src.event_date,
        src.event_name, src.event_type, src.step_number, src.page_url, src.product_id,
        src.cart_value, src.cdc_action, CURRENT_TIMESTAMP()
    );

-- 5. RESUME TASK FOR AUTOMATIC EXECUTION (Optional in dev, triggered via EXECUTE TASK)
-- ALTER TASK STAGING.TSK_INGEST_STG_EVENTS RESUME;
