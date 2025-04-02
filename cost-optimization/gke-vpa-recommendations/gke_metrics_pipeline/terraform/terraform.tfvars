# Required Variables (You MUST provide these)
monitoring_project_id = "your-monitoring-gcp-project-id"  # Replace with your Monitoring Project ID

# Optional Variables (You can customize or leave as is)
region = "us-central1"  # GCP region

projects_to_monitor = [
  #"your-project-to-monitor-1",  # Replace with your Project IDs
  #"your-project-to-monitor-2",
  # Add more project IDs as needed
]

resource_labels = {
  # You can add or override labels here if needed
  # environment = "production"
  # team        = "my-team"
}

artifact_registry_location = "us-central1"  # Location for Artifact Registry

artifact_registry_name = "gke-rec-repo"  # Name for the Artifact Registry

bigquery_dataset = "gke_metric_dataset"  # The name of the BigQuery dataset

bigquery_table = "gke_metrics"  # The name of the BigQuery table

bigquery_view = "container_recommendations"  # The name of the BigQuery container recommendation vie