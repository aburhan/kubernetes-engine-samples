# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Create monitored projects
resource "google_monitoring_monitored_project" "projects_monitored" {
  for_each      = toset(var.projects_to_monitor)
  metrics_scope = join("", ["locations/global/metricsScopes/", var.monitoring_project_id])
  name          = each.value
}

# Create Artifact Registry Repository
resource "google_artifact_registry_repository" "repo" {
  project      = var.monitoring_project_id
  location     = var.artifact_registry_location
  repository_id = var.artifact_registry_name
  format       = "DOCKER"
}

# Create Pubsub topics
resource "google_pubsub_topic" "gke_namespaces_queries" {
  name = var.pubsub-namespaces-topic
}

resource "google_pubsub_topic" "gke_metrics_to_bigquery" {
  name = var.pubsub-to-bq-topic
}

# Create Pubsub scriptions
resource "google_pubsub_subscription" "bigquery_subscription" {
  name  = "gke-metrics-to-bigquery"
  topic = google_pubsub_topic.gke_metrics_to_bigquery

  bigquery_config {
    table = "${google_bigquery_table.test.project}.${google_bigquery_table.test.dataset_id}.${google_bigquery_table.test.table_id}"
  }
}

# Create BigQuery table
resource "google_bigquery_dataset" "dataset" {
  dataset_id  = var.bigquery_dataset
  description = "GKE container recommendations dataset"
  location    = var.region
  labels      = var.resource_labels
}

resource "google_bigquery_table" "gke_metrics" {
  dataset_id          = google_bigquery_dataset.dataset.dataset_id
  table_id            = var.bigquery_table
  description         = "GKE system and scale metrics"
  deletion_protection = false
  
  time_partitioning {
    type = "DAY"
  }

  labels = local.resource_labels

  schema = file("../scripts/sql/bigquery_schema.json")
 
}

resource "google_bigquery_table" "workload_recommendation_view" {
  dataset_id = google_bigquery_dataset.dataset.dataset_id
  table_id   = var.bigquery_view
  deletion_protection=false
  view {
    query = templatefile("../scripts/sql/container_recommendations.sql", {
        project_id = var.monitoring_project_id,
        table_dataset = var.bigquery_dataset, table_id = var.bigquery_table })
    use_legacy_sql = false
  }
  labels = local.resource_labels
  depends_on = [google_bigquery_table.gke_metrics]
}