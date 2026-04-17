import logging
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.etree import ElementTree

import requests
from dotenv import load_dotenv


class Bronze:
    def __init__(self) -> None:
        self.base_dir = Path(__file__).resolve().parent.parent
        self.env_file = self.base_dir / ".env"
        self.raw_dir = self.base_dir / "data" / "raw"
        self.log_dir = self.base_dir / "logs"
        self.log_file = self.log_dir / "bronze.log"
        self.timeout = 30
        self.logger = self.setup_logger()

    def setup_logger(self) -> logging.Logger:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            logger = logging.getLogger("bronze")
            logger.setLevel(logging.INFO)

            if not logger.handlers:
                file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
                formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)

            return logger
        except Exception as exc:
            raise OSError(f"Erro ao configurar o logger Bronze: {exc}") from exc

    def get_config(self) -> tuple[str, list[str], str]:
        try:
            load_dotenv(dotenv_path=self.env_file)
            base_url = os.getenv("BRONZE_BASE_URL", "").strip().rstrip("/")
            target_months_raw = os.getenv("BRONZE_TARGET_MONTHS", "").strip()
            listing_url = os.getenv("BRONZE_LISTING_URL", "").strip()

            if not base_url:
                raise ValueError("A variável BRONZE_BASE_URL não foi definida no .env.")

            if not target_months_raw:
                raise ValueError(
                    "A variável BRONZE_TARGET_MONTHS não foi definida no .env."
                )

            if not listing_url:
                raise ValueError("A variável BRONZE_LISTING_URL não foi definida no .env.")

            target_months = [
                month.strip() for month in target_months_raw.split(",") if month.strip()
            ]

            invalid_months = [
                month for month in target_months if not re.fullmatch(r"\d{4}-\d{2}", month)
            ]

            if invalid_months:
                raise ValueError(
                    "Os meses devem estar no formato YYYY-MM: "
                    + ", ".join(invalid_months)
                )

            return base_url, target_months, listing_url
        except Exception as exc:
            raise ValueError(f"Erro ao ler a configuração Bronze no .env: {exc}") from exc

    def list_available_files(self, listing_url: str) -> list[str]:
        try:
            response = requests.get(listing_url, timeout=self.timeout)
            response.raise_for_status()

            root = ElementTree.fromstring(response.text)
            namespace_uri = root.tag[root.tag.find("{") + 1 : root.tag.find("}")]
            namespace = {"s3": namespace_uri}

            keys = []
            for contents in root.findall("s3:Contents", namespace):
                key = contents.findtext("s3:Key", default="", namespaces=namespace)
                if key and key.lower().endswith(".csv"):
                    keys.append(key)

            return sorted(keys)
        except Exception as exc:
            raise ConnectionError(f"Erro ao listar os arquivos disponíveis: {exc}") from exc

    def filter_files_by_month(self, file_keys: list[str], target_month: str) -> list[str]:
        try:
            target_date = datetime.strptime(target_month, "%Y-%m")
            month_tag = target_date.strftime("%b%Y")
            matched_files = [
                file_key
                for file_key in file_keys
                if "JourneyDataExtract" in file_key and month_tag in file_key
            ]

            if not matched_files:
                raise FileNotFoundError(
                    f"Nenhum arquivo CSV encontrado para o mes {target_month}."
                )

            return sorted(matched_files)
        except Exception as exc:
            raise ValueError(
                f"Erro ao filtrar os arquivos para o mes {target_month}: {exc}"
            ) from exc

    def select_target_files(
        self,
        file_keys: list[str],
        target_months: list[str],
    ) -> list[str]:
        try:
            selected_files = []

            for target_month in target_months:
                month_files = self.filter_files_by_month(file_keys, target_month)
                self.logger.info(
                    "Arquivos encontrados para %s: %s",
                    target_month,
                    ", ".join(Path(file_key).name for file_key in month_files),
                )
                selected_files.extend(month_files)

            return sorted(set(selected_files))
        except Exception as exc:
            raise ValueError(f"Erro ao selecionar os arquivos alvo: {exc}") from exc

    def poll_source(self, url: str) -> None:
        try:
            response = requests.head(url, allow_redirects=True, timeout=self.timeout)
            response.raise_for_status()
        except Exception as exc:
            raise ConnectionError(f"Erro ao validar a URL com HEAD: {exc}") from exc

    def generate_output_path(self, url: str) -> Path:
        try:
            self.raw_dir.mkdir(parents=True, exist_ok=True)

            parsed_url = urlparse(url)
            file_name = Path(parsed_url.path).name or "bronze_file"

            return self.raw_dir / file_name
        except Exception as exc:
            raise OSError(f"Erro ao preparar o caminho em data/raw: {exc}") from exc

    def download_bronze(self, url: str, destination: Path) -> Path:
        try:
            with requests.get(url, stream=True, timeout=self.timeout) as response:
                response.raise_for_status()

                with destination.open("wb") as file_obj:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file_obj.write(chunk)

            return destination
        except Exception as exc:
            raise IOError(f"Erro ao baixar e salvar o arquivo raw: {exc}") from exc

    def build_source_url(self, base_url: str, file_key: str) -> str:
        try:
            return f"{base_url}/{Path(file_key).name}"
        except Exception as exc:
            raise ValueError(f"Erro ao montar a URL do arquivo Bronze: {exc}") from exc

    def download_file(self, base_url: str, file_key: str) -> Path:
        try:
            source_url = self.build_source_url(base_url=base_url, file_key=file_key)
            self.logger.info("Iniciando ingestao Bronze para a URL %s", source_url)

            self.poll_source(source_url)
            output_path = self.generate_output_path(source_url)
            saved_file = self.download_bronze(source_url, output_path)

            self.logger.info(
                "Ingestao Bronze concluida com sucesso. Arquivo salvo em %s",
                saved_file,
            )
            return saved_file
        except Exception as exc:
            self.logger.exception(
                "Falha na ingestao Bronze para o arquivo %s: %s",
                file_key,
                exc,
            )
            raise

    def run(self) -> list[Path]:
        try:
            base_url, target_months, listing_url = self.get_config()
            available_files = self.list_available_files(listing_url=listing_url)
            target_files = self.select_target_files(available_files, target_months)

            saved_files = []
            for file_key in target_files:
                saved_files.append(self.download_file(base_url=base_url, file_key=file_key))

            return saved_files
        except Exception as exc:
            self.logger.exception("Falha geral na camada Bronze: %s", exc)
            raise
