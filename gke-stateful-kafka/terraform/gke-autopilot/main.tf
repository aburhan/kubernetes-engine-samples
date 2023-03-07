# google_client_config and kubernetes provider must be explicitly specified like the following.
data "google_client_config" "default" {}

module "network" {
  source     = "../modules/network"
  project_id = var.project_id
}

module "gke-us-central1-autopilot" {
  source                          = "terraform-google-modules/kubernetes-engine/google//modules/beta-autopilot-private-cluster"
  project_id                      = var.project_id
  name                            = "gke-kafka-us-central1"
  kubernetes_version              = "1.24.2-gke.1900" # Will be ignored if use "REGULAR" release_channel
  # release_channel                 = "REGULAR" # Default version is 1.22 in REGULAR so commented it out to specify V1.24 via var.kubernetes_version
  region                          = "us-central1"
  regional                        = true
  zones                           = ["us-central1-a", "us-central1-b", "us-central1-c"]
  network                         = module.network.network_name
  subnetwork                      = module.network.primary_subnet_name
  ip_range_pods                   = "ip-range-pods-us-central1"
  ip_range_services               = "ip-range-svc-us-central1"
  horizontal_pod_autoscaling      = true
  enable_vertical_pod_autoscaling = true
  enable_private_endpoint         = false
  enable_private_nodes            = true
  master_ipv4_cidr_block          = "172.16.0.32/28"
  create_service_account          = false
}

module "gke-us-west1-autopilot" {
  source                          = "terraform-google-modules/kubernetes-engine/google//modules/beta-autopilot-private-cluster"
  project_id                      = var.project_id
  name                            = "gke-kafka-us-west1"
  kubernetes_version              = "1.24.2-gke.1900" # Will be ignored if use "REGULAR" release_channel
  # release_channel                 = "REGULAR" # Default version is 1.22 in REGULAR so commented it out to specify V1.24 via var.kubernetes_version
  region                          = "us-central1"
  regional                        = true
  zones                           = ["us-central1-a", "us-central1-b", "us-central1-c"]
  network                         = module.network.network_name
  subnetwork                      = module.network.secondary_subnet_name
  ip_range_pods                   = "ip-range-pods-us-central1"
  ip_range_services               = "ip-range-svc-us-central1"
  horizontal_pod_autoscaling      = true
  enable_vertical_pod_autoscaling = true
  enable_private_endpoint         = false
  enable_private_nodes            = true
  master_ipv4_cidr_block          = "172.16.0.32/28"
  create_service_account          = false
}
