import os

USER_AGENT = f"cloud-solutions/gke-vpa-recommendations-v1.2"

# --- Configuration ---
PROJECT_ID = os.environ.get("PROJECT_ID")
if not PROJECT_ID:
    raise EnvironmentError("PROJECT_ID environment variable must be set")

PUBSUB_TOPIC_ID = os.environ.get("PUBSUB_TOPIC_ID")
if not PUBSUB_TOPIC_ID:
    raise EnvironmentError("PUBSUB_TOPIC_ID environment variable not set")

METRIC_TYPE = "kubernetes.io/container/cpu/core_usage_time"

BASE_URL = f"https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}"
METRICS_SCOPE = "https://www.googleapis.com/auth/monitoring.read"

# Cloud Monitoring
GROUP_BY_FIELDS = [
    'resource.label.location',
    'resource.label.project_id',
    'resource.label.cluster_name',
    'resource.label.namespace_name',
    'resource.label.container_name',
    'metadata.system_labels.top_level_controller_name',
    'metadata.system_labels.top_level_controller_type']
SCALE_GROUP_BY_FIELDS = [
    'resource.label.location',
    'resource.label.project_id',
    'resource.label.cluster_name',
    'resource.label.namespace_name',
    'metric.label.container_name',
    'resource.label.controller_kind',
    'resource.label.controller_name']

# Default Filters
DEFAULT_EXCLUDED_NAMESPACES = [
    "kube-system",
    "istio-system",
    "gatekeeper-system",
    "gke-system",
    "gmp-system",
    "gke-gmp-system",
    "gke-managed-filestorecsi",
    "gke-mcs",
    "gke-managed-cim"
]

DEFAULT_INCLUDED_K8S_OBJECTS = ["Deployment"]

USAGE_METRIC_WINDOW = int(os.environ.get("METRIC_WINDOW","2592000"))

METRIC_WINDOW = int(os.environ.get("METRIC_WINDOW", "300"))

# Logging Configuration
LOGGING_CONFIG = {
    "format": "%(asctime)s - %(levelname)s - %(message)s",
}

METRIC_QUERIES = [
  {
    "metric": "kubernetes.io/container/cpu/core_usage_time",
    "window": USAGE_METRIC_WINDOW,
    "per_series_aligner": "ALIGN_RATE",
    "cross_series_reducer": "REDUCE_PERCENTILE_99",
    "data_type": "double_value",
    "columns": GROUP_BY_FIELDS
  },
  {
    "metric": "kubernetes.io/container/cpu/request_cores",
    "window": METRIC_WINDOW,
    "per_series_aligner": "ALIGN_MEAN",
    "cross_series_reducer": "REDUCE_MEAN",
    "data_type": "double_value",
    "columns": GROUP_BY_FIELDS
  },
  {
    "metric": "kubernetes.io/container/cpu/limit_cores",
    "window": METRIC_WINDOW,
    "per_series_aligner": "ALIGN_MEAN",
    "cross_series_reducer": "REDUCE_MEAN",
    "data_type": "double_value",
    "columns": GROUP_BY_FIELDS
  },
  {
    "metric": "kubernetes.io/container/memory/used_bytes",
    "window": USAGE_METRIC_WINDOW,
    "per_series_aligner": "ALIGN_MAX",
    "cross_series_reducer": "REDUCE_MAX",
    "data_type": "double_value",
    "columns": GROUP_BY_FIELDS
  },
  {
    "metric": "kubernetes.io/container/memory/request_bytes",
    "window": METRIC_WINDOW,
    "per_series_aligner": "ALIGN_MEAN",
    "cross_series_reducer": "REDUCE_MEAN",
    "data_type": "double_value",
    "columns": GROUP_BY_FIELDS
  },
  {
    "metric": "kubernetes.io/container/memory/limit_bytes",
    "window": METRIC_WINDOW,
    "per_series_aligner": "ALIGN_MEAN",
    "cross_series_reducer": "REDUCE_MEAN",
    "data_type": "double_value",
    "columns": GROUP_BY_FIELDS
  },]
