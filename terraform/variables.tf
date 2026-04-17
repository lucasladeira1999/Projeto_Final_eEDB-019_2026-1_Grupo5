variable "postgres_password" {
  description = "Senha do usuário PostgreSQL"
  type        = string
  sensitive   = true
}

variable "postgres_user" {
  description = "Usuário PostgreSQL"
  type        = string
  default     = "bike_user"
}

variable "postgres_db" {
  description = "Banco principal do pipeline"
  type        = string
  default     = "bike_elt"
}

variable "airflow_user" {
  description = "Usuário admin do Airflow"
  type        = string
  default     = "airflow"
}

variable "airflow_password" {
  description = "Senha do usuário admin do Airflow"
  type        = string
  sensitive   = true
}
