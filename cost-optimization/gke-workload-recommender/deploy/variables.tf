variable "project_id" {
  description = "The ID of the Google Cloud project"
  type        = string
}

variable "region" {
  description = "The region for resources"
  type        = string
  default     = "us-central1"
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "workload_metrics"
}

variable "table_id" {
  description = "BigQuery table ID"
  type        = string
  default     = "hpa_forecast_results"
}

variable "service_account_email" {
  description = "Email of the service account (must be created manually)"
  type        = string
}

variable "artifact_registry_id" {
  description = "The ID of the Artifact Registry"
  type        = string
  default     = "workload-forecast-registry"
}
