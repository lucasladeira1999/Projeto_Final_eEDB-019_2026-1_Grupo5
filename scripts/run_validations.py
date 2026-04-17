import json
import os
from pathlib import Path

import great_expectations as gx

BASE_DIR = Path(__file__).resolve().parent.parent
GE_DIR = BASE_DIR / "great_expectations"
REPORT_DIR = BASE_DIR / "logs" / "validations"


def connection_string() -> str:
    user = os.getenv("POSTGRES_USER", "bike_user")
    password = os.getenv("POSTGRES_PASSWORD", "bike_pass")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    database = os.getenv("POSTGRES_DB", "bike_elt")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"


def ensure_datasource(context) -> None:
    datasource_name = "raw_postgres"
    try:
        context.get_datasource(datasource_name)
        return
    except Exception:
        pass

    context.add_datasource(
        name=datasource_name,
        class_name="Datasource",
        execution_engine={
            "class_name": "SqlAlchemyExecutionEngine",
            "connection_string": connection_string(),
        },
        data_connectors={
            "default_inferred_data_connector_name": {
                "class_name": "InferredAssetSqlDataConnector",
                "include_schema_name": True,
            }
        },
    )


def run_checkpoint() -> None:
    context = gx.get_context(context_root_dir=str(GE_DIR))
    ensure_datasource(context)

    result = context.run_checkpoint(checkpoint_name="raw_trips_checkpoint")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / "raw_trips_checkpoint_result.json"
    with report_file.open("w", encoding="utf-8") as file_obj:
        json.dump(result.to_json_dict(), file_obj, indent=2)

    context.build_data_docs()
    print(f"Resultado do checkpoint salvo em: {report_file}")

    if not result.success:
        raise RuntimeError("Validação Great Expectations falhou.")


if __name__ == "__main__":
    run_checkpoint()
