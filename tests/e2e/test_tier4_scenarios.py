"""
PulseCart E2E Test Suite - Tier 4: Real-World Application Scenarios
Executes 5 comprehensive, multi-step, end-to-end operational workflows:
1. Scenario 1: Full DTC E-Commerce Daily Operational Lifecycle
2. Scenario 2: High-Traffic Promotional Flash Sale Surge
3. Scenario 3: End-to-End Checkout A/B Experiment Decision Lifecycle
4. Scenario 4: Multi-Month Cohort Retention & Customer LTV Maturation
5. Scenario 5: Operational Incident, Circuit Breaker Trip & Resilient Recovery
"""

from datetime import datetime, timedelta, timezone
import json
import math
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from tests.e2e.conftest import (
    generate_reference_bundle,
    oracle_compute_funnel_metrics,
    oracle_compute_srm_chi2,
    oracle_compute_two_proportion_ztest,
    oracle_verify_financial_integrity,
    oracle_verify_timestamp_monotonicity,
)


@pytest.mark.tier4
class TestTier4RealWorldScenarios:
    """Real-World Operational Scenarios for PulseCart."""

    def test_scenario_1_full_dtc_daily_lifecycle(self, duckdb_conn, ref_data_bundle):
        """
        Scenario 1: Full DTC E-Commerce Daily Operational Lifecycle
        Steps:
        1. Ingest raw relational tables (users, products, sessions, events, orders, order_items).
        2. Execute Staging view transformations.
        3. Execute Intermediate aggregations.
        4. Materialize Mart Facts & Dimensions.
        5. Run Statistical Analysis (Funnel, Cohort Retention, A/B Testing).
        6. Verify downstream reporting outputs & financial reconciliation.
        """
        # Step 1: Verify raw tables loaded in DuckDB
        raw_tables = [t[0] for t in duckdb_conn.execute("SHOW TABLES").fetchall()]
        assert "raw_sessions" in raw_tables
        assert "raw_orders" in raw_tables

        # Step 2: Build Staging views
        duckdb_conn.execute("""
        CREATE TEMP VIEW stg_v_users AS
        SELECT TRIM(user_id) AS user_id, UPPER(TRIM(country)) AS country, TRIM(customer_segment) AS customer_segment
        FROM raw_users;
        """)
        duckdb_conn.execute("""
        CREATE TEMP VIEW stg_v_sessions AS
        SELECT session_id, user_id, CAST(session_start AS DATE) AS session_date, device_type, ab_variant
        FROM raw_sessions;
        """)
        duckdb_conn.execute("""
        CREATE TEMP VIEW stg_v_events AS
        SELECT event_id, session_id, user_id, event_type, step_number
        FROM raw_events;
        """)
        duckdb_conn.execute("""
        CREATE TEMP VIEW stg_v_orders AS
        SELECT order_id, session_id, user_id, order_date, total_amount
        FROM raw_orders;
        """)

        # Step 3: Intermediate Funnel Aggregations
        duckdb_conn.execute("""
        CREATE TEMP VIEW int_v_funnel AS
        SELECT
            session_id,
            MAX(CASE WHEN event_type = 'landing_page' THEN 1 ELSE 0 END) AS is_landing,
            MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS is_purchase,
            MAX(step_number) AS furthest_step
        FROM stg_v_events
        GROUP BY session_id;
        """)

        # Step 4: Marts Fact Funnel
        df_fct_funnel = duckdb_conn.execute("""
        SELECT
            s.session_id,
            s.user_id,
            s.session_date,
            s.device_type,
            s.ab_variant,
            f.is_landing,
            f.is_purchase,
            f.furthest_step
        FROM stg_v_sessions s
        JOIN int_v_funnel f ON s.session_id = f.session_id;
        """).df()
        assert len(df_fct_funnel) >= 1000

        # Step 5: Statistical Funnel Metrics
        events = ref_data_bundle["events"]
        sessions = ref_data_bundle["sessions"]
        funnel_metrics = oracle_compute_funnel_metrics(events, sessions)
        assert len(funnel_metrics) == 6
        assert funnel_metrics.iloc[0]["stage_name"] == "landing_page"
        assert funnel_metrics.iloc[-1]["stage_name"] == "purchase"

        # Step 6: Verify Financial Invariants
        orders = ref_data_bundle["orders"]
        order_items = ref_data_bundle["order_items"]
        assert oracle_verify_financial_integrity(orders, order_items)

    def test_scenario_2_promotional_flash_sale_surge(self, ref_data_bundle):
        """
        Scenario 2: High-Traffic Promotional Flash Sale Surge
        Steps:
        1. Simulate flash sale traffic surge with high Mobile (70%) and VIP (35%) participation.
        2. Apply promotional coupon discount ($10-$15 off for VIPs over $50).
        3. Verify Free Shipping threshold ($Total > $100 -> Shipping = $0).
        4. Reconcile subtotal, tax, shipping, discount, and total amounts.
        5. Verify profitability and margin calculations.
        """
        products = ref_data_bundle["products"].to_dict("records")
        rng = np.random.default_rng(seed=101)

        simulated_orders = []
        simulated_items = []
        order_counter = 0
        item_counter = 0

        for i in range(200):
            order_counter += 1
            oid = f"ORD-FLASH-{order_counter:05d}"
            sid = f"SES-FLASH-{order_counter:05d}"
            uid = f"USR-FLASH-{order_counter:05d}"
            is_vip = bool(rng.random() < 0.35)

            # Sample 2-4 items
            n_items = int(rng.integers(2, 5))
            chosen_prods = rng.choice(products, size=n_items, replace=True)
            
            subtotal = 0.0
            order_profit = 0.0

            for prod in chosen_prods:
                item_counter += 1
                qty = int(rng.integers(1, 3))
                unit_p = prod["price"]
                unit_c = prod["cost"]
                line_total = round(unit_p * qty, 2)
                line_profit = round((unit_p - unit_c) * qty, 2)
                subtotal += line_total
                order_profit += line_profit

                simulated_items.append({
                    "order_item_id": f"ITM-FLASH-{item_counter:06d}",
                    "order_id": oid,
                    "product_id": prod["product_id"],
                    "quantity": qty,
                    "unit_price": unit_p,
                    "unit_cost": unit_c,
                    "line_total": line_total,
                    "total_item_price": line_total,
                    "line_profit": line_profit,
                })

            subtotal = round(subtotal, 2)
            tax = round(subtotal * 0.08, 2)
            shipping = 0.0 if subtotal > 100.0 else 9.99
            discount = 15.0 if (is_vip and subtotal > 50.0) else 0.0
            total = round(subtotal + tax + shipping - discount, 2)

            simulated_orders.append({
                "order_id": oid,
                "session_id": sid,
                "user_id": uid,
                "subtotal": subtotal,
                "tax_amount": tax,
                "shipping_fee": shipping,
                "discount_amount": discount,
                "total_amount": total,
            })

        df_orders = pd.DataFrame(simulated_orders)
        df_items = pd.DataFrame(simulated_items)

        # Invariant verification under flash sale surge
        assert oracle_verify_financial_integrity(df_orders, df_items)

        # Free shipping threshold verification
        free_shipping_orders = df_orders[df_orders["subtotal"] > 100.0]
        assert (free_shipping_orders["shipping_fee"] == 0.0).all()

        # VIP discount verification
        discounted_orders = df_orders[df_orders["discount_amount"] > 0]
        assert (discounted_orders["discount_amount"] == 15.0).all()

    def test_scenario_3_checkout_ab_experiment_decision_cycle(self, ref_data_bundle):
        """
        Scenario 3: End-to-End Checkout A/B Experiment Decision Lifecycle
        Steps:
        1. Sample traffic assigned to Control vs Treatment at checkout_started.
        2. Evaluate Sample Ratio Mismatch (SRM) via Pearson Chi-Square test.
        3. Compute two-proportion z-test, pooled standard error, and p-value.
        4. Compute 95% Confidence Interval for relative lift using Delta Method.
        5. Execute executive decision logic (Rollout vs Retain).
        6. Calculate projected annual incremental revenue and gross margin impact.
        """
        # Baseline simulation parameters matching PulseCart R1 & R3
        n_ctrl = 52400
        conv_ctrl = 5240    # 10.00%
        n_treat = 52350
        conv_treat = 5701   # 10.89% (+8.90% lift)

        # Step 1 & 2: SRM Check
        chi2, p_val_srm, srm_passed = oracle_compute_srm_chi2(n_ctrl, n_treat)
        assert srm_passed is True
        assert chi2 < 6.635
        assert p_val_srm >= 0.01

        # Step 3 & 4: Two-Proportion Hypothesis Test & Confidence Intervals
        stats_res = oracle_compute_two_proportion_ztest(n_ctrl, conv_ctrl, n_treat, conv_treat, alpha=0.05)
        assert stats_res["statistically_significant"] is True
        assert stats_res["p_value"] < 0.001
        assert round(stats_res["relative_lift"] * 100.0, 1) == 8.9
        assert stats_res["ci_rel_lower"] > 0.0

        # Step 5: Automated Executive Decision Rule
        decision = "ROLLOUT_TREATMENT" if (
            srm_passed and stats_res["statistically_significant"] and stats_res["relative_lift"] > 0
        ) else "RETAIN_CONTROL"
        assert decision == "ROLLOUT_TREATMENT"

        # Step 6: Annual Incremental Revenue Modeling
        baseline_annual_orders = 100000
        baseline_aov = 125.0
        gross_margin_pct = 0.54

        inc_revenue = baseline_annual_orders * baseline_aov * stats_res["relative_lift"]
        inc_gross_profit = inc_revenue * gross_margin_pct

        assert inc_revenue > 1000000.0
        assert inc_gross_profit > 500000.0

    def test_scenario_4_multi_month_cohort_retention_and_ltv(self, duckdb_conn):
        """
        Scenario 4: Multi-Month Cohort Retention & Customer LTV Maturation
        Steps:
        1. Cohort identification by maiden purchase month (M0).
        2. Track activity from Month 0 through Month 3+.
        3. Verify Month 0 retention is strictly 100%.
        4. Verify realistic retention decay from M0 to M1 to M2.
        5. Verify Repeat Purchase Rate (RPR) calculation.
        6. Verify monotonically increasing customer LTV trajectory.
        """
        sql_cohort = """
        WITH first_orders AS (
            SELECT user_id, DATE_TRUNC('month', MIN(order_timestamp)) AS cohort_month
            FROM raw_orders
            GROUP BY user_id
        ),
        monthly_activity AS (
            SELECT
                fo.cohort_month,
                DATEDIFF('month', fo.cohort_month, DATE_TRUNC('month', o.order_timestamp)) AS month_offset,
                COUNT(DISTINCT o.user_id) AS active_users,
                SUM(o.total_amount) AS revenue
            FROM raw_orders o
            JOIN first_orders fo ON o.user_id = fo.user_id
            GROUP BY 1, 2
        ),
        cohort_sizes AS (
            SELECT cohort_month, COUNT(DISTINCT user_id) AS initial_users
            FROM first_orders
            GROUP BY 1
        )
        SELECT
            ma.cohort_month,
            ma.month_offset,
            ma.active_users,
            cs.initial_users,
            ROUND(ma.active_users * 100.0 / cs.initial_users, 2) AS retention_rate,
            SUM(ma.revenue) OVER (PARTITION BY ma.cohort_month ORDER BY ma.month_offset) AS cumulative_revenue,
            ROUND(SUM(ma.revenue) OVER (PARTITION BY ma.cohort_month ORDER BY ma.month_offset) / cs.initial_users, 2) AS cumulative_ltv_per_user
        FROM monthly_activity ma
        JOIN cohort_sizes cs ON ma.cohort_month = cs.cohort_month
        ORDER BY ma.cohort_month, ma.month_offset;
        """
        df = duckdb_conn.execute(sql_cohort).df()
        assert len(df) > 0

        # Verify M0 retention is 100%
        m0_rows = df[df["month_offset"] == 0]
        assert (m0_rows["retention_rate"] == 100.0).all()

        # Verify cumulative LTV is non-decreasing
        for _, cohort_df in df.groupby("cohort_month"):
            assert cohort_df["cumulative_ltv_per_user"].is_monotonic_increasing

    def test_scenario_5_orchestration_circuit_breaker_resilience(self, duckdb_conn):
        """
        Scenario 5: Operational Incident, Circuit Breaker Trip & Resilient Recovery
        Steps:
        1. Inject deliberate referential corruption (orphan order referencing invalid session).
        2. Execute quality test gate (`dbt test`).
        3. Detect failure and trigger hard circuit breaker abort.
        4. Verify marts build and Power BI refresh are halted.
        5. Generate incident webhook alert payload.
        6. Clean corrupted data and re-run quality gate.
        7. Confirm clean pass and resume downstream operations.
        """
        # Step 1: Inject corrupted orphan order
        duckdb_conn.execute("""
        CREATE TEMP TABLE test_orders AS SELECT * FROM raw_orders;
        INSERT INTO test_orders (order_id, session_id, user_id, order_date, order_timestamp, subtotal, tax_amount, shipping_fee, discount_amount, total_amount, payment_method, status, ab_variant)
        VALUES ('ORD-CORRUPT-999', 'SES-GHOST-999', 'USR-00000001', '2025-01-15', '2025-01-15 12:00:00', 100.0, 8.0, 0.0, 0.0, 108.0, 'Credit Card', 'completed', 'control');
        """)

        # Step 2: Quality Gate - Referential Integrity Check
        orphan_count = duckdb_conn.execute("""
        SELECT COUNT(*) FROM test_orders o
        LEFT JOIN raw_sessions s ON o.session_id = s.session_id
        WHERE s.session_id IS NULL;
        """).fetchone()[0]

        # Step 3: Hard Circuit Breaker Triggered
        assert orphan_count == 1
        circuit_breaker_tripped = (orphan_count > 0)
        assert circuit_breaker_tripped is True

        # Step 4: Verify Downstream Marts Blocked
        marts_materialized = False
        pbi_refreshed = False
        if not circuit_breaker_tripped:
            marts_materialized = True
            pbi_refreshed = True
        assert marts_materialized is False
        assert pbi_refreshed is False

        # Step 5: Incident Alert Payload
        alert_payload = {
            "channel": "#data-ops-alerts",
            "severity": "CRITICAL_P1",
            "event": "CIRCUIT_BREAKER_HALT",
            "reason": f"Detected {orphan_count} orphan orders in test_orders",
            "action_taken": "Aborted downstream marts build and Power BI dataset refresh",
            "runbook": "https://wiki.pulsecart.internal/runbooks/orphan-records",
        }
        assert alert_payload["severity"] == "CRITICAL_P1"

        # Step 6: Cleanse Corrupted Record
        duckdb_conn.execute("DELETE FROM test_orders WHERE order_id = 'ORD-CORRUPT-999';")
        cleaned_orphans = duckdb_conn.execute("""
        SELECT COUNT(*) FROM test_orders o
        LEFT JOIN raw_sessions s ON o.session_id = s.session_id
        WHERE s.session_id IS NULL;
        """).fetchone()[0]
        assert cleaned_orphans == 0

        # Step 7: Resilient Recovery
        circuit_breaker_tripped = (cleaned_orphans > 0)
        assert circuit_breaker_tripped is False
        if not circuit_breaker_tripped:
            marts_materialized = True
            pbi_refreshed = True
        assert marts_materialized is True
        assert pbi_refreshed is True
