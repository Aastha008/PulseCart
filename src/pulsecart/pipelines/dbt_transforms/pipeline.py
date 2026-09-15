"""
PulseCart Kedro Pipeline: dbt Transforms.

Kedro Concept: Pipeline
-----------------------
A Pipeline represents a collection of nodes with directed dependencies. Kedro
automatically builds a Directed Acyclic Graph (DAG) by matching the outputs of
one node to the inputs of another via topological sort.
"""

from kedro.pipeline import Pipeline, node
from .nodes import (
    validate_raw_sources_node,
    run_dbt_models_node,
    run_dbt_tests_node,
)


def create_pipeline(**kwargs) -> Pipeline:
    """Creates the dbt transforms pipeline."""
    return Pipeline(
        [
            node(
                func=validate_raw_sources_node,
                inputs=[
                    "raw_users",
                    "raw_sessions",
                    "raw_events",
                    "raw_orders",
                    "raw_order_items",
                    "raw_products",
                ],
                outputs="raw_validation_status",
                name="validate_raw_sources_node",
                tags=["dbt", "validation", "raw"],
            ),
            node(
                func=run_dbt_models_node,
                inputs=["raw_validation_status", "params:dbt"],
                outputs="dbt_models_status",
                name="materialize_dbt_models_node",
                tags=["dbt", "staging", "intermediate", "marts"],
            ),
            node(
                func=run_dbt_tests_node,
                inputs=["dbt_models_status"],
                outputs="dbt_test_status",
                name="run_dbt_schema_tests_node",
                tags=["dbt", "data_quality", "circuit_breaker"],
            ),
        ]
    )
