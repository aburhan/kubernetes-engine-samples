data "google_client_config" "default" {}

resource "google_artifact_registry_repository" "main" {
  location      = "us"
  repository_id = "main"
  format        = "DOCKER"
}

module "network" {
  source     = "../modules/network"
  project_id = var.project_id
}

module "gke-us-central1" {
  source                 = "../modules/gke/"
  project_id             = var.project_id
  name                   = "gke-kafka-us-central1"
  regional               = true
  region                 = "us-central1"
  network                = module.network.network_name
  subnetwork             = module.network.primary_subnet_name
  ip_range_pods          = "ip-range-pods-us-central1"
  ip_range_services      = "ip-range-svc-us-central1"
  create_service_account = true

  enable_private_endpoint  = false
  enable_private_nodes     = true
  master_ipv4_cidr_block   = "172.16.0.0/28"
  remove_default_node_pool = true
  network_policy           = true
  cluster_autoscaling = {
    "enabled" : true,
    "gpu_resources" : [],
    "min_cpu_cores" : 60,
    "min_memory_gb" : 240,
    "max_cpu_cores" : 72,
    "max_memory_gb" : 288,
  }

  node_pools = [
    {
      name            = "pool-system"
      autoscaling     = true
      min_count       = 1
      max_count       = 2
      max_surge       = 1
      max_unavailable = 0
      machine_type    = "e2-standard-4"
      node_locations  = "us-central1-a,us-central1-b,us-central1-c"
      auto_repair     = true
    },
    {
      name            = "pool-kafka"
      autoscaling     = false
      max_surge       = 1
      max_unavailable = 0
      machine_type    = "e2-standard-8"
      node_locations  = "us-central1-a,us-central1-b,us-central1-c"
      auto_repair     = true
    },
    {
      name            = "pool-zookeeper"
      autoscaling     = false
      max_surge       = 1
      max_unavailable = 0
      machine_type    = "e2-standard-8"
      node_locations  = "us-central1-a,us-central1-b,us-central1-c"
      auto_repair     = true
    },
  ]

  node_pools_labels = {
    all = {}

    pool-kafka = {
      "app.stateful/component" = "kafka-broker"
    }
    pool-zookeeper = {
      "app.stateful/component" = "zookeeper"
    }
  }

  node_pools_taints = {
    all = []

    pool-kafka = [
      {
        key    = "app.stateful/component"
        value  = "kafka-broker"
        effect = "NO_SCHEDULE"
      },
    ],
    pool-zookeeper = [
      {
        key    = "app.stateful/component"
        value  = "zookeeper"
        effect = "NO_SCHEDULE"
      },
    ]
  }
}


module "gke-us-west1" {
  source                 = "../modules/gke/"
  project_id             = var.project_id
  name                   = "gke-kafka-us-west1"
  regional               = true
  region                 = "us-west1"
  network                = module.network.network_name
  subnetwork             = module.network.secondary_subnet_name
  ip_range_pods          = "ip-range-pods-us-west1"
  ip_range_services      = "ip-range-svc-us-west1"
  create_service_account = false
  service_account        = module.gke-us-central1.service_account

  enable_private_endpoint  = false
  enable_private_nodes     = true
  master_ipv4_cidr_block   = "172.16.0.16/28"
  remove_default_node_pool = true
  network_policy           = true
  cluster_autoscaling = {
    "enabled" : true,
    "gpu_resources" : [],
    "min_cpu_cores" : 60,
    "min_memory_gb" : 240,
    "max_cpu_cores" : 72,
    "max_memory_gb" : 288,
  }

  node_pools = [
    {
      name            = "pool-system"
      autoscaling     = true
      min_count       = 1
      max_count       = 2
      max_surge       = 1
      max_unavailable = 0
      machine_type    = "e2-standard-4"
      node_locations  = "us-west1-a,us-west1-b,us-west1-c"
      auto_repair     = true
    },
    {
      name            = "pool-kafka"
      autoscaling     = false
      max_surge       = 1
      max_unavailable = 0
      machine_type    = "e2-standard-8"
      node_locations  = "us-west1-a,us-west1-b,us-west1-c"
      auto_repair     = true
    },
    {
      name            = "pool-zookeeper"
      autoscaling     = false
      max_surge       = 1
      max_unavailable = 0
      machine_type    = "e2-standard-8"
      node_locations  = "us-west1-a,us-west1-b,us-west1-c"
      auto_repair     = true
    },
  ]

  node_pools_labels = {
    all = {}

    pool-kafka = {
      "app.stateful/component" = "kafka-broker"
    }
    pool-zookeeper = {
      "app.stateful/component" = "zookeeper"
    }
  }

  node_pools_taints = {
    all = []

    pool-kafka = [
      {
        key    = "app.stateful/component"
        value  = "kafka-broker"
        effect = "NO_SCHEDULE"
      },
    ],
    pool-zookeeper = [
      {
        key    = "app.stateful/component"
        value  = "zookeeper"
        effect = "NO_SCHEDULE"
      },
    ]
  }
}


resource "google_artifact_registry_repository_iam_binding" "binding" {
  project    = google_artifact_registry_repository.main.project
  location   = google_artifact_registry_repository.main.location
  repository = google_artifact_registry_repository.main.name
  role       = "roles/artifactregistry.reader"
  members = [
    "serviceAccount:${module.gke-us-central1.service_account}",
  ]
}
