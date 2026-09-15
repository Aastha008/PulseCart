"""
PulseCart Kedro Nodes: dbt & Data Warehouse Wrapper.

Kedro Concept: Nodes
--------------------
A Node is a pure Python function with explicit inputs and outputs, wrapped in
Kedro's `node()` construct. Nodes are decoupled from physical storage; they
receive data loaded by the Data Catalog and return data to be saved by the Catalog.

In this pipeline, instead of rewriting the SQL transformations, we wrap the
existing dbt / BigQuery transformations as Kedro nodes. This guarantees:
1. SQL logic stays in the data warehouse / dbt layer (pushdown ELT).
2. Kedro orchestrates lineage, dependencies, schema tests, and downstream Python nodes.
3. Full observability across both SQL execution and statistical modeling.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict
import pandas as pd

# Add pulsecart root to path for run_dbt runner
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_dbt import DbtExecutionEngine

logger = logging.getLogger(__name__)


def validate_raw_sources_node(
    raw_users: pd.DataFrame,
    raw_sessions: pd.DataFrame,
    raw_events: pd.DataFrame,
    raw_orders: pd.DataFrame,
    raw_order_items: pd.DataFrame,
    raw_products: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Validates that all raw ingestion datasets are present, non-empty,
    and meet basic integrity contracts before triggering dbt transformations.

    Inputs are automatically loaded by Kedro via catalog.yml.
    """
    logger.info("Validating raw landing datasets in Kedro Data Catalog...")
    table_counts = {
        "users": len(raw_users),
        "sessions": len(raw_sessions),
        "events": len(raw_events),
        "orders": len(raw_orders),
        "order_items": len(raw_order_items),
        "products": len(raw_products),
    }

    for tbl, count in table_counts.items():
        if count == 0:
            raise ValueError(f"Raw source dataset '{tbl}' is empty in Data Catalog!")
        logger.info(f"  - Verified raw_{tbl}: {count:,} records")

    return {
        "status": "VALIDATED",
        "timestamp": time.time(),
        "table_counts": table_counts,
    }


def run_dbt_models_node(
    raw_status: Dict[str, Any],
    dbt_params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executes the 18 dbt models across staging, intermediate, and marts layers.
    Wraps existing dbt/BigQuery SQL logic without rewriting.

    In production with BigQuery, this executes `dbt run --target bigquery`.
    Locally, it executes via DuckDB with BigQuery dialect compatibility macros.
    """
    logger.info("Starting dbt compilation and model execution across staging, intermediate, and marts...")
    t0 = time.time()

    engine = DbtExecutionEngine()
    engine.ingest_raw_sources()
    model_results = engine.execute_models()
    engine.export_marts()

    duration = round(time.time() - t0, 2)
    logger.info(f"dbt execution completed successfully in {duration}s. Materialized {len(model_results)} models.")

    return {
        "status": "SUCCESS",
        "duration_seconds": duration,
        "models_materialized": model_results,
    }


def run_dbt_tests_node(
    dbt_run_status: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executes automated dbt schema tests (uniqueness, not-null, referential integrity, accepted values).
    Acts as a Kedro Data Quality Circuit Breaker: if test failures > 0, halts downstream execution.
    """
    logger.info("Executing dbt schema & referential integrity tests (115 assertions)...")
    engine = DbtExecutionEngine()
    engine.ingest_raw_sources()
    engine.execute_models()
    passed, failed = engine.run_tests()

    if failed > 0:
        logger.critical(f"Data Quality Circuit Breaker Tripped! {failed} tests failed.")
        raise RuntimeError(f"dbt tests failed: {failed} failures detected.")

    logger.info(f"All {passed} dbt schema tests passed with 0 errors.")
    return {
        "status": "PASSED",
        "tests_passed": passed,
        "tests_failed": failed,
    }
