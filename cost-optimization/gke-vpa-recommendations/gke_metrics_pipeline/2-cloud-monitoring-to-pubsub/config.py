import os


USER_AGENT = f"cloud-solutions/gke-vpa-recommendations-v1.2"

# --- Configuration ---
PROJECT_ID = os.environ.get("PROJECT_ID")
if not PROJECT_ID:
    raise EnvironmentError("PROJECT_ID environment variable must be set")

PUBSUB_SUBSCRIPTION_ID = os.environ.get("PUBSUB_SUBSCRIPTION_ID")
if not PUBSUB_SUBSCRIPTION_ID:
    raise EnvironmentError("PUBSUB_SUBSCRIPTION_ID environment variable not set")

DESTINATION_PUBSUB_TOPIC_ID = os.environ.get("DESTINATION_PUBSUB_TOPIC_ID")

if not DESTINATION_PUBSUB_TOPIC_ID:
    raise EnvironmentError("DESTINATION_PUBSUB_TOPIC_ID environment variable not set")

BASE_URL = f"https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}"

METRICS_SCOPE = "https://www.googleapis.com/auth/monitoring.read"

# Logging Configuration
LOGGING_CONFIG = {
    "format": "%(asctime)s - %(levelname)s - %(message)s",
}
