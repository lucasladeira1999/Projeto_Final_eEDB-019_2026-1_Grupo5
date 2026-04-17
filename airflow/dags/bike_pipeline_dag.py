from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.operators.bash import BashOperator


default_args = {
    "owner": "data-eng",
    "depends_on_past": False,
    "email": [os.getenv("AIRFLOW_ALERT_EMAIL", "alerts@example.com")],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bike_pipeline_dag",
    default_args=default_args,
    description="Pipeline ELT Santander Cycles (raw -> silver -> gold)",
    schedule_interval="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["santander-cycles", "elt"],
) as dag:
    download_raw = BashOperator(
        task_id="download_raw",
        bash_command="cd /opt/airflow && python scripts/load_raw.py --download-only",
    )

    load_to_postgres = BashOperator(
        task_id="load_to_postgres",
        bash_command="cd /opt/airflow && python scripts/load_raw.py --load-only",
    )

    validate_raw = BashOperator(
        task_id="validate_raw",
        bash_command="cd /opt/airflow && python scripts/run_validations.py",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "cd /opt/airflow/dbt_project "
            "&& dbt deps --profiles-dir . "
            "&& dbt run --profiles-dir ."
        ),
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/dbt_project && dbt test --profiles-dir .",
    )

    dbt_docs = BashOperator(
        task_id="dbt_docs",
        bash_command=(
            "cd /opt/airflow/dbt_project "
            "&& dbt docs generate --profiles-dir ."
        ),
    )

    download_raw >> load_to_postgres >> validate_raw >> dbt_run >> dbt_test >> dbt_docs
