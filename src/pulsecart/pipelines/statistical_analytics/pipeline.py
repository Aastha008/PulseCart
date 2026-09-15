"""
PulseCart Kedro Pipeline: Statistical Analytics & Experimentation.

Kedro Concept: Topological Graph Resolution
-------------------------------------------
Kedro builds execution dependencies based on declared inputs and outputs.
These three nodes run concurrently or sequentially as their dataset dependencies
(fct_funnel, fct_user_retention, fct_orders, fct_ab_test) are satisfied by
the dbt layer or Data Catalog.
"""

from kedro.pipeline import Pipeline, node
from .nodes import (
    compute_funnel_analytics_node,
    compute_cohort_retention_node,
    evaluate_ab_experiment_node,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Creates the statistical analytics pipeline."""
    return Pipeline(
        [
            node(
                func=compute_funnel_analytics_node,
                inputs=["fct_funnel", "params:funnel"],
                outputs="funnel_analysis_report",
                name="compute_funnel_analytics_node",
                tags=["analytics", "funnel"],
            ),
            node(
                func=compute_cohort_retention_node,
                inputs=["fct_user_retention", "fct_orders", "params:cohort_retention"],
                outputs="cohort_retention_report",
                name="compute_cohort_retention_node",
                tags=["analytics", "retention", "cohorts"],
            ),
            node(
                func=evaluate_ab_experiment_node,
                inputs=["fct_ab_test", "params:ab_test"],
                outputs="ab_test_results_report",
                name="evaluate_ab_experiment_node",
                tags=["analytics", "ab_testing", "experimentation"],
            ),
        ]
    )
