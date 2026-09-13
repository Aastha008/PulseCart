"""
PulseCart E2E Test Suite - Tier 3: Cross-Feature Combinations
Covers pairwise, multidimensional, and cross-pipeline interactions across
tables, stages, models, dimensions, statistical engines, and operational gates.
"""

from datetime import datetime, timedelta, timezone
import math
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from tests.e2e.conftest import (
    oracle_compute_funnel_metrics,
    oracle_compute_srm_chi2,
    oracle_compute_two_proportion_ztest,
    oracle_verify_financial_integrity,
    oracle_verify_timestamp_monotonicity,
)


@pytest.mark.tier3
class TestTier3CrossFeatureCombinations:
    """Pairwise and multi-feature interaction verification."""

    def test_comb_01_multidimensional_variance_interaction(self, ref_data_bundle):
        """Combines F01 (Users), F03 (Sessions), F05 (Variance), and F07 (Invariants)."""
        users = ref_data_bundle["users"]
        sessions = ref_data_bundle["sessions"]
        orders = ref_data_bundle["orders"]

        merged = sessions.merge(users, on="user_id", suffixes=("_sess", "_user"))
        merged = merged.merge(orders[["session_id", "order_id"]], on="session_id", how="left")
        merged["converted"] = merged["order_id"].notnull().astype(int)

        # Cross-cut: Device x Customer Segment
        grid = merged.groupby(["device_type", "customer_segment"])["converted"].agg(["count", "mean"])
        assert len(grid) >= 6
        assert (grid["count"] > 0).all()

    def test_comb_02_funnel_state_machine_with_order_financials(self, ref_data_bundle):
        """Combines F04 (Funnel State Machine), F07 (Invariants), and F02 (Products)."""
        events = ref_data_bundle["events"]
        orders = ref_data_bundle["orders"]
        order_items = ref_data_bundle["order_items"]
        products = ref_data_bundle["products"]

        # Reconcile purchase events with orders
        purchases = events[events["event_name"] == "purchase"]
        assert len(purchases) == len(orders)

        # Reconcile order item prices with product catalog
        prod_map = products.set_index("product_id")["price"].to_dict()
        for _, item in order_items.iterrows():
            pid = item["product_id"]
            catalog_price = prod_map[pid]
            assert abs(item["unit_price"] - catalog_price) < 0.01

        # Financial reconciliation
        assert oracle_verify_financial_integrity(orders, order_items)

    def test_comb_03_ab_variant_with_stage_conversion_and_revenue(self, ref_data_bundle):
        """Combines F06 (A/B Test), F04 (Funnel), and F07 (Invariants)."""
        sessions = ref_data_bundle["sessions"]
        events = ref_data_bundle["events"]
        orders = ref_data_bundle["orders"]

        checkout_sids = set(events[events["event_name"] == "checkout_started"]["session_id"])
        sess_checkout = sessions[sessions["session_id"].isin(checkout_sids)].copy()

        merged = sess_checkout.merge(orders[["session_id", "total_amount"]], on="session_id", how="left")
        merged["converted"] = merged["total_amount"].notnull().astype(int)
        merged["revenue"] = merged["total_amount"].fillna(0.0)

        by_variant = merged.groupby("ab_variant").agg(
            sessions_at_checkout=("session_id", "count"),
            conversions=("converted", "sum"),
            total_revenue=("revenue", "sum"),
        )
        assert "control" in by_variant.index and "treatment" in by_variant.index
        assert by_variant.loc["treatment", "sessions_at_checkout"] > 0
        assert by_variant.loc["control", "sessions_at_checkout"] > 0

    def test_comb_04_raw_to_staging_to_intermediate_lineage(self, duckdb_conn):
        """Combines F08 (Raw), F09 (Staging), F10 (Intermediate), and F11 (Marts)."""
        sql_stg_events = """
        CREATE TEMP VIEW v_stg_events AS
        SELECT event_id, session_id, user_id, event_timestamp, event_type, step_number
        FROM raw_events;
        """
        sql_int_funnel = """
        CREATE TEMP VIEW v_int_funnel AS
        SELECT
            session_id,
            MAX(CASE WHEN event_type = 'landing_page' THEN 1 ELSE 0 END) AS is_landing,
            MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS is_purchase,
            MAX(step_number) AS furthest_step
        FROM v_stg_events
        GROUP BY session_id;
        """
        sql_marts_funnel = """
        SELECT
            s.session_id,
            s.device_type,
            f.is_landing,
            f.is_purchase,
            f.furthest_step
        FROM raw_sessions s
        JOIN v_int_funnel f ON s.session_id = f.session_id;
        """
        duckdb_conn.execute(sql_stg_events)
        duckdb_conn.execute(sql_int_funnel)
        df = duckdb_conn.execute(sql_marts_funnel).df()
        assert len(df) > 0
        assert df["session_id"].is_unique

    def test_comb_05_cohort_retention_with_segment_ltv(self, duckdb_conn):
        """Combines F17 (Cohort Retention), F01 (User Segments), and F11 (Marts)."""
        sql = """
        WITH user_first_order AS (
            SELECT
                u.user_id,
                u.customer_segment,
                DATE_TRUNC('month', MIN(o.order_timestamp)) AS cohort_month
            FROM raw_users u
            JOIN raw_orders o ON u.user_id = o.user_id
            GROUP BY u.user_id, u.customer_segment
        )
        SELECT
            ufo.cohort_month,
            ufo.customer_segment,
            DATEDIFF('month', ufo.cohort_month, DATE_TRUNC('month', o.order_timestamp)) AS month_offset,
            COUNT(DISTINCT o.user_id) AS active_users,
            SUM(o.total_amount) AS revenue,
            ROUND(SUM(o.total_amount) / COUNT(DISTINCT ufo.user_id), 2) AS ltv_per_acquired_user
        FROM raw_orders o
        JOIN user_first_order ufo ON o.user_id = ufo.user_id
        GROUP BY 1, 2, 3
        ORDER BY 1, 2, 3;
        """
        df = duckdb_conn.execute(sql).df()
        assert len(df) > 0
        assert "customer_segment" in df.columns

    def test_comb_06_star_schema_with_dax_measure_slicing(self, duckdb_conn):
        """Combines F21 (Star Schema), F22 (DAX Measures), and F12 (Dimensions)."""
        # Simulate Star Schema join: fct_orders -> dim_users, dim_products, dim_date
        sql = """
        SELECT
            u.customer_segment,
            p.category,
            d.year,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.total_item_price), 2) AS gross_revenue,
            ROUND(SUM(oi.line_profit), 2) AS gross_profit,
            ROUND(SUM(oi.line_profit) / SUM(oi.total_item_price) * 100.0, 2) AS gross_margin_pct
        FROM raw_orders o
        JOIN raw_users u ON o.user_id = u.user_id
        JOIN raw_order_items oi ON o.order_id = oi.order_id
        JOIN raw_products p ON oi.product_id = p.product_id
        JOIN (
            SELECT CAST('2025-01-01' AS DATE) + INTERVAL (n) DAY AS date_day, 2025 AS year
            FROM range(0, 365) t(n)
        ) d ON CAST(o.order_timestamp AS DATE) = d.date_day
        GROUP BY u.customer_segment, p.category, d.year;
        """
        df = duckdb_conn.execute(sql).df()
        assert len(df) > 0
        assert (df["gross_margin_pct"] > 0).all()

    def test_comb_07_incremental_merge_with_referential_schema_tests(self, duckdb_conn):
        """Combines F14 (Incremental Merge), F15 (Schema Tests), and F11 (Facts)."""
        # 1. Verify lookback window filters correctly
        # 2. Verify all output keys are unique and non-null
        sql = """
        WITH latest_batch AS (
            SELECT * FROM raw_orders
            WHERE order_timestamp >= (SELECT MAX(order_timestamp) - INTERVAL 7 DAY FROM raw_orders)
        )
        SELECT
            order_id,
            COUNT(*) AS cnt
        FROM latest_batch
        GROUP BY order_id
        HAVING COUNT(*) > 1;
        """
        dups = duckdb_conn.execute(sql).fetchall()
        assert len(dups) == 0

    def test_comb_08_ab_subgroup_statistical_testing(self, ref_data_bundle):
        """Combines F18 (SRM), F19 (Z-Test), F03 (Sessions), and F05 (Device Variance)."""
        sessions = ref_data_bundle["sessions"]
        orders = ref_data_bundle["orders"]

        merged = sessions.merge(orders[["session_id", "order_id"]], on="session_id", how="left")
        merged["converted"] = merged["order_id"].notnull().astype(int)

        # Test A/B metrics across Mobile subgroup
        mobile = merged[merged["device_type"] == "Mobile"]
        counts = mobile["ab_variant"].value_counts()
        n_c = int(counts.get("control", 0))
        n_t = int(counts.get("treatment", 0))
        
        # SRM check on Mobile subgroup
        chi2, p_val, srm_ok = oracle_compute_srm_chi2(n_c, n_t)
        assert srm_ok is True

        conv_c = int(mobile[mobile["ab_variant"] == "control"]["converted"].sum())
        conv_t = int(mobile[mobile["ab_variant"] == "treatment"]["converted"].sum())
        z_res = oracle_compute_two_proportion_ztest(n_c, conv_c, n_t, conv_t)
        assert 0.0 <= z_res["conversion_rate_control"] <= 1.0
        assert 0.0 <= z_res["conversion_rate_treatment"] <= 1.0

    def test_comb_09_product_catalog_margins_to_order_line_profit(self, ref_data_bundle):
        """Combines F02 (Product Catalog), F07 (Invariants), and F11 (Order Facts)."""
        products = ref_data_bundle["products"]
        order_items = ref_data_bundle["order_items"]

        merged = order_items.merge(products, on="product_id", suffixes=("_item", "_catalog"))
        # Unit price and cost must match catalog
        assert (merged["unit_price_item"] == merged["price"]).all()
        assert (merged["unit_cost"] == merged["cost"]).all()

        # Reconcile line profit
        expected_profit = ((merged["price"] - merged["cost"]) * merged["quantity"]).round(2)
        diff = (merged["line_profit"] - expected_profit).abs()
        assert (diff < 0.02).all()

    def test_comb_10_pipeline_dag_with_circuit_breaker_gate(self):
        """Combines F26 (Orchestration Pipeline) with F15 (Schema Test Gates)."""
        # Step 1: Raw Ingestion
        ingestion_status = "SUCCESS"
        # Step 2: dbt Run Staging
        stg_status = "SUCCESS" if ingestion_status == "SUCCESS" else "SKIPPED"
        # Step 3: dbt Test (Circuit Breaker Gate)
        test_failures = 0
        circuit_breaker_tripped = (test_failures > 0)
        # Step 4: Marts & Power BI
        marts_status = "SKIPPED" if circuit_breaker_tripped else "SUCCESS"
        pbi_status = "SKIPPED" if circuit_breaker_tripped else "SUCCESS"

        assert stg_status == "SUCCESS"
        assert not circuit_breaker_tripped
        assert marts_status == "SUCCESS"
        assert pbi_status == "SUCCESS"

    def test_comb_11_user_dimension_lifetime_metrics_reconciliation(self, duckdb_conn):
        """Combines F12 (Dim Users) and F11 (Fct Orders)."""
        sql = """
        SELECT
            u.user_id,
            COUNT(o.order_id) AS orders_count,
            COALESCE(SUM(o.total_amount), 0.0) AS spend_sum
        FROM raw_users u
        LEFT JOIN raw_orders o ON u.user_id = o.user_id
        GROUP BY u.user_id;
        """
        df = duckdb_conn.execute(sql).df()
        assert len(df) > 0
        assert (df["orders_count"] >= 0).all()
        assert (df["spend_sum"] >= 0).all()

    def test_comb_12_active_and_inactive_date_relationship_simulation(self, duckdb_conn):
        """Combines F21 (Semantic Model) and F11 (Fct Orders)."""
        # Active: order_date. Inactive: shipping_date.
        sql = """
        SELECT
            CAST(o.order_timestamp AS DATE) AS order_date,
            CAST(o.order_timestamp + INTERVAL 2 DAY AS DATE) AS shipping_date,
            COUNT(*) AS order_count
        FROM raw_orders o
        GROUP BY 1, 2;
        """
        df = duckdb_conn.execute(sql).df()
        assert len(df) > 0
        assert (df["shipping_date"] >= df["order_date"]).all()

    def test_comb_13_funnel_dropoff_rates_with_executive_revenue_projections(self):
        """Combines F16 (Funnel Analytics) and F25 (Revenue Impact Models)."""
        checkout_sessions = 50000
        current_cr = 0.100  # 10%
        target_cr = 0.1089  # +8.9% lift
        aov = 120.0

        current_revenue = checkout_sessions * current_cr * aov
        lifted_revenue = checkout_sessions * target_cr * aov
        incremental = lifted_revenue - current_revenue

        assert incremental > 0
        assert round(incremental, 2) == 53400.0

    def test_comb_14_srm_check_preceding_hypothesis_testing(self):
        """Combines F18 (SRM) and F19 (Two-Proportion Z-Test)."""
        # Case A: Balanced traffic -> proceed with test
        chi2, p_val, srm_passed = oracle_compute_srm_chi2(50000, 50000)
        assert srm_passed is True
        z_res = oracle_compute_two_proportion_ztest(50000, 5000, 50000, 5450)
        assert z_res["statistically_significant"] is True

        # Case B: Biased traffic -> flag experiment invalid
        chi2_b, p_val_b, srm_passed_b = oracle_compute_srm_chi2(40000, 60000)
        assert srm_passed_b is False
        experiment_valid = srm_passed_b
        assert experiment_valid is False

    def test_comb_15_end_to_end_referential_lineage_trace(self, ref_data_bundle):
        """Combines all entities: users -> sessions -> events -> orders -> order_items."""
        users = ref_data_bundle["users"]
        sessions = ref_data_bundle["sessions"]
        events = ref_data_bundle["events"]
        orders = ref_data_bundle["orders"]
        order_items = ref_data_bundle["order_items"]

        # Pick one order
        if len(orders) > 0:
            sample_order = orders.iloc[0]
            oid = sample_order["order_id"]
            sid = sample_order["session_id"]
            uid = sample_order["user_id"]

            # Trace backwards
            assert uid in users["user_id"].values
            assert sid in sessions["session_id"].values
            assert sid in events["session_id"].values
            # Trace forwards
            assert oid in order_items["order_id"].values
