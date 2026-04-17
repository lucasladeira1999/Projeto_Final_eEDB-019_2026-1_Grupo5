output "postgres_connection" {
  description = "String de conexão para o PostgreSQL"
  value       = "postgresql://${var.postgres_user}:***@localhost:5433/${var.postgres_db}"
}

output "airflow_url" {
  description = "URL do Airflow Webserver"
  value       = "http://localhost:8081"
}

output "logs_hint" {
  description = "Comando para visualizar logs do container do Airflow"
  value       = "docker logs -f tf-bike-airflow-webserver"
}
