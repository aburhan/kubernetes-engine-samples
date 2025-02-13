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
  default     = "gke_workload_metrics"
}

variable "table_id" {
  description = "BigQuery table ID"
  type        = string
  default     = "gke_workload_recommendations"
}

variable "artifact_registry_id" {
  description = "The ID of the Artifact Registry"
  type        = string
  default     = "workloadrecommender-repo"
}
