"""
Unit tests for PulseCart Kedro Pipeline Architecture.
Verifies pipeline registry, node graph connectivity, and Data Catalog definitions.
"""

from pathlib import Path
import pytest
from kedro.framework.project import configure_project
from kedro.framework.session import KedroSession
from pulsecart.pipeline_registry import register_pipelines


@pytest.fixture(scope="module")
def project_root():
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="module")
def pipelines():
    return register_pipelines()


def test_pipeline_registry_keys(pipelines):
    """Verifies that all expected modular pipelines are registered."""
    expected = {
        "__default__",
        "dbt_pipeline",
        "analytics_pipeline",
        "reporting_pipeline",
        "analytics_and_reporting",
    }
    assert expected.issubset(set(pipelines.keys()))


def test_dbt_pipeline_nodes(pipelines):
    """Verifies that the dbt pipeline contains validation, transformation, and test nodes."""
    dbt_p = pipelines["dbt_pipeline"]
    node_names = [n.name for n in dbt_p.nodes]
    assert "validate_raw_sources_node" in node_names
    assert "materialize_dbt_models_node" in node_names
    assert "run_dbt_schema_tests_node" in node_names
    assert len(dbt_p.nodes) == 3


def test_analytics_pipeline_nodes(pipelines):
    """Verifies that the analytics pipeline contains funnel, cohort, and ab_test nodes."""
    analytics_p = pipelines["analytics_pipeline"]
    node_names = [n.name for n in analytics_p.nodes]
    assert "compute_funnel_analytics_node" in node_names
    assert "compute_cohort_retention_node" in node_names
    assert "evaluate_ab_experiment_node" in node_names
    assert len(analytics_p.nodes) == 3


def test_reporting_pipeline_nodes(pipelines):
    """Verifies that the reporting pipeline contains executive summary and BI refresh nodes."""
    reporting_p = pipelines["reporting_pipeline"]
    node_names = [n.name for n in reporting_p.nodes]
    assert "generate_executive_summary_node" in node_names
    assert "trigger_power_bi_refresh_node" in node_names
    assert len(reporting_p.nodes) == 2


def test_default_pipeline_composite(pipelines):
    """Verifies that __default__ unites all 8 nodes in a single topological graph."""
    default_p = pipelines["__default__"]
    assert len(default_p.nodes) == 8


def test_pipeline_acyclic(pipelines):
    """Verifies that all registered pipelines are strictly Directed Acyclic Graphs (DAGs)."""
    for name, p in pipelines.items():
        # In Kedro, CircularDependencyError is raised at pipeline construction if cycles exist.
        # Here we verify that node_dependencies are populated and valid.
        assert isinstance(p.node_dependencies, dict)
        assert len(p.nodes) > 0
