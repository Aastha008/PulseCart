"""
PulseCart Kedro Pipeline: Executive Reporting & BI Integration.
"""

from kedro.pipeline import Pipeline, node
from .nodes import (
    generate_executive_summary_node,
    trigger_power_bi_refresh_node,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Creates the executive reporting and BI refresh pipeline."""
    return Pipeline(
        [
            node(
                func=generate_executive_summary_node,
                inputs=[
                    "funnel_analysis_report",
                    "cohort_retention_report",
                    "ab_test_results_report",
                ],
                outputs="statistical_summary_report",
                name="generate_executive_summary_node",
                tags=["reporting", "summary", "executive"],
            ),
            node(
                func=trigger_power_bi_refresh_node,
                inputs=["statistical_summary_report", "params:power_bi"],
                outputs="power_bi_refresh_status",
                name="trigger_power_bi_refresh_node",
                tags=["reporting", "power_bi", "bi_refresh"],
            ),
        ]
    )
