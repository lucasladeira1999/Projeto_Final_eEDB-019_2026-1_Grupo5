terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

resource "docker_network" "bike_pipeline" {
  name = "bike-pipeline-network"
}

resource "docker_volume" "postgres_data" {
  name = "bike-pipeline-postgres-data"
}

resource "docker_image" "postgres" {
  name         = "postgres:15"
  keep_locally = true
}

resource "docker_image" "airflow" {
  name         = "apache/airflow:2.11.1"
  keep_locally = true
}

resource "docker_container" "postgres" {
  name  = "tf-bike-postgres"
  image = docker_image.postgres.image_id

  env = [
    "POSTGRES_USER=${var.postgres_user}",
    "POSTGRES_PASSWORD=${var.postgres_password}",
    "POSTGRES_DB=${var.postgres_db}"
  ]

  ports {
    internal = 5432
    external = 5433
  }

  mounts {
    target = "/var/lib/postgresql/data"
    source = docker_volume.postgres_data.name
    type   = "volume"
  }

  networks_advanced {
    name = docker_network.bike_pipeline.name
  }
}

resource "docker_container" "airflow_webserver" {
  name  = "tf-bike-airflow-webserver"
  image = docker_image.airflow.image_id

  env = [
    "AIRFLOW__CORE__EXECUTOR=LocalExecutor",
    "AIRFLOW__CORE__LOAD_EXAMPLES=false",
    "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://${var.postgres_user}:${var.postgres_password}@tf-bike-postgres:5432/${var.postgres_db}",
    "_AIRFLOW_WWW_USER_USERNAME=${var.airflow_user}",
    "_AIRFLOW_WWW_USER_PASSWORD=${var.airflow_password}"
  ]

  command = ["webserver"]

  ports {
    internal = 8080
    external = 8081
  }

  networks_advanced {
    name = docker_network.bike_pipeline.name
  }

  depends_on = [docker_container.postgres]
}
