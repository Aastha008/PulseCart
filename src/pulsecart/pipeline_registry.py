"""
PulseCart Kedro Pipeline Registry.

Kedro Concept: Pipeline Registry
--------------------------------
The Pipeline Registry acts as the routing and discovery engine for a project.
It maps human-readable pipeline names (used in CLI commands like
`kedro run --pipeline dbt_pipeline`) to composite `Pipeline` objects.

In PulseCart, we expose:
1. `__default__`: The complete end-to-end pipeline:
   Raw Ingestion Check -> dbt Staging -> dbt Intermediate -> dbt Marts ->
   dbt Schema Tests (115 assertions) -> Funnel Analytics -> Cohort Retention ->
   Checkout A/B Experiment -> Executive Summary JSON -> Power BI Dataset Refresh.
2. `dbt_pipeline`: Isolates in-warehouse dbt execution and schema testing.
3. `analytics_pipeline`: Executes Python statistical engines on materialized marts.
4. `reporting_pipeline`: Consolidates deliverables and triggers BI refresh.
"""

from typing import Dict
from kedro.pipeline import Pipeline
from pulsecart.pipelines import (
    dbt_transforms,
    statistical_analytics,
    reporting,
)


def register_pipelines() -> Dict[str, Pipeline]:
    """Registers the project's pipelines for execution and CLI discovery."""
    dbt_p = dbt_transforms.create_pipeline()
    analytics_p = statistical_analytics.create_pipeline()
    reporting_p = reporting.create_pipeline()

    default_pipeline = dbt_p + analytics_p + reporting_p

    return {
        "__default__": default_pipeline,
        "dbt_pipeline": dbt_p,
        "analytics_pipeline": analytics_p,
        "reporting_pipeline": reporting_p,
        "analytics_and_reporting": analytics_p + reporting_p,
    }
