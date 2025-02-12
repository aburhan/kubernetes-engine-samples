terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.20"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ************************************************** #
# Assign IAM Roles to Provided Service Account
# ************************************************** #
resource "google_project_iam_member" "bq_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${var.service_account_email}"
}

resource "google_project_iam_member" "bq_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${var.service_account_email}"
}

# ************************************************** #
# Create BigQuery Dataset
# ************************************************** #
resource "google_bigquery_dataset" "gke-workload_metrics" {
  dataset_id  = var.dataset_id
  project     = var.project_id
  location    = var.region
  description = "Dataset for workload forecast metrics"
}

# ************************************************** #
# Create BigQuery Table
# ************************************************** #
resource "google_bigquery_table" "workload_recommendations" {
  dataset_id = google_bigquery_dataset.workload_metrics.dataset_id
  table_id   = var.table_id
  project    = var.project_id
  deletion_protection = false

  schema = jsonencode([
    { name = "run_date", type = "DATETIME", mode = "NULLABLE" },
    { name = "window_begin", type = "DATETIME", mode = "NULLABLE" },
    { name = "site_id", type = "STRING", mode = "NULLABLE" },
    { name = "vertical_id", type = "STRING", mode = "NULLABLE" },
    { name = "num_replicas_at_usage_window", type = "INTEGER", mode = "NULLABLE" },
    { name = "sum_containers_cpu_request", type = "FLOAT", mode = "NULLABLE" },
    { name = "sum_containers_cpu_usage", type = "FLOAT", mode = "NULLABLE" },
    { name = "sum_containers_mem_request_mi", type = "FLOAT", mode = "NULLABLE" },
    { name = "sum_containers_mem_usage_mi", type = "FLOAT", mode = "NULLABLE" },
    { name = "forecast_replicas_up_and_running", type = "INTEGER", mode = "NULLABLE" },
    { name = "forecast_sum_cpu_up_and_running", type = "FLOAT", mode = "NULLABLE" },
    { name = "forecast_sum_mem_up_and_running", type = "FLOAT", mode = "NULLABLE" },
    { name = "forecast_cpu_saving", type = "FLOAT", mode = "NULLABLE" },
    { name = "forecast_mem_saving_mi", type = "FLOAT", mode = "NULLABLE" },
    { name = "avg_saving_in_cpus", type = "FLOAT", mode = "NULLABLE" },
    { name = "method", type = "STRING", mode = "NULLABLE" }
  ])
}

# ************************************************** #
# Create Artifact Registry for Docker Images
# ************************************************** #
resource "google_artifact_registry_repository" "docker_registry" {
  provider      = google
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_id
  format        = "python"

  description = "Python repository for workload forecasting"
}
