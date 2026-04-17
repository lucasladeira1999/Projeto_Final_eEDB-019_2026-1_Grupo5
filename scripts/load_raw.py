import argparse
import csv
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

import psycopg2
from psycopg2.extras import execute_values

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.bronze import Bronze


def normalize_column_name(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    normalized = normalized.replace("startstation", "start_station").replace(
        "endstation", "end_station"
    )
    return normalized


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "bike_elt"),
        user=os.getenv("POSTGRES_USER", "bike_user"),
        password=os.getenv("POSTGRES_PASSWORD", "bike_pass"),
    )


def parse_datetime(value: str):
    if not value:
        return None

    value = value.strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_int(value: str):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def ensure_raw_table(cursor):
    cursor.execute(
        """
        CREATE SCHEMA IF NOT EXISTS raw;
        CREATE TABLE IF NOT EXISTS raw.trips (
            rental_id BIGINT PRIMARY KEY,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            start_station_id INTEGER,
            end_station_id INTEGER,
            start_station_name TEXT,
            end_station_name TEXT,
            bike_id BIGINT,
            duration INTEGER,
            ingestion_file TEXT,
            loaded_at TIMESTAMP DEFAULT NOW()
        );
        """
    )


def iter_csv_rows(file_path: Path) -> Iterable[tuple]:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with file_path.open("r", newline="", encoding=encoding) as file_obj:
                reader = csv.DictReader(file_obj)
                for row in reader:
                    normalized = {normalize_column_name(k): v for k, v in row.items()}
                    rental_id = parse_int(normalized.get("rental_id"))
                    if rental_id is None:
                        continue

                    start_date = parse_datetime(normalized.get("start_date", ""))
                    end_date = parse_datetime(normalized.get("end_date", ""))

                    yield (
                        rental_id,
                        start_date,
                        end_date,
                        parse_int(normalized.get("start_station_id")),
                        parse_int(normalized.get("end_station_id")),
                        normalized.get("start_station_name"),
                        normalized.get("end_station_name"),
                        parse_int(normalized.get("bike_id")),
                        parse_int(normalized.get("duration")),
                        file_path.name,
                    )
            break
        except UnicodeDecodeError:
            continue


def load_files_into_postgres(file_paths: list[Path]) -> int:
    insert_sql = """
        INSERT INTO raw.trips (
            rental_id,
            start_date,
            end_date,
            start_station_id,
            end_station_id,
            start_station_name,
            end_station_name,
            bike_id,
            duration,
            ingestion_file
        ) VALUES %s
        ON CONFLICT (rental_id) DO UPDATE SET
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            start_station_id = EXCLUDED.start_station_id,
            end_station_id = EXCLUDED.end_station_id,
            start_station_name = EXCLUDED.start_station_name,
            end_station_name = EXCLUDED.end_station_name,
            bike_id = EXCLUDED.bike_id,
            duration = EXCLUDED.duration,
            ingestion_file = EXCLUDED.ingestion_file,
            loaded_at = NOW();
    """

    total_rows = 0
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            ensure_raw_table(cursor)
            for file_path in file_paths:
                batch = []
                for row in iter_csv_rows(file_path):
                    batch.append(row)
                    if len(batch) >= 1000:
                        execute_values(cursor, insert_sql, batch)
                        total_rows += len(batch)
                        batch = []

                if batch:
                    execute_values(cursor, insert_sql, batch)
                    total_rows += len(batch)

        conn.commit()

    return total_rows


def download_raw_files() -> list[Path]:
    bronze = Bronze()
    return bronze.run()


def discover_existing_raw_files() -> list[Path]:
    if not RAW_DIR.exists():
        return []
    return sorted(RAW_DIR.glob("*.csv"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Download e carga da camada raw.trips")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--load-only", action="store_true")
    args = parser.parse_args()

    downloaded_files: list[Path] = []

    if not args.load_only:
        downloaded_files = download_raw_files()
        print(f"Arquivos baixados: {len(downloaded_files)}")

    if args.download_only:
        return

    files_to_load = downloaded_files or discover_existing_raw_files()
    if not files_to_load:
        raise FileNotFoundError("Nenhum CSV encontrado em data/raw para carregar.")

    loaded_rows = load_files_into_postgres(files_to_load)
    print(f"Linhas carregadas/atualizadas em raw.trips: {loaded_rows}")


if __name__ == "__main__":
    main()
