"""
PulseCart Unit Test Suite - Milestone 3 Analytics & Statistical Engines
Tests funnel.py, retention.py, ab_test.py, and statistical_runner.py
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.analytics.ab_test import (
    ABTestAnalyzer,
    ABTestResult,
    SRMResult,
    compute_ab_test,
    compute_srm_test,
    compute_two_proportion_ztest,
)
from src.analytics.funnel import (
    FUNNEL_STAGES,
    FunnelAnalyzer,
    FunnelStageMetric,
    compute_funnel_metrics,
)
from src.analytics.retention import (
    CohortRetentionRecord,
    RetentionAnalyzer,
    compute_cohort_retention,
)
from src.analytics.statistical_runner import run_all_analytics
from tests.e2e.conftest import (
    oracle_compute_funnel_metrics,
    oracle_compute_srm_chi2,
    oracle_compute_two_proportion_ztest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# 1. Multi-Stage Funnel Unit Tests
# ===========================================================================
class TestFunnelAnalytics:
    """Unit tests for src/analytics/funnel.py"""

    @pytest.fixture
    def mock_funnel_data(self) -> pd.DataFrame:
        """Synthetic mock session funnel DataFrame."""
        records = []
        for i in range(100):
            # 100 landing, 80 view, 50 cart, 30 checkout, 20 payment, 15 purchase
            records.append({
                "session_id": f"SES-{i:05d}",
                "user_id": f"USR-{i % 20:05d}",
                "device_type": "Desktop" if i < 60 else "Mobile",
                "traffic_source": "Organic Search" if i < 50 else "Direct",
                "country": "US" if i < 70 else "UK",
                "customer_segment": "Regular" if i < 80 else "VIP",
                "reached_landing_page": 1,
                "reached_product_view": 1 if i < 80 else 0,
                "reached_add_to_cart": 1 if i < 50 else 0,
                "reached_checkout_started": 1 if i < 30 else 0,
                "reached_payment_started": 1 if i < 20 else 0,
                "reached_purchase": 1 if i < 15 else 0,
                "furthest_step_reached": (
                    6 if i < 15 else 5 if i < 20 else 4 if i < 30 else 3 if i < 50 else 2 if i < 80 else 1
                ),
            })
        return pd.DataFrame(records)

    def test_evaluate_all_six_stages(self, mock_funnel_data):
        analyzer = FunnelAnalyzer(df=mock_funnel_data)
        metrics = analyzer.evaluate_funnel()
        assert len(metrics) == 6
        assert metrics["stage_name"].tolist() == FUNNEL_STAGES
        assert metrics["step_number"].tolist() == list(range(1, 7))

    def test_step_and_overall_conversion_rates(self, mock_funnel_data):
        analyzer = FunnelAnalyzer(df=mock_funnel_data)
        metrics = analyzer.evaluate_funnel()
        assert metrics.iloc[0]["sessions_count"] == 100
        assert metrics.iloc[0]["step_conversion_rate"] == 100.0
        assert metrics.iloc[0]["overall_conversion_rate"] == 100.0

        assert metrics.iloc[1]["sessions_count"] == 80
        assert metrics.iloc[1]["step_conversion_rate"] == 80.0
        assert metrics.iloc[1]["overall_conversion_rate"] == 80.0

        assert metrics.iloc[-1]["sessions_count"] == 15
        assert metrics.iloc[-1]["overall_conversion_rate"] == 15.0

    def test_drop_off_calculations(self, mock_funnel_data):
        analyzer = FunnelAnalyzer(df=mock_funnel_data)
        metrics = analyzer.evaluate_funnel()
        for i in range(1, len(metrics)):
            prev = metrics.iloc[i - 1]["sessions_count"]
            curr = metrics.iloc[i]["sessions_count"]
            expected_abs_drop = prev - curr
            assert metrics.iloc[i]["absolute_drop_off"] == expected_abs_drop
            assert metrics.iloc[i]["drop_off_rate"] == round(expected_abs_drop / prev * 100.0, 2)

    def test_dimensional_slicing(self, mock_funnel_data):
        analyzer = FunnelAnalyzer(df=mock_funnel_data)
        by_device = analyzer.slice_by_dimension("device_type")
        assert set(by_device.keys()) == {"Desktop", "Mobile"}
        assert by_device["Desktop"].iloc[0]["sessions_count"] == 60
        assert by_device["Mobile"].iloc[0]["sessions_count"] == 40

    def test_empty_dataframe_division_by_zero_guard(self):
        empty_df = pd.DataFrame(columns=["session_id", "reached_landing_page", "device_type"])
        analyzer = FunnelAnalyzer(df=empty_df)
        metrics = analyzer.evaluate_funnel()
        assert len(metrics) == 6
        assert (metrics["sessions_count"] == 0).all()
        assert (metrics["step_conversion_rate"] == 0.0).all()
        assert (metrics["overall_conversion_rate"] == 0.0).all()
        assert (metrics["absolute_drop_off"] == 0).all()

    def test_run_full_analysis_structure(self, mock_funnel_data):
        analyzer = FunnelAnalyzer(df=mock_funnel_data)
        res = analyzer.run_full_analysis()
        assert "total_sessions" in res
        assert "overall_funnel" in res
        assert "dimensional_analysis" in res
        assert res["total_sessions"] == 100
        assert len(res["overall_funnel"]) == 6
        assert "device_type" in res["dimensional_analysis"]

    def test_oracle_compatibility_mode(self):
        sessions = pd.DataFrame([{"session_id": f"S{i}"} for i in range(10)])
        events = pd.DataFrame([
            {"session_id": f"S{i}", "event_type": "landing_page"} for i in range(10)
        ] + [
            {"session_id": f"S{i}", "event_type": "purchase"} for i in range(4)
        ])
        metrics = compute_funnel_metrics(df=events, sessions_df=sessions)
        oracle_metrics = oracle_compute_funnel_metrics(events, sessions)
        assert len(metrics) == 6
        assert metrics.iloc[-1]["overall_conversion_rate"] == oracle_metrics.iloc[-1]["overall_conversion_rate"]

    def test_defensive_null_handling_in_reached_flags(self):
        """Verify that NaN / None in reached_* columns are handled defensively without raising IntCastingNaNError."""
        df_with_nans = pd.DataFrame({
            "session_id": ["S1", "S2", "S3", "S4"],
            "reached_landing_page": [1, np.nan, 1, 0],
            "reached_product_view": [1, 0, np.nan, np.nan],
            "reached_add_to_cart": [np.nan, np.nan, 0, 0],
            "reached_checkout_started": [None, None, None, None],
            "reached_payment_started": [np.nan, 0, 0, 0],
            "reached_purchase": [0, 0, 0, 0],
        })
        analyzer = FunnelAnalyzer(df=df_with_nans)
        counts = analyzer.extract_stage_counts(df_with_nans)
        assert counts["landing_page"] == 2
        assert counts["product_view"] == 1
        assert counts["add_to_cart"] == 0
        assert counts["checkout_started"] == 0
        metrics = analyzer.evaluate_funnel()
        assert len(metrics) == 6
        assert metrics.iloc[0]["sessions_count"] == 2


# ===========================================================================
# 2. Monthly Cohort Retention Unit Tests
# ===========================================================================
class TestRetentionAnalytics:
    """Unit tests for src/analytics/retention.py"""

    @pytest.fixture
    def mock_retention_data(self) -> pd.DataFrame:
        """Synthetic mock user retention records."""
        records = []
        # Cohort 2025-01: 10 users M0, 5 users M1, 2 users M2
        for uid in range(1, 11):
            u_str = f"USR-{uid:04d}"
            records.append({
                "user_id": u_str,
                "cohort_month": "2025-01-01",
                "activity_month": "2025-01-01",
                "month_offset": 0,
                "revenue_in_month": 100.0,
                "customer_segment": "Regular" if uid <= 5 else "VIP",
            })
            if uid <= 5:
                records.append({
                    "user_id": u_str,
                    "cohort_month": "2025-01-01",
                    "activity_month": "2025-02-01",
                    "month_offset": 1,
                    "revenue_in_month": 50.0,
                    "customer_segment": "Regular" if uid <= 5 else "VIP",
                })
            if uid <= 2:
                records.append({
                    "user_id": u_str,
                    "cohort_month": "2025-01-01",
                    "activity_month": "2025-03-01",
                    "month_offset": 2,
                    "revenue_in_month": 30.0,
                    "customer_segment": "Regular" if uid <= 5 else "VIP",
                })
        return pd.DataFrame(records)

    @pytest.fixture
    def mock_orders_data(self) -> pd.DataFrame:
        """Synthetic mock completed orders."""
        return pd.DataFrame([
            {"order_id": "O1", "user_id": "USR-1", "status": "completed", "customer_segment": "Regular", "total_amount": 100.0},
            {"order_id": "O2", "user_id": "USR-1", "status": "completed", "customer_segment": "Regular", "total_amount": 50.0},
            {"order_id": "O3", "user_id": "USR-2", "status": "completed", "customer_segment": "Regular", "total_amount": 80.0},
            {"order_id": "O4", "user_id": "USR-3", "status": "completed", "customer_segment": "VIP", "total_amount": 120.0},
            {"order_id": "O5", "user_id": "USR-3", "status": "completed", "customer_segment": "VIP", "total_amount": 60.0},
            {"order_id": "O6", "user_id": "USR-3", "status": "completed", "customer_segment": "VIP", "total_amount": 40.0},
        ])

    def test_cohort_retention_matrix_calculation(self, mock_retention_data):
        analyzer = RetentionAnalyzer(retention_df=mock_retention_data)
        matrix = analyzer.calculate_cohort_retention_matrix()
        assert "2025-01" in matrix.index
        assert matrix.loc["2025-01", 0] == 100.0
        assert matrix.loc["2025-01", 1] == 50.0
        assert matrix.loc["2025-01", 2] == 20.0

    def test_retention_invariants_verification(self, mock_retention_data):
        analyzer = RetentionAnalyzer(retention_df=mock_retention_data)
        invariants = analyzer.verify_retention_invariants()
        assert invariants["month_0_is_100_percent"] is True
        assert invariants["decay_monotonic_vs_m0"] is True
        assert invariants["all_decay_monotonic"] is True
        assert len(invariants["violations"]) == 0

    def test_repeat_purchase_rate_formula(self, mock_orders_data):
        analyzer = RetentionAnalyzer(orders_df=mock_orders_data)
        rpr_res = analyzer.calculate_repeat_purchase_rate()
        # Users: USR-1 (2 orders), USR-2 (1 order), USR-3 (3 orders) -> 2 repeat out of 3 = 66.67%
        assert rpr_res["total_purchasing_users"] == 3
        assert rpr_res["repeat_purchasing_users"] == 2
        assert rpr_res["repeat_purchase_rate"] == 66.67

    def test_ltv_curves_monotonicity(self, mock_retention_data):
        analyzer = RetentionAnalyzer(retention_df=mock_retention_data)
        ltv_df = analyzer.calculate_ltv_curves()
        assert len(ltv_df) > 0
        assert "cumulative_revenue" in ltv_df.columns
        assert "cumulative_ltv" in ltv_df.columns
        for (seg, cohort), grp in ltv_df.groupby(["customer_segment", "cohort_month_str"]):
            assert grp["cumulative_revenue"].is_monotonic_increasing
            assert grp["cumulative_ltv"].is_monotonic_increasing

    def test_empty_retention_handling(self):
        analyzer = RetentionAnalyzer(retention_df=pd.DataFrame(), orders_df=pd.DataFrame())
        matrix = analyzer.calculate_cohort_retention_matrix()
        assert len(matrix) == 0
        inv = analyzer.verify_retention_invariants()
        assert inv["month_0_is_100_percent"] is True
        rpr = analyzer.calculate_repeat_purchase_rate()
        assert rpr["repeat_purchase_rate"] == 0.0


# ===========================================================================
# 3. A/B Testing & Statistical Experimentation Unit Tests
# ===========================================================================
class TestABTestingAnalytics:
    """Unit tests for src/analytics/ab_test.py"""

    def test_srm_exact_equal_split(self):
        srm = compute_srm_test(50000, 50000)
        assert srm.chi2_statistic == 0.0
        assert srm.p_value == 1.0
        assert srm.srm_passed is True

    def test_srm_matches_conftest_oracle(self):
        n_c, n_t = 49820, 50180
        res = compute_srm_test(n_c, n_t)
        o_chi2, o_p, o_pass = oracle_compute_srm_chi2(n_c, n_t)
        assert abs(res.chi2_statistic - o_chi2) < 1e-4
        assert abs(res.p_value - o_p) < 1e-4
        assert res.srm_passed == o_pass

    def test_srm_detects_severe_imbalance(self):
        srm = compute_srm_test(40000, 60000)
        assert srm.chi2_statistic > 6.635
        assert srm.p_value < 0.01
        assert srm.srm_passed is False

    def test_two_proportion_ztest_matches_oracle(self):
        n_c, c_c = 50000, 5000
        n_t, c_t = 50000, 5450
        res = compute_two_proportion_ztest(n_c, c_c, n_t, c_t)
        o_res = oracle_compute_two_proportion_ztest(n_c, c_c, n_t, c_t)

        assert abs(res.conversion_rate_control - o_res["conversion_rate_control"]) < 1e-6
        assert abs(res.conversion_rate_treatment - o_res["conversion_rate_treatment"]) < 1e-6
        assert abs(res.relative_lift - o_res["relative_lift"]) < 1e-6
        assert abs(res.pooled_se - o_res["pooled_se"]) < 1e-6
        assert abs(res.z_score - o_res["z_score"]) < 1e-6
        assert abs(res.p_value - o_res["p_value"]) < 1e-6
        assert abs(res.ci_abs_lower - o_res["ci_abs_lower"]) < 1e-6
        assert abs(res.ci_abs_upper - o_res["ci_abs_upper"]) < 1e-6
        assert abs(res.ci_rel_lower - o_res["ci_rel_lower"]) < 1e-6
        assert abs(res.ci_rel_upper - o_res["ci_rel_upper"]) < 1e-6
        assert res.statistically_significant == o_res["statistically_significant"]

    def test_delta_method_ci_bracket_contains_lift(self):
        res = compute_two_proportion_ztest(50000, 5000, 50000, 5450)
        assert res.ci_rel_lower < res.relative_lift < res.ci_rel_upper
        assert res.statistically_significant is True

    def test_zero_conversions_boundary(self):
        res = compute_two_proportion_ztest(1000, 0, 1000, 0)
        assert res.z_score == 0.0
        assert res.relative_lift == 0.0
        assert res.statistically_significant is False

    def test_empty_sample_boundary(self):
        res = compute_two_proportion_ztest(0, 0, 0, 0)
        assert res.z_score == 0.0
        assert res.relative_lift == 0.0
        assert res.statistically_significant is False

    def test_evaluate_experiment_dataframe(self):
        df = pd.DataFrame([
            {"ab_variant": "control", "completed_purchase": 1, "device_type": "Desktop", "country": "US"}
        ] * 100 + [
            {"ab_variant": "control", "completed_purchase": 0, "device_type": "Desktop", "country": "US"}
        ] * 900 + [
            {"ab_variant": "treatment", "completed_purchase": 1, "device_type": "Desktop", "country": "US"}
        ] * 120 + [
            {"ab_variant": "treatment", "completed_purchase": 0, "device_type": "Desktop", "country": "US"}
        ] * 880)

        analyzer = ABTestAnalyzer(df=df)
        res = analyzer.run_full_analysis()
        overall = res["overall_results"]
        assert overall["n_control"] == 1000
        assert overall["n_treatment"] == 1000
        assert overall["conversions_control"] == 100
        assert overall["conversions_treatment"] == 120
        assert round(overall["relative_lift"], 2) == 0.20


# ===========================================================================
# 4. Master Statistical Runner Unit Tests
# ===========================================================================
class TestStatisticalRunner:
    """Unit tests for src/analytics/statistical_runner.py"""

    def test_full_pipeline_execution_and_artifacts(self, tmp_path):
        marts_dir = PROJECT_ROOT / "data" / "marts"
        if not marts_dir.exists():
            pytest.skip("data/marts not found, skipping integration runner test")

        output_dir = tmp_path / "reports_test"
        summary = run_all_analytics(data_dir=marts_dir, output_dir=output_dir)

        assert summary["status"] == "SUCCESS"
        assert output_dir.exists()

        # Check all 4 JSON files created
        funnel_file = output_dir / "funnel_analysis.json"
        cohort_file = output_dir / "cohort_retention.json"
        ab_file = output_dir / "ab_test_results.json"
        summary_file = output_dir / "statistical_summary.json"

        assert funnel_file.exists()
        assert cohort_file.exists()
        assert ab_file.exists()
        assert summary_file.exists()

        # Validate JSON content
        with open(funnel_file) as f:
            f_data = json.load(f)
            assert len(f_data["overall_funnel"]) == 6

        with open(cohort_file) as f:
            c_data = json.load(f)
            assert c_data["retention_invariants"]["month_0_is_100_percent"] is True

        with open(ab_file) as f:
            a_data = json.load(f)
            assert a_data["overall_results"]["srm"]["srm_passed"] is True

        with open(summary_file) as f:
            s_data = json.load(f)
            assert s_data["status"] == "SUCCESS"
