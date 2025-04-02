
variable "monitoring_project_id" {
  type        = string
  description = "GCP Project ID to use as the Monitoring Project"
}
variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}
variable "projects_to_monitor" {
  type        = list(string)
  description = "List of GCP Project IDs to monitor"
  default     = []
}
variable "resource_labels" {
  type        = map(string)
  description = "Resource labels"
  default     = {}
}

variable "artifact_registry_location" {
  type        = string
  description = "Location for Artifact Registry"
  default     = "us-central1"
}

variable "artifact_registry_name" {
  type        = string
  description = "Name for the Artifact Registry"
  default     = "gke-rec-repo"
}

variable "bigquery_dataset" {
  description = "The name of the BigQuery dataset"
  default     = "gke_metric_dataset"
}

variable "bigquery_table" {
  description = "The name of the BigQuery table"
  default     = "gke_metrics"
}
variable "bigquery_view" {
  description = "The name of the BigQuery container recommendation view"
  default     = "container_recommendations"
}
variable "pubsub-namespaces-topic" {
  description = "Pubsub for namespaces and metric types to query"
  default = "gke-namespaces"
}
variable "pubsub-to-bq-topic" {
  description = "Pubsub for namespaces and metric types to query"
  default = "gke-metrics-to-bigquery"
}


locals {
  resource_labels = merge(var.resource_labels, {
    deployed_by = "cloudbuild"
    solution    = "goog-ab-gke-workload-recs"
    terraform   = "true"
  })
}
