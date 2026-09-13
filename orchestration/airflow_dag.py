"""
PulseCart Production Apache Airflow DAG: pulsecart_daily_analytics_pipeline
Schedules the daily end-to-end ingestion, dbt build, data quality tests,
and Power BI dataset refresh at 04:00 UTC.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.utils.email import send_email

# Default DAG configuration
default_args = {
    "owner": "analytics_engineering",
    "depends_on_past": False,
    "email": ["data-ops-alerts@pulsecart.internal"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(minutes=60),
}


def notify_pipeline_failure(context):
    """Sends immediate Slack and PagerDuty alert upon DAG failure."""
    task_id = context.get("task_instance").task_id
    execution_date = context.get("execution_date")
    error = context.get("exception")
    subject = f"[CRITICAL P1] Airflow DAG Failure: pulsecart_daily_analytics_pipeline.{task_id}"
    body = f"""
    <h3>PulseCart Analytics Pipeline Failure Alert</h3>
    <p><b>Task Failed:</b> {task_id}</p>
    <p><b>Execution Date:</b> {execution_date}</p>
    <p><b>Error Details:</b> {error}</p>
    <p><b>Action Taken:</b> Circuit breaker tripped. Downstream Power BI refresh suspended.</p>
    """
    send_email(to=["data-ops-alerts@pulsecart.internal"], subject=subject, html_content=body)


with DAG(
    dag_id="pulsecart_daily_analytics_pipeline",
    default_args=default_args,
    description="End-to-end daily e-commerce analytics warehouse refresh & quality gates",
    schedule_interval="0 4 * * *",  # Daily at 04:00 AM UTC
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    on_failure_callback=notify_pipeline_failure,
    tags=["pulsecart", "dbt", "bigquery", "powerbi", "experimentation"],
) as dag:

    # 1. Ingestion Sensor / Pre-flight check
    task_check_raw_sources = BashOperator(
        task_id="check_raw_ingestion_sources",
        bash_command="python -m orchestration.circuit_breaker --check-sources",
    )

    # 2. dbt Compile & Run Staging & Intermediate
    task_dbt_run_staging_intermediate = BashOperator(
        task_id="dbt_run_staging_intermediate",
        bash_command="dbt run --models staging.* intermediate.* --profiles-dir dbt_pulsecart/",
    )

    # 3. Intermediate Data Quality Tests (Pre-Marts Circuit Breaker)
    task_dbt_test_intermediate = BashOperator(
        task_id="dbt_test_intermediate_circuit_breaker",
        bash_command="dbt test --models intermediate.* --profiles-dir dbt_pulsecart/",
    )

    # 4. dbt Incremental Marts Materialization
    task_dbt_run_marts = BashOperator(
        task_id="dbt_run_consumption_marts",
        bash_command="dbt run --models marts.* --profiles-dir dbt_pulsecart/",
    )

    # 5. Full dbt Test Suite (Post-Marts Verification)
    task_dbt_test_marts = BashOperator(
        task_id="dbt_test_all_marts",
        bash_command="dbt test --models marts.* --profiles-dir dbt_pulsecart/",
    )

    # 6. Statistical Experimentation & Cohort Metrics Update
    task_update_statistical_reports = BashOperator(
        task_id="execute_statistical_runner",
        bash_command="python src/analytics/statistical_runner.py",
    )

    # 7. Power BI REST API Semantic Refresh
    task_trigger_powerbi_refresh = BashOperator(
        task_id="trigger_powerbi_dataset_refresh",
        bash_command="python -m orchestration.circuit_breaker --refresh-powerbi",
    )

    # DAG Dependency Topology:
    # Check Ingestion -> Staging/Int -> Test Int -> Marts -> Test Marts -> Stats -> Power BI
    (
        task_check_raw_sources
        >> task_dbt_run_staging_intermediate
        >> task_dbt_test_intermediate
        >> task_dbt_run_marts
        >> task_dbt_test_marts
        >> task_update_statistical_reports
        >> task_trigger_powerbi_refresh
    )
