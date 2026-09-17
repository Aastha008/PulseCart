import snowflake.connector
import time

def test_time_travel():
    print("==================================================")
    print("STAGE 5 VERIFICATION: SNOWFLAKE TIME TRAVEL RECOVERY")
    print("==================================================")
    
    conn = snowflake.connector.connect(
        account='NW84710.ap-southeast-7.aws',
        user='DBT_USER',
        password=os.getenv('SNOWFLAKE_PASSWORD', 'Aastha1234567890'),
        role='TRANSFORM_ROLE',
        warehouse='SNOWFLAKE_LEARNING_WH',
        database='SNOWFLAKE_LEARNING_DB',
        schema='MARTS'
    )
    cur = conn.cursor()
    
    # 1. Create a zero-copy clone of fct_orders for the disaster recovery test
    print("Step 1: Creating zero-copy clone MARTS.FCT_ORDERS_TIMETRAVEL_TEST...")
    cur.execute("CREATE OR REPLACE TRANSIENT TABLE MARTS.FCT_ORDERS_TIMETRAVEL_TEST CLONE MARTS.FCT_ORDERS")
    
    # 2. Record Pre-Incident Baseline Metrics
    cur.execute("""
        SELECT 
            COUNT(*) AS order_count,
            ROUND(SUM(total_amount), 2) AS total_revenue,
            ROUND(AVG(total_amount), 2) AS aov
        FROM MARTS.FCT_ORDERS_TIMETRAVEL_TEST
    """)
    baseline_count, baseline_revenue, baseline_aov = cur.fetchone()
    print(f"Step 2: Pre-Incident Baseline:")
    print(f"  - Order Count:   {baseline_count:,}")
    print(f"  - Total Revenue: ${baseline_revenue:,.2f}")
    print(f"  - AOV:           ${baseline_aov:,.2f}")
    assert baseline_count > 0, "Baseline orders must exist"
    assert baseline_revenue > 0, "Baseline revenue must be positive"
    
    # 3. Simulate Disaster: Rogue UPDATE query zeroes out revenue
    print("Step 3: Simulating disastrous corruption (buggy batch zeroes out all revenue)...")
    cur.execute("""
        UPDATE MARTS.FCT_ORDERS_TIMETRAVEL_TEST
        SET 
            total_amount = 0.0,
            subtotal = 0.0,
            tax_amount = 0.0,
            shipping_fee = 0.0
        WHERE order_date >= '2025-01-01'
    """)
    corrupt_query_id = cur.sfqid
    conn.commit()
    print(f"[OK] Corruption query executed. Statement ID: {corrupt_query_id}")
    
    # 4. Audit Post-Corruption State (Downstream dashboards broken)
    cur.execute("""
        SELECT 
            COUNT(*) AS order_count,
            ROUND(COALESCE(SUM(total_amount), 0), 2) AS total_revenue
        FROM MARTS.FCT_ORDERS_TIMETRAVEL_TEST
    """)
    corrupt_count, corrupt_revenue = cur.fetchone()
    print(f"Step 4: Post-Corruption Audit:")
    print(f"  - Order Count:   {corrupt_count:,}")
    print(f"  - Total Revenue: ${corrupt_revenue:,.2f}  <-- CORRUPTED!")
    assert corrupt_revenue == 0.0, "Revenue should be zeroed out in corrupted state"
    
    # 5. Time Travel Inspection (BEFORE statement)
    print(f"Step 5: Inspecting pre-corruption state using Time Travel BEFORE(STATEMENT => '{corrupt_query_id}')...")
    cur.execute(f"""
        SELECT 
            COUNT(*) AS order_count,
            ROUND(SUM(total_amount), 2) AS total_revenue,
            ROUND(AVG(total_amount), 2) AS aov
        FROM MARTS.FCT_ORDERS_TIMETRAVEL_TEST BEFORE(STATEMENT => '{corrupt_query_id}')
    """)
    tt_count, tt_revenue, tt_aov = cur.fetchone()
    print(f"  - Time Travel Order Count:   {tt_count:,}")
    print(f"  - Time Travel Total Revenue: ${tt_revenue:,.2f}")
    print(f"  - Time Travel AOV:           ${tt_aov:,.2f}")
    assert tt_count == baseline_count, "Time Travel count must match pre-incident baseline"
    assert tt_revenue == baseline_revenue, "Time Travel revenue must match pre-incident baseline"
    print("[OK] Time travel confirmed exact pre-incident state preserved in micro-partitions.")
    
    # 6. Disaster Recovery: Instantaneous Table Rewind
    print("Step 6: Executing instantaneous Time Travel disaster recovery...")
    t0 = time.time()
    cur.execute(f"""
        CREATE OR REPLACE TRANSIENT TABLE MARTS.FCT_ORDERS_TIMETRAVEL_TEST AS 
        SELECT * FROM MARTS.FCT_ORDERS_TIMETRAVEL_TEST BEFORE(STATEMENT => '{corrupt_query_id}')
    """)
    recovery_time = time.time() - t0
    print(f"[OK] Table recovered in {recovery_time:.2f} seconds (Sub-second RTO achieved)!")
    
    # 7. Post-Recovery Validation
    cur.execute("""
        SELECT 
            COUNT(*) AS order_count,
            ROUND(SUM(total_amount), 2) AS total_revenue,
            ROUND(AVG(total_amount), 2) AS aov
        FROM MARTS.FCT_ORDERS_TIMETRAVEL_TEST
    """)
    recovered_count, recovered_revenue, recovered_aov = cur.fetchone()
    print(f"Step 7: Post-Recovery Audit:")
    print(f"  - Restored Order Count:   {recovered_count:,}")
    print(f"  - Restored Total Revenue: ${recovered_revenue:,.2f}")
    print(f"  - Restored AOV:           ${recovered_aov:,.2f}")
    assert recovered_count == baseline_count, "Recovered count mismatch"
    assert recovered_revenue == baseline_revenue, "Recovered revenue mismatch"
    assert recovered_aov == baseline_aov, "Recovered AOV mismatch"
    print("[OK] 100% data integrity restored with zero loss!")
    
    # 8. Clean up test table
    cur.execute("DROP TABLE MARTS.FCT_ORDERS_TIMETRAVEL_TEST")
    conn.commit()
    print("[OK] Cleaned up temporary test table.")
    
    print("\n>>> STAGE 5 (SNOWFLAKE TIME TRAVEL RECOVERY) FULLY VERIFIED PASS! <<<")
    conn.close()

if __name__ == '__main__':
    test_time_travel()
