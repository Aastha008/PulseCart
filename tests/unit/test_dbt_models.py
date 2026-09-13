"""
PulseCart dbt Models & BigQuery Transformation Engine - Unit Test Suite.
Validates SQL compilation, DuckDB compatibility translation, model execution,
schema types, primary key uniqueness/non-nullness, foreign key referential integrity,
and financial accounting consistency across all 4 layers (18 models).
"""

import os
import sys
import pytest
import pandas as pd
import duckdb
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from run_dbt import (
    DbtExecutionEngine,
    translate_bq_to_duckdb_sql,
    split_top_level_args,
    extract_function_calls,
    MODELS_DIR,
    RAW_DATA_DIR,
)


# ===========================================================================
# 1. Unit Tests for SQL Dialect Translation & Parsing
# ===========================================================================
class TestSqlDialectTranslation:
    """Validates the translation of BigQuery-specific syntax to DuckDB ANSI SQL."""

    def test_split_top_level_args_simple(self):
        args = split_top_level_args("a, b, c")
        assert args == ["a", "b", "c"]

    def test_split_top_level_args_nested_parentheses(self):
        args = split_top_level_args("CURRENT_TIMESTAMP(), CAST(COALESCE(x, y) AS TIMESTAMP), DAY")
        assert len(args) == 3
        assert args[0] == "CURRENT_TIMESTAMP()"
        assert args[1] == "CAST(COALESCE(x, y) AS TIMESTAMP)"
        assert args[2] == "DAY"

    def test_extract_function_calls(self):
        sql = "SELECT TIMESTAMP_DIFF(end_ts, start_ts, SECOND), TIMESTAMP_DIFF(t2, t1, DAY) FROM tbl"
        calls = extract_function_calls(sql, "TIMESTAMP_DIFF")
        assert len(calls) == 2
        assert calls[0][1] == ["end_ts", "start_ts", "SECOND"]
        assert calls[1][1] == ["t2", "t1", "DAY"]

    def test_translate_timestamp_diff(self):
        sql = "SELECT TIMESTAMP_DIFF(end_time, start_time, SECOND) AS duration"
        translated = translate_bq_to_duckdb_sql(sql)
        assert "date_diff('second', start_time, end_time)" in translated

    def test_translate_date_diff(self):
        sql = "SELECT DATE_DIFF(d2, d1, MONTH) AS month_diff"
        translated = translate_bq_to_duckdb_sql(sql)
        assert "date_diff('month', d1, d2)" in translated

    def test_translate_date_trunc(self):
        sql = "SELECT DATE_TRUNC(order_date, MONTH) AS order_month"
        translated = translate_bq_to_duckdb_sql(sql)
        assert "date_trunc('month', order_date)" in translated

    def test_translate_logical_or(self):
        sql = "SELECT LOGICAL_OR(event_type = 'purchase') AS has_purchase"
        translated = translate_bq_to_duckdb_sql(sql)
        assert "bool_or(event_type = 'purchase')" in translated

    def test_translate_format_date(self):
        sql = "SELECT FORMAT_DATE('%B', date_day) AS month_name"
        translated = translate_bq_to_duckdb_sql(sql)
        assert "strftime(date_day, '%B')" in translated

    def test_translate_dbt_jinja_references(self):
        sql = "SELECT * FROM {{ ref('stg_users') }} JOIN {{ source('raw_pulsecart', 'raw_orders') }} USING (user_id)"
        translated = translate_bq_to_duckdb_sql(sql)
        assert "{{ ref('stg_users') }}" not in translated
        assert "stg_users" in translated
        assert "raw_orders" in translated

    def test_translate_strip_config_and_incremental(self):
        sql = """
        {{ config(materialized = 'incremental', unique_key = 'id') }}
        SELECT * FROM stg_sessions
        {% if is_incremental() %}
          WHERE session_start > '2025-01-01'
        {% endif %}
        """
        translated = translate_bq_to_duckdb_sql(sql)
        assert "config(" not in translated
        assert "is_incremental" not in translated
        assert "WHERE session_start" not in translated


# ===========================================================================
# 2. Fixture: Shared In-Memory Engine with Executed Models
# ===========================================================================
@pytest.fixture(scope="module")
def executed_dbt_engine():
    """Initializes DuckDB engine, loads raw data, and executes all 18 models."""
    engine = DbtExecutionEngine(db_path=":memory:")
    engine.ingest_raw_sources()
    engine.execute_models()
    return engine


# ===========================================================================
# 3. Model Materialization & Schema Tests
# ===========================================================================
class TestDbtModelExecution:
    """Verifies that all 18 models materialize with valid row counts and non-empty columns."""

    def test_all_18_models_exist(self, executed_dbt_engine):
        tables = executed_dbt_engine.conn.execute("SHOW TABLES").fetchall()
        table_names = {t[0] for t in tables}

        expected_staging = {
            "stg_users",
            "stg_sessions",
            "stg_events",
            "stg_orders",
            "stg_order_items",
            "stg_products",
        }
        expected_intermediate = {
            "int_session_funnel_events",
            "int_order_items_aggregated",
            "int_user_order_summary",
            "int_user_cohort_monthly",
            "int_ab_session_conversions",
        }
        expected_marts = {
            "fct_funnel",
            "fct_orders",
            "fct_user_retention",
            "fct_ab_test",
            "dim_users",
            "dim_products",
            "dim_date",
        }
        all_expected = expected_staging | expected_intermediate | expected_marts
        assert all_expected.issubset(table_names), f"Missing models: {all_expected - table_names}"

    def test_staging_users_schema_and_counts(self, executed_dbt_engine):
        df = executed_dbt_engine.conn.execute("SELECT * FROM stg_users LIMIT 5").df()
        expected_cols = {
            "user_id",
            "signup_timestamp",
            "signup_date",
            "cohort_month",
            "country",
            "customer_segment",
            "acquisition_channel",
        }
        assert expected_cols.issubset(set(df.columns))
        count = executed_dbt_engine.conn.execute("SELECT COUNT(*) FROM stg_users").fetchone()[0]
        assert count > 0

    def test_staging_sessions_duration(self, executed_dbt_engine):
        min_dur = executed_dbt_engine.conn.execute("SELECT MIN(session_duration_seconds) FROM stg_sessions").fetchone()[0]
        assert min_dur >= 0

    def test_intermediate_funnel_furthest_step(self, executed_dbt_engine):
        res = executed_dbt_engine.conn.execute("""
            SELECT MIN(furthest_step_reached), MAX(furthest_step_reached) 
            FROM int_session_funnel_events
        """).fetchone()
        assert res[0] >= 1
        assert res[1] <= 6

    def test_marts_dim_date_range(self, executed_dbt_engine):
        res = executed_dbt_engine.conn.execute("""
            SELECT MIN(date_day), MAX(date_day), COUNT(*) FROM dim_date
        """).fetchone()
        assert str(res[0])[:10] == "2024-01-01"
        assert str(res[1])[:10] == "2026-12-31"
        assert res[2] == 1096  # 366 (2024 leap year) + 365 + 365


# ===========================================================================
# 4. Primary Key & Referential Integrity Tests
# ===========================================================================
class TestIntegrityConstraints:
    """Verifies uniqueness, non-null primary keys, and foreign key referential integrity."""

    @pytest.mark.parametrize(
        "table,pk",
        [
            ("stg_users", "user_id"),
            ("stg_sessions", "session_id"),
            ("stg_events", "event_id"),
            ("stg_orders", "order_id"),
            ("stg_order_items", "order_item_id"),
            ("stg_products", "product_id"),
            ("fct_funnel", "session_id"),
            ("fct_orders", "order_id"),
            ("fct_ab_test", "session_id"),
            ("dim_users", "user_id"),
            ("dim_products", "product_id"),
            ("dim_date", "date_day"),
        ],
    )
    def test_pk_unique_and_not_null(self, executed_dbt_engine, table, pk):
        # Null check
        null_count = executed_dbt_engine.conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {pk} IS NULL"
        ).fetchone()[0]
        assert null_count == 0, f"{table}.{pk} contains nulls"

        # Unique check
        dup_count = executed_dbt_engine.conn.execute(
            f"SELECT COUNT(*) FROM (SELECT {pk} FROM {table} GROUP BY {pk} HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        assert dup_count == 0, f"{table}.{pk} contains duplicates"

    def test_referential_integrity_fct_orders_to_dim_users(self, executed_dbt_engine):
        orphans = executed_dbt_engine.conn.execute("""
            SELECT COUNT(*) FROM fct_orders o
            LEFT JOIN dim_users u ON o.user_id = u.user_id
            WHERE u.user_id IS NULL
        """).fetchone()[0]
        assert orphans == 0, "fct_orders contains orphan user_ids"

    def test_referential_integrity_fct_orders_to_fct_funnel(self, executed_dbt_engine):
        orphans = executed_dbt_engine.conn.execute("""
            SELECT COUNT(*) FROM fct_orders o
            LEFT JOIN fct_funnel f ON o.session_id = f.session_id
            WHERE f.session_id IS NULL
        """).fetchone()[0]
        assert orphans == 0, "fct_orders contains orphan session_ids"

    def test_referential_integrity_fct_funnel_to_dim_users(self, executed_dbt_engine):
        orphans = executed_dbt_engine.conn.execute("""
            SELECT COUNT(*) FROM fct_funnel f
            LEFT JOIN dim_users u ON f.user_id = u.user_id
            WHERE u.user_id IS NULL
        """).fetchone()[0]
        assert orphans == 0, "fct_funnel contains orphan user_ids"

    def test_referential_integrity_fct_ab_test_to_dim_users(self, executed_dbt_engine):
        orphans = executed_dbt_engine.conn.execute("""
            SELECT COUNT(*) FROM fct_ab_test ab
            LEFT JOIN dim_users u ON ab.user_id = u.user_id
            WHERE u.user_id IS NULL
        """).fetchone()[0]
        assert orphans == 0, "fct_ab_test contains orphan user_ids"


# ===========================================================================
# 5. Financial & Accounting Integrity Tests
# ===========================================================================
class TestFinancialIntegrity:
    """Verifies financial metrics, gross margin math, and revenue consistency."""

    def test_fct_orders_positive_revenue(self, executed_dbt_engine):
        bad_rev = executed_dbt_engine.conn.execute(
            "SELECT COUNT(*) FROM fct_orders WHERE total_amount <= 0"
        ).fetchone()[0]
        assert bad_rev == 0, "fct_orders has zero or negative total_amount"

    def test_fct_orders_gross_profit_bound(self, executed_dbt_engine):
        # Gross profit must be positive and not exceed total amount
        bad_profit = executed_dbt_engine.conn.execute(
            "SELECT COUNT(*) FROM fct_orders WHERE gross_profit < 0 OR gross_profit > total_amount"
        ).fetchone()[0]
        assert bad_profit == 0, "fct_orders gross_profit out of bounds"

    def test_dim_products_margin_rate(self, executed_dbt_engine):
        bad_margins = executed_dbt_engine.conn.execute(
            "SELECT COUNT(*) FROM dim_products WHERE margin_rate <= 0 OR margin_rate >= 1"
        ).fetchone()[0]
        assert bad_margins == 0, "dim_products has margin_rate outside (0, 1)"


# ===========================================================================
# 6. A/B Experiment & Funnel Logic Tests
# ===========================================================================
class TestExperimentAndFunnelLogic:
    """Verifies A/B variant assignment and funnel stage order invariants."""

    def test_ab_variant_accepted_values(self, executed_dbt_engine):
        variants = executed_dbt_engine.conn.execute(
            "SELECT DISTINCT ab_variant FROM fct_ab_test"
        ).fetchall()
        val_set = {v[0] for v in variants}
        assert val_set == {"control", "treatment"}

    def test_ab_conversion_binary(self, executed_dbt_engine):
        bad_flags = executed_dbt_engine.conn.execute(
            "SELECT COUNT(*) FROM fct_ab_test WHERE completed_purchase NOT IN (0, 1)"
        ).fetchone()[0]
        assert bad_flags == 0

    def test_funnel_stage_ordering_invariants(self, executed_dbt_engine):
        # Sessions with has_purchase = TRUE must have reached_purchase = 1 and stage_order = 6
        bad_stages = executed_dbt_engine.conn.execute("""
            SELECT COUNT(*) FROM fct_funnel 
            WHERE has_purchase = TRUE AND funnel_stage_order != 6
        """).fetchone()[0]
        assert bad_stages == 0


# ===========================================================================
# 7. Schema Test Runner Integration Test
# ===========================================================================
class TestSchemaTestRunner:
    """Verifies that engine.run_tests() executes the 40+ dbt tests with 0 failures."""

    def test_schema_tests_pass_zero_failures(self, executed_dbt_engine):
        passed, failed = executed_dbt_engine.run_tests()
        assert passed >= 40, f"Expected at least 40 tests, got {passed}"
        assert failed == 0, f"Expected 0 failures, got {failed} failures"
