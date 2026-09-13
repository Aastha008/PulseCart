"""
PulseCart Master Statistical Analytics Runner CLI
Feature F20 / Milestone 3

CLI tool orchestrating:
1. Multi-stage funnel analysis with dimensional slicing.
2. Monthly cohort retention matrices, repeat purchase rates, and LTV curves.
3. Checkout A/B experiment evaluation with SRM balance check and Two-Proportion Z-Test.
4. Generates formatted console outputs and 4 structured JSON artifacts:
   - reports/funnel_analysis.json
   - reports/cohort_retention.json
   - reports/ab_test_results.json
   - reports/statistical_summary.json
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, Optional

# Ensure pulsecart root is accessible
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.ab_test import ABTestAnalyzer
from src.analytics.funnel import FunnelAnalyzer
from src.analytics.retention import RetentionAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("statistical_runner")


def run_all_analytics(
    data_dir: Optional[Path] = None, output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Executes all Milestone 3 analytics engines, prints formatted summaries,
    and writes structured JSON reports to the designated output directory.
    """
    start_time = datetime.now(timezone.utc)
    if data_dir is None:
        data_dir = PROJECT_ROOT / "data" / "marts"
    else:
        data_dir = Path(data_dir)

    if output_dir is None:
        output_dir = PROJECT_ROOT / "reports"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" PULSECART REPRODUCIBLE ANALYTICS & STATISTICAL EXPERIMENTATION RUNNER")
    print("=" * 80)
    print(f" Data Directory:   {data_dir.resolve()}")
    print(f" Output Directory: {output_dir.resolve()}")
    print(f" Started:          {start_time.isoformat()}\n")

    # -----------------------------------------------------------------------
    # 1. Multi-Stage Funnel Analysis
    # -----------------------------------------------------------------------
    print("-" * 80)
    print(" [1/3] EXECUTING MULTI-STAGE FUNNEL ANALYSIS")
    print("-" * 80)

    funnel_path = data_dir / "fct_funnel.parquet"
    if not funnel_path.exists():
        funnel_path = data_dir / "fct_funnel.csv"

    funnel_analyzer = FunnelAnalyzer(data_path=funnel_path)
    funnel_report = funnel_analyzer.run_full_analysis()

    # Pretty print funnel table
    print(
        f"{'Step':<5} {'Stage Name':<20} {'Sessions':<12} {'Step Conv %':<14} {'Overall Conv %':<16} {'Drop-Off':<12} {'Drop %':<10}"
    )
    print("-" * 90)
    for stage_data in funnel_report["overall_funnel"]:
        print(
            f"{stage_data['step_number']:<5} "
            f"{stage_data['stage_name']:<20} "
            f"{stage_data['sessions_count']:<12,d} "
            f"{stage_data['step_conversion_rate']:<14.2f}% "
            f"{stage_data['overall_conversion_rate']:<16.2f}% "
            f"{stage_data['absolute_drop_off']:<12,d} "
            f"{stage_data['drop_off_rate']:<10.2f}%"
        )
    print(
        f"\n Total Sessions: {funnel_report['total_sessions']:,} | "
        f"Overall Conversion Rate: {funnel_report['overall_conversion_rate']:.2f}% | "
        f"Top Drop-off Stage: {funnel_report['top_dropoff_stage']}"
    )

    funnel_file = output_dir / "funnel_analysis.json"
    with open(funnel_file, "w", encoding="utf-8") as f:
        json.dump(funnel_report, f, indent=2)
    print(f" -> Saved: {funnel_file.name}")

    # -----------------------------------------------------------------------
    # 2. Monthly Cohort Retention & LTV Analysis
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print(" [2/3] EXECUTING MONTHLY COHORT RETENTION & LTV ANALYSIS")
    print("-" * 80)

    retention_path = data_dir / "fct_user_retention.parquet"
    if not retention_path.exists():
        retention_path = data_dir / "fct_user_retention.csv"

    orders_path = data_dir / "fct_orders.parquet"
    if not orders_path.exists():
        orders_path = data_dir / "fct_orders.csv"

    retention_analyzer = RetentionAnalyzer(
        retention_path=retention_path, orders_path=orders_path
    )
    retention_report = retention_analyzer.run_full_analysis()

    inv = retention_report["retention_invariants"]
    rpr = retention_report["repeat_purchase_metrics"]

    print(f" Total Cohorts Analyzed: {retention_report['total_cohorts']}")
    print(f" Month 0 Retention == 100%:  {inv['month_0_is_100_percent']}")
    print(f" Retention <= Month 0:       {inv['decay_monotonic_vs_m0']}")
    print(f" Total Purchasing Users:     {rpr['total_purchasing_users']:,}")
    print(f" Repeat Purchasing Users:    {rpr['repeat_purchasing_users']:,}")
    print(f" Repeat Purchase Rate:       {rpr['repeat_purchase_rate']:.2f}%\n")

    # Sample preview of cohort retention matrix
    print(f"{'Cohort Month':<15} {'M0':<10} {'M1':<10} {'M2':<10} {'M3':<10} {'M4':<10} {'M5':<10} {'M6':<10}")
    print("-" * 85)
    for c_rec in retention_report["cohort_retention_matrix"][:6]:
        rates = c_rec["retention_rates"]
        row_str = f"{c_rec['cohort_month']:<15}"
        for m in range(7):
            key = f"M{m}"
            if key in rates:
                row_str += f"{rates[key]:>6.1f}%   "
            else:
                row_str += f"{'--':>6}   "
        print(row_str)

    cohort_file = output_dir / "cohort_retention.json"
    with open(cohort_file, "w", encoding="utf-8") as f:
        json.dump(retention_report, f, indent=2)
    print(f" -> Saved: {cohort_file.name}")

    # -----------------------------------------------------------------------
    # 3. Checkout A/B Experiment & Statistical Hypothesis Testing
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print(" [3/3] EXECUTING CHECKOUT A/B EXPERIMENTATION & HYPOTHESIS TEST")
    print("-" * 80)

    ab_path = data_dir / "fct_ab_test.parquet"
    if not ab_path.exists():
        ab_path = data_dir / "fct_ab_test.csv"

    ab_analyzer = ABTestAnalyzer(data_path=ab_path)
    ab_report = ab_analyzer.run_full_analysis()
    overall_ab = ab_report["overall_results"]
    srm = overall_ab["srm"]

    print(f" Experiment: {ab_report['experiment_name']}")
    print(
        f" Sample Ratio Mismatch (SRM) Check (alpha = {srm['alpha']}):\n"
        f"   Control: {srm['n_control']:,} | Treatment: {srm['n_treatment']:,} | Total: {srm['total_samples']:,}\n"
        f"   Chi-Square Stat: {srm['chi2_statistic']:.4f} | p-value: {srm['p_value']:.4f} | "
        f"SRM Status: {'PASSED (No Mismatch)' if srm['srm_passed'] else 'FAILED (Mismatch Detected)'}"
    )

    print(
        f"\n Two-Proportion Z-Test Results (alpha = {overall_ab['alpha']}):\n"
        f"   Control Conversions:    {overall_ab['conversions_control']:,} / {overall_ab['n_control']:,} "
        f"({overall_ab['conversion_rate_control'] * 100:.2f}%)\n"
        f"   Treatment Conversions:  {overall_ab['conversions_treatment']:,} / {overall_ab['n_treatment']:,} "
        f"({overall_ab['conversion_rate_treatment'] * 100:.2f}%)\n"
        f"   Absolute Difference:    {overall_ab['absolute_difference'] * 100:+.2f} pp\n"
        f"   Relative Lift:          {overall_ab['relative_lift'] * 100:+.2f}%\n"
        f"   Pooled Standard Error:  {overall_ab['pooled_se']:.5f}\n"
        f"   Z-Score:                {overall_ab['z_score']:.4f}\n"
        f"   Two-Sided p-value:      {overall_ab['p_value']:.4e}\n"
        f"   95% CI (Absolute Diff): [{overall_ab['ci_abs_lower'] * 100:.2f} pp, {overall_ab['ci_abs_upper'] * 100:.2f} pp]\n"
        f"   95% CI (Relative Lift): [{overall_ab['ci_rel_lower'] * 100:.2f}%, {overall_ab['ci_rel_upper'] * 100:.2f}%]\n"
        f"   Statistical Significance: {'YES (Reject H0)' if overall_ab['statistically_significant'] else 'NO (Fail to Reject H0)'}"
    )

    ab_file = output_dir / "ab_test_results.json"
    with open(ab_file, "w", encoding="utf-8") as f:
        json.dump(ab_report, f, indent=2)
    print(f" -> Saved: {ab_file.name}")

    # -----------------------------------------------------------------------
    # 4. Master Statistical Summary
    # -----------------------------------------------------------------------
    end_time = datetime.now(timezone.utc)
    duration_secs = (end_time - start_time).total_seconds()

    decision_rec = (
        "DEPLOY TREATMENT: Statistically significant positive lift observed without SRM."
        if (overall_ab["statistically_significant"] and overall_ab["relative_lift"] > 0 and srm["srm_passed"])
        else "DO NOT DEPLOY: Results inconclusive or SRM detected."
    )

    summary = {
        "status": "SUCCESS",
        "execution_timestamp": end_time.isoformat(),
        "duration_seconds": round(duration_secs, 2),
        "data_directory": str(data_dir.resolve()),
        "output_directory": str(output_dir.resolve()),
        "funnel_summary": {
            "total_sessions": funnel_report["total_sessions"],
            "overall_conversion_rate": funnel_report["overall_conversion_rate"],
            "top_dropoff_stage": funnel_report["top_dropoff_stage"],
        },
        "retention_summary": {
            "total_cohorts": retention_report["total_cohorts"],
            "month_0_is_100_percent": inv["month_0_is_100_percent"],
            "decay_monotonic_vs_m0": inv["decay_monotonic_vs_m0"],
            "repeat_purchase_rate": rpr["repeat_purchase_rate"],
            "total_purchasing_users": rpr["total_purchasing_users"],
        },
        "ab_test_summary": {
            "experiment_name": ab_report["experiment_name"],
            "n_control": overall_ab["n_control"],
            "n_treatment": overall_ab["n_treatment"],
            "srm_passed": srm["srm_passed"],
            "srm_p_value": srm["p_value"],
            "conversion_rate_control": overall_ab["conversion_rate_control"],
            "conversion_rate_treatment": overall_ab["conversion_rate_treatment"],
            "relative_lift": overall_ab["relative_lift"],
            "z_score": overall_ab["z_score"],
            "p_value": overall_ab["p_value"],
            "statistically_significant": overall_ab["statistically_significant"],
            "ci_rel_95": [overall_ab["ci_rel_lower"], overall_ab["ci_rel_upper"]],
            "recommendation": decision_rec,
        },
        "generated_reports": [
            str(funnel_file.resolve()),
            str(cohort_file.resolve()),
            str(ab_file.resolve()),
            str((output_dir / "statistical_summary.json").resolve()),
        ],
    }

    summary_file = output_dir / "statistical_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 80)
    print(" EXECUTION COMPLETED SUCCESSFULLY")
    print(f" Execution Duration: {duration_secs:.2f} seconds")
    print(f" Master Summary Saved: {summary_file.name}")
    print("=" * 80)

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PulseCart Master Statistical Analytics Runner CLI"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="reports",
        help="Directory to write JSON reports (default: reports)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/marts",
        help="Directory containing fact marts (default: data/marts)",
    )

    args = parser.parse_args()

    try:
        run_all_analytics(data_dir=Path(args.data_dir), output_dir=Path(args.output_dir))
        return 0
    except Exception as e:
        logger.exception(f"Fatal error during analytics run: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
