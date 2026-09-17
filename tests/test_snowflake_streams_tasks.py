import snowflake.connector
import time

def test_streams_and_tasks():
    print("==================================================")
    print("STAGE 4 VERIFICATION: SNOWFLAKE STREAMS & TASKS")
    print("==================================================")
    
    conn = snowflake.connector.connect(
        account='NW84710.ap-southeast-7.aws',
        user='DBT_USER',
        password=os.getenv('SNOWFLAKE_PASSWORD', 'Aastha1234567890'),
        role='TRANSFORM_ROLE',
        warehouse='SNOWFLAKE_LEARNING_WH',
        database='SNOWFLAKE_LEARNING_DB',
        schema='STAGING'
    )
    cur = conn.cursor()
    
    # Clean up any leftover test data first
    cur.execute("DELETE FROM RAW_PULSECART.RAW_EVENTS WHERE EVENT_ID LIKE 'EVT-CDC-%'")
    conn.commit()

    # 1. Setup Stream and Staging Table
    print("Step 1: Setting up Stream on RAW_EVENTS and Target Table STG_EVENTS_CDC...")
    cur.execute("""
        CREATE OR REPLACE STREAM RAW_PULSECART.STREAM_RAW_EVENTS 
        ON TABLE RAW_PULSECART.RAW_EVENTS
        APPEND_ONLY = TRUE
    """)
    
    cur.execute("""
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
    """)
    
    cur.execute("""
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
            )
    """)
    print("[OK] Stream, Staging Table, and Task initialized.")
    
    # 2. Verify Stream has no data initially
    cur.execute("SELECT SYSTEM$STREAM_HAS_DATA('RAW_PULSECART.STREAM_RAW_EVENTS')")
    has_data_initial = cur.fetchone()[0]
    print(f"Step 2: Initial stream data check: SYSTEM$STREAM_HAS_DATA = {has_data_initial}")
    assert not has_data_initial, "Stream should be empty initially"
    
    # 3. Simulate Incoming Clickstream Events
    print("Step 3: Simulating 5 real-time incoming events inserted into RAW_EVENTS...")
    test_events = [
        ('EVT-CDC-99001', 'SES-000000001', 'USR-00004370', '2025-01-01 00:05:00', 'product_view', 'interaction', 2, '/product/p1', 'PRD-00001', 0.0),
        ('EVT-CDC-99002', 'SES-000000001', 'USR-00004370', '2025-01-01 00:06:00', 'add_to_cart', 'conversion', 3, '/cart', 'PRD-00001', 320.99),
        ('EVT-CDC-99003', 'SES-000000001', 'USR-00004370', '2025-01-01 00:07:00', 'checkout_started', 'funnel', 4, '/checkout', 'PRD-00001', 320.99),
        ('EVT-CDC-99004', 'SES-000000001', 'USR-00004370', '2025-01-01 00:08:00', 'payment_started', 'funnel', 5, '/payment', 'PRD-00001', 320.99),
        ('EVT-CDC-99005', 'SES-000000001', 'USR-00004370', '2025-01-01 00:09:00', 'purchase', 'conversion', 6, '/confirmation', 'PRD-00001', 320.99),
    ]
    cur.executemany("""
        INSERT INTO RAW_PULSECART.RAW_EVENTS (
            EVENT_ID, SESSION_ID, USER_ID, EVENT_TIMESTAMP, EVENT_NAME,
            EVENT_TYPE, STEP_NUMBER, PAGE_URL, PRODUCT_ID, CART_VALUE
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, test_events)
    conn.commit()
    print(f"[OK] Inserted {len(test_events)} events into RAW_PULSECART.RAW_EVENTS.")
    
    # 4. Verify Stream Detected the Changes (CDC)
    cur.execute("SELECT SYSTEM$STREAM_HAS_DATA('RAW_PULSECART.STREAM_RAW_EVENTS')")
    has_data_after = cur.fetchone()[0]
    print(f"Step 4: Post-insert stream check: SYSTEM$STREAM_HAS_DATA = {has_data_after}")
    assert has_data_after, "Stream should detect incoming records"
    
    cur.execute("SELECT COUNT(*), METADATA$ACTION FROM RAW_PULSECART.STREAM_RAW_EVENTS GROUP BY METADATA$ACTION")
    stream_counts = cur.fetchall()
    print(f"[OK] Stream CDC buffer state: {stream_counts}")
    
    # 5. Execute Task's CDC Ingestion Logic
    print("Step 5: Executing Task ingestion MERGE transaction...")
    cur.execute("""
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
            )
    """)
    conn.commit()
    
    # Check rows landed in STG_EVENTS_CDC
    cur.execute("SELECT COUNT(*) FROM STAGING.STG_EVENTS_CDC WHERE EVENT_ID LIKE 'EVT-CDC-%'")
    landed_count = cur.fetchone()[0]
    print(f"[OK] Records successfully landed in STAGING.STG_EVENTS_CDC: {landed_count}")
    assert landed_count == 5, f"Expected 5 records, found {landed_count}"
    
    # 6. Verify Stream offset consumed
    cur.execute("SELECT SYSTEM$STREAM_HAS_DATA('RAW_PULSECART.STREAM_RAW_EVENTS')")
    has_data_final = cur.fetchone()[0]
    print(f"Step 6: Stream offset check post-ingestion: SYSTEM$STREAM_HAS_DATA = {has_data_final}")
    assert not has_data_final, "Stream offset should be fully consumed after transaction commit"
    
    # 7. Clean up test events
    print("Step 7: Cleaning up test records...")
    cur.execute("DELETE FROM RAW_PULSECART.RAW_EVENTS WHERE EVENT_ID LIKE 'EVT-CDC-%'")
    cur.execute("DELETE FROM STAGING.STG_EVENTS_CDC WHERE EVENT_ID LIKE 'EVT-CDC-%'")
    conn.commit()
    print("[OK] Test cleanup completed.")
    
    print("\n>>> STAGE 4 (SNOWFLAKE STREAMS & TASKS) FULLY VERIFIED PASS! <<<")
    conn.close()

if __name__ == '__main__':
    test_streams_and_tasks()
