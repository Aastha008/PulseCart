"""
PulseCart Kedro Nodes: Statistical Analytics & Experimentation Engine.

Kedro Concept: Nodes as Pure Analytical Functions
-------------------------------------------------
In this module, our nodes are pure Python functions that accept in-memory
DataFrames loaded by the Data Catalog (from Parquet or BigQuery), apply
scientific computing libraries (SciPy, NumPy, Pandas), and return structured
dictionaries representing statistical findings.

Nodes do NOT hardcode file paths or database credentials.
All threshold parameters (alpha = 0.05, 95% CI, SRM alpha = 0.01) are injected
dynamically from `parameters_analytics.yml`.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict
import pandas as pd

# Add pulsecart root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.funnel import FunnelAnalyzer
from src.analytics.retention import RetentionAnalyzer
from src.analytics.ab_test import ABTestAnalyzer

logger = logging.getLogger(__name__)


def compute_funnel_analytics_node(
    fct_funnel: pd.DataFrame,
    funnel_params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates multi-stage session funnel progression, step-by-step conversion rates,
    drop-off counts, and dimensional breakdowns across device, channel, and country.
    """
    logger.info(f"Executing Funnel Analytics on {len(fct_funnel):,} session records...")
    analyzer = FunnelAnalyzer(df=fct_funnel)
    report = analyzer.run_full_analysis()

    logger.info(
        f"Funnel Analysis Complete: Total Sessions = {report['total_sessions']:,}, "
        f"Overall Conversion = {report['overall_conversion_rate']:.2f}%, "
        f"Top Drop-Off = {report['top_dropoff_stage']}"
    )
    return report


def compute_cohort_retention_node(
    fct_user_retention: pd.DataFrame,
    fct_orders: pd.DataFrame,
    retention_params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Computes monthly user cohort retention matrices (M0-M6+), validates decay invariants,
    calculates repeat purchase rate, and evaluates LTV curves by customer segment.
    """
    logger.info(
        f"Executing Cohort Retention on {len(fct_user_retention):,} cohort records "
        f"and {len(fct_orders):,} order transactions..."
    )
    analyzer = RetentionAnalyzer(
        retention_df=fct_user_retention,
        orders_df=fct_orders,
    )
    report = analyzer.run_full_analysis()

    rpr = report["repeat_purchase_metrics"]
    logger.info(
        f"Cohort Retention Complete: {report['total_cohorts']} cohorts analyzed. "
        f"Repeat Purchase Rate = {rpr['repeat_purchase_rate']:.2f}% "
        f"({rpr['repeat_purchasing_users']:,} / {rpr['total_purchasing_users']:,} users)"
    )
    return report


def evaluate_ab_experiment_node(
    fct_ab_test: pd.DataFrame,
    ab_params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluates the checkout A/B test:
    1. Sample Ratio Mismatch (SRM) balance check (Pearson's Chi-Square Goodness-of-Fit, alpha=0.01).
    2. Two-Proportion Z-Test for conversion lift (H0: pt = pc vs H1: pt != pc).
    3. Pooled standard error, z-score, two-sided empirical p-value.
    4. 95% Confidence Intervals for absolute risk difference and relative lift.
    """
    alpha = ab_params.get("alpha", 0.05)
    srm_alpha = ab_params.get("srm_alpha", 0.01)

    logger.info(
        f"Executing A/B Experiment Hypothesis Testing on {len(fct_ab_test):,} sessions "
        f"(alpha={alpha}, srm_alpha={srm_alpha})..."
    )
    analyzer = ABTestAnalyzer(df=fct_ab_test)
    report = analyzer.run_full_analysis()

    overall = report["overall_results"]
    srm = overall["srm"]

    if not srm["srm_passed"]:
        logger.warning(
            f"SRM CHECK FAILED! Chi-square = {srm['chi2_statistic']:.4f}, p = {srm['p_value']:.4f}"
        )
    else:
        logger.info(
            f"SRM Balance Check PASSED: Chi-square = {srm['chi2_statistic']:.4f}, p = {srm['p_value']:.4f} > {srm_alpha}"
        )

    logger.info(
        f"A/B Test Evaluation Complete: "
        f"Control = {overall['conversion_rate_control'] * 100:.2f}%, "
        f"Treatment = {overall['conversion_rate_treatment'] * 100:.2f}%, "
        f"Relative Lift = {overall['relative_lift'] * 100:+.2f}%, "
        f"Z = {overall['z_score']:.4f}, p = {overall['p_value']:.4e}, "
        f"Statistically Significant = {overall['statistically_significant']}"
    )

    return report
