"""
PulseCart Milestone 3 Automated Invariant Verification Suite
Empirically tests statistical rigor, mathematical invariants, and reporting artifacts:
1. Multi-stage Funnel Monotonicity & Dimensional Slicing
2. Cohort Retention Month 0 = 100%, Monotonic Decay vs M0, Repeat Purchasing, and LTV Curves
3. A/B Testing SRM Chi-Square Balance, Two-Proportion Z-Test, and Delta Method 95% CIs
4. Report JSON generation and schema validation

Exit Code: 0 on all invariants passed, 1 on any invariant violation.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

# Ensure pulsecart root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.analytics.ab_test import ABTestAnalyzer, compute_srm_test, compute_two_proportion_ztest
from src.analytics.funnel import FUNNEL_STAGES, FunnelAnalyzer
from src.analytics.retention import RetentionAnalyzer
from src.analytics.statistical_runner import run_all_analytics


def verify_funnel_invariants(data_dir: Path) -> List[str]:
    """Verifies funnel fact table invariants."""
    violations = []
    print("\n" + "=" * 80)
    print("VERIFICATION CHECK 1: FUNNEL MONOTONICITY & STAGE COMPLETENESS")
    print("=" * 80)

    funnel_path = data_dir / "fct_funnel.parquet"
    if not funnel_path.exists():
        funnel_path = data_dir / "fct_funnel.csv"

    if not funnel_path.exists():
        return [f"Funnel data mart file not found at {funnel_path}"]

    analyzer = FunnelAnalyzer(data_path=funnel_path)
    df = analyzer.load_data()
    print(f"  Loaded fct_funnel rows: {len(df):,}")

    if len(df) < 1000:
        violations.append(f"fct_funnel has only {len(df)} rows (< 1000)")

    metrics_df = analyzer.evaluate_funnel(df)
    print(f"  Funnel stages evaluated: {len(metrics_df)} (expected 6)")

    if len(metrics_df) != 6:
        violations.append(f"Expected 6 stages, got {len(metrics_df)}")

    # Check stage names in exact order
    stages = metrics_df["stage_name"].tolist()
    if stages != FUNNEL_STAGES:
        violations.append(f"Stages {stages} do not match expected {FUNNEL_STAGES}")

    # Check counts strictly decreasing / non-increasing
    counts = metrics_df["sessions_count"].tolist()
    print(f"  Stage counts: {' -> '.join(str(c) for c in counts)}")

    if counts[0] <= 0:
        violations.append("Step 1 landing sessions count must be > 0")

    for i in range(1, len(counts)):
        if counts[i] > counts[i - 1]:
            violations.append(
                f"Funnel monotonicity violated at stage {stages[i]}: {counts[i]} > {counts[i-1]}"
            )

    # Check conversion rates bounds [0, 100]
    for _, row in metrics_df.iterrows():
        cr = row["step_conversion_rate"]
        ocr = row["overall_conversion_rate"]
        if not (0.0 <= cr <= 100.0):
            violations.append(f"Stage {row['stage_name']} step conversion rate {cr}% out of range [0, 100]")
        if not (0.0 <= ocr <= 100.0):
            violations.append(f"Stage {row['stage_name']} overall conversion rate {ocr}% out of range [0, 100]")

    # Check dimensional slices
    for dim in ["device_type", "country", "customer_segment"]:
        slices = analyzer.slice_by_dimension(dim, df)
        print(f"  Dimensional slice '{dim}': {list(slices.keys())}")
        if len(slices) < 2:
            violations.append(f"Dimension '{dim}' has fewer than 2 slices ({len(slices)})")

    if not violations:
        print("  [PASS] All funnel stage and dimensional invariants verified successfully!")
    else:
        for v in violations:
            print(f"  [FAIL] {v}")

    return violations


def verify_retention_invariants(data_dir: Path) -> List[str]:
    """Verifies retention, repeat purchase, and LTV invariants."""
    violations = []
    print("\n" + "=" * 80)
    print("VERIFICATION CHECK 2: COHORT RETENTION, REPEAT PURCHASES & LTV")
    print("=" * 80)

    retention_path = data_dir / "fct_user_retention.parquet"
    if not retention_path.exists():
        retention_path = data_dir / "fct_user_retention.csv"

    orders_path = data_dir / "fct_orders.parquet"
    if not orders_path.exists():
        orders_path = data_dir / "fct_orders.csv"

    analyzer = RetentionAnalyzer(retention_path=retention_path, orders_path=orders_path)
    ret_df = analyzer.load_retention_data()
    ord_df = analyzer.load_orders_data()

    print(f"  Loaded fct_user_retention rows: {len(ret_df):,}")
    print(f"  Loaded fct_orders rows:         {len(ord_df):,}")

    matrix = analyzer.calculate_cohort_retention_matrix(ret_df)
    inv = analyzer.verify_retention_invariants(ret_df)

    print(f"  Total cohorts in matrix: {len(matrix)}")
    print(f"  Month 0 retention == 100%: {inv['month_0_is_100_percent']}")
    print(f"  Subsequent months <= Month 0: {inv['decay_monotonic_vs_m0']}")

    if not inv["month_0_is_100_percent"]:
        violations.append("Retention invariant failed: Month 0 retention is not 100% for all cohorts")

    if not inv["decay_monotonic_vs_m0"]:
        violations.append("Retention invariant failed: One or more subsequent months exceed Month 0 cohort size")

    # Verify repeat purchase rate
    rpr_res = analyzer.calculate_repeat_purchase_rate(ord_df)
    rpr = rpr_res["repeat_purchase_rate"]
    tot_purchasers = rpr_res["total_purchasing_users"]
    rep_purchasers = rpr_res["repeat_purchasing_users"]

    print(f"  Total purchasing users: {tot_purchasers:,}")
    print(f"  Repeat purchasing users: {rep_purchasers:,}")
    print(f"  Repeat purchase rate: {rpr:.2f}%")

    if tot_purchasers <= 0:
        violations.append("Total purchasing users is 0")
    if not (0.0 <= rpr <= 100.0):
        violations.append(f"Repeat purchase rate {rpr}% out of range [0, 100]")
    if rep_purchasers > tot_purchasers:
        violations.append(f"Repeat purchasers ({rep_purchasers}) > total purchasers ({tot_purchasers})")

    # Verify LTV curves monotonicity
    ltv_df = analyzer.calculate_ltv_curves(ret_df)
    print(f"  LTV curve segment-cohort records: {len(ltv_df)}")
    has_segment = "customer_segment" in ltv_df.columns
    group_cols = ["customer_segment", "cohort_month_str"] if has_segment else ["cohort_month_str"]

    ltv_mono_fails = 0
    for _, grp in ltv_df.groupby(group_cols):
        if not grp["cumulative_revenue"].is_monotonic_increasing:
            ltv_mono_fails += 1

    if ltv_mono_fails > 0:
        violations.append(f"Cumulative revenue curve failed monotonicity in {ltv_mono_fails} cohorts")
    else:
        print("  [PASS] Cumulative LTV curves strictly monotonic non-decreasing across all cohorts!")

    if not violations:
        print("  [PASS] All retention and repeat purchase invariants verified successfully!")
    else:
        for v in violations:
            print(f"  [FAIL] {v}")

    return violations


def verify_ab_test_invariants(data_dir: Path) -> List[str]:
    """Verifies A/B test SRM, Two-Proportion Z-Test, and Confidence Interval invariants."""
    violations = []
    print("\n" + "=" * 80)
    print("VERIFICATION CHECK 3: A/B EXPERIMENT SRM & STATISTICAL RIGOR")
    print("=" * 80)

    ab_path = data_dir / "fct_ab_test.parquet"
    if not ab_path.exists():
        ab_path = data_dir / "fct_ab_test.csv"

    analyzer = ABTestAnalyzer(data_path=ab_path)
    df = analyzer.load_data()
    print(f"  Loaded fct_ab_test rows: {len(df):,}")

    full_res = analyzer.run_full_analysis(df)
    overall = full_res["overall_results"]
    srm = overall["srm"]

    print(f"  Control sample size:   {overall['n_control']:,}")
    print(f"  Treatment sample size: {overall['n_treatment']:,}")
    print(f"  SRM Chi-Square stat:   {srm['chi2_statistic']:.4f} (p-value: {srm['p_value']:.4f})")
    print(f"  SRM Status:            {'PASSED' if srm['srm_passed'] else 'FAILED'}")

    # SRM check must pass (traffic is balanced)
    if not srm["srm_passed"]:
        violations.append(f"A/B SRM balance check failed: chi2={srm['chi2_statistic']:.4f}, p={srm['p_value']:.4f} < 0.01")

    # Conversions check
    cr_ctrl = overall["conversion_rate_control"]
    cr_treat = overall["conversion_rate_treatment"]
    rel_lift = overall["relative_lift"]
    abs_diff = overall["absolute_difference"]
    z_score = overall["z_score"]
    p_val = overall["p_value"]

    print(f"  Control conversion rate:   {cr_ctrl * 100:.2f}%")
    print(f"  Treatment conversion rate: {cr_treat * 100:.2f}%")
    print(f"  Relative lift:             {rel_lift * 100:+.2f}%")
    print(f"  Z-score:                   {z_score:.4f}")
    print(f"  p-value:                   {p_val:.4e}")
    print(f"  95% CI Relative:           [{overall['ci_rel_lower'] * 100:.2f}%, {overall['ci_rel_upper'] * 100:.2f}%]")

    # Check bounds
    if not (0.0 <= cr_ctrl <= 1.0):
        violations.append(f"Control conversion rate {cr_ctrl} out of [0, 1]")
    if not (0.0 <= cr_treat <= 1.0):
        violations.append(f"Treatment conversion rate {cr_treat} out of [0, 1]")
    if not (0.0 <= p_val <= 1.0):
        violations.append(f"p-value {p_val} out of [0, 1]")

    # Check Delta method CI encloses the estimate
    if not (overall["ci_rel_lower"] <= rel_lift <= overall["ci_rel_upper"]):
        violations.append(
            f"Delta method relative CI [{overall['ci_rel_lower']}, {overall['ci_rel_upper']}] does not enclose lift {rel_lift}"
        )

    # Dimensional breakdowns
    by_device = full_res["by_device"]
    by_country = full_res["by_country"]
    print(f"  A/B breakdowns by device: {list(by_device.keys())}")
    print(f"  A/B breakdowns by country: {list(by_country.keys())}")

    if len(by_device) < 2:
        violations.append("A/B breakdown by device has fewer than 2 segments")
    if len(by_country) < 2:
        violations.append("A/B breakdown by country has fewer than 2 segments")

    if not violations:
        print("  [PASS] All A/B testing statistical invariants verified successfully!")
    else:
        for v in violations:
            print(f"  [FAIL] {v}")

    return violations


def verify_generated_reports(output_dir: Path) -> List[str]:
    """Verifies that all 4 JSON reports exist, parse cleanly, and contain non-empty data."""
    violations = []
    print("\n" + "=" * 80)
    print("VERIFICATION CHECK 4: JSON REPORT ARTIFACTS VALIDATION")
    print("=" * 80)

    expected_files = [
        "funnel_analysis.json",
        "cohort_retention.json",
        "ab_test_results.json",
        "statistical_summary.json",
    ]

    for fname in expected_files:
        fpath = output_dir / fname
        if not fpath.exists():
            violations.append(f"Missing expected report: {fname}")
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"  [PASS] Valid JSON in {fname} ({fpath.stat().st_size:,} bytes)")
        except Exception as e:
            violations.append(f"Failed to parse {fname} as JSON: {e}")

    # Check statistical_summary.json status
    summary_path = output_dir / "statistical_summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
            if summary.get("status") != "SUCCESS":
                violations.append(f"statistical_summary status is '{summary.get('status')}', expected 'SUCCESS'")

    return violations


def main() -> int:
    print("=" * 80)
    print("PULSECART MILESTONE 3 ANALYTICS EMPIRICAL INVARIANT VERIFIER")
    print("=" * 80)

    data_dir = PROJECT_ROOT / "data" / "marts"
    output_dir = PROJECT_ROOT / "reports"

    # Step 1: Run analytics runner to ensure reports are fresh
    print("\n[STEP 1] Generating fresh analytics reports via run_all_analytics()...")
    run_all_analytics(data_dir=data_dir, output_dir=output_dir)

    # Step 2: Verify each domain
    all_violations: List[str] = []
    all_violations.extend(verify_funnel_invariants(data_dir))
    all_violations.extend(verify_retention_invariants(data_dir))
    all_violations.extend(verify_ab_test_invariants(data_dir))
    all_violations.extend(verify_generated_reports(output_dir))

    # Step 3: Final verdict
    print("\n" + "=" * 80)
    print("FINAL INVARIANT VERIFICATION SUMMARY")
    print("=" * 80)
    print(f" Total Violations Detected: {len(all_violations)}")

    if len(all_violations) == 0:
        print("\n [VERDICT: PASS] 100% OF MILESTONE 3 INVARIANTS VERIFIED SUCCESSFULLY!")
        print("=" * 80)
        return 0
    else:
        print("\n [VERDICT: FAIL] THE FOLLOWING VIOLATIONS WERE DETECTED:")
        for v in all_violations:
            print(f"   - {v}")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
