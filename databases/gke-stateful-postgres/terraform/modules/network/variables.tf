variable "project_id" {
  description = "The project ID to host the cluster in"
}
variable "primary_region" {
  description = "The project ID to host the cluster in"
  default     = "us-central1"
}

variable "backup_region" {
  description = "The project ID to host the cluster in"
  default     = "us-west1"
}