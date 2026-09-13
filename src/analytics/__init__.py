"""
PulseCart Core Analytics & Statistical Experimentation Engine
Milestone 3 Implementation

Modules:
- funnel: Multi-stage funnel analysis with dimensional slicing.
- retention: Monthly cohort retention matrices, repeat purchase rates, and LTV curves.
- ab_test: SRM balance check (Chi2) and Two-Proportion Z-Test with Delta Method 95% CIs.
- statistical_runner: Unified CLI and reporting orchestrator.
"""

from src.analytics.funnel import (
    FunnelAnalyzer,
    FunnelStageMetric,
    compute_funnel_metrics,
)
from src.analytics.retention import (
    RetentionAnalyzer,
    CohortRetentionRecord,
    compute_cohort_retention,
)
from src.analytics.ab_test import (
    ABTestAnalyzer,
    ABTestResult,
    SRMResult,
    compute_srm_test,
    compute_two_proportion_ztest,
)
from src.analytics.statistical_runner import run_all_analytics

__all__ = [
    "FunnelAnalyzer",
    "FunnelStageMetric",
    "compute_funnel_metrics",
    "RetentionAnalyzer",
    "CohortRetentionRecord",
    "compute_cohort_retention",
    "ABTestAnalyzer",
    "ABTestResult",
    "SRMResult",
    "compute_srm_test",
    "compute_two_proportion_ztest",
    "run_all_analytics",
]
