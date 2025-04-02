import google.auth
import google.auth.transport.requests
from pubsub import publish_to_pubsub

def get_auth_token():
    """
    Authenticates with Google Cloud and retrieves an access token.

    Returns:
        str: Access token to authenticate Cloud Monitoring API requests.
    """
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/monitoring.read"])
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    return credentials.token

def get_first_point(item):
    if "timeSeries" in item and item["timeSeries"]:
        return item["timeSeries"][0].get("points", [{}])[0]
    elif "points" in item and item["points"]:
        return item["points"][0]
    return {}

def get_value_from_point(point, key):
    return point.get("value", {}).get(key)

def process_metric_value(metric_name, double_value, int64_value):
    """
    Processes metric values, converting units and selecting the appropriate value.

    Args:
        metric_name (str): The name of the metric.
        double_value (float or None): The double value of the metric.
        int64_value (int or None): The int64 value of the metric.

    Returns:
        tuple: (value, units) where value can be float, int, or None,
               and units is a string or None.
    """
    value = None
    units = None

    if int64_value is None:
        value = double_value
    elif double_value is None:
        value = int64_value
    else:
        value = double_value or int64_value  # Prioritize doubleValue if both are present

    if value is not None:
        if "memory" in metric_name:
            value = value / (1024 * 1024)  # Bytes to MiB
            units = "MiB"
        elif "cpu" in metric_name:
            value = value * 1000  # vCPU to millicores
            units = "millicores"

    return value, units

def enrich_message_and_publish_message(monitoring_data, replica_lookup):
    transformed_list = []

    for item in monitoring_data.get("timeSeries", []):
        point = get_first_point(item)

        # Extract controller name/type for lookup
        system_labels = item.get("metadata", {}).get("systemLabels", {})
        controller_name = system_labels.get("top_level_controller_name")
        controller_type = system_labels.get("top_level_controller_type")

        # Lookup replicas
        replicas = replica_lookup.get(f"{controller_name}|{controller_type}")

        metric_type = item.get("metric", {}).get("type")

        double_value = get_value_from_point(point, "doubleValue")
        int64_value = get_value_from_point(point, "int64Value")

        value, units = process_metric_value(metric_type, double_value, int64_value)

        message_data = {
            "metric": item.get("metric", {}).get("type"),
            **item.get("resource", {}).get("labels", {}),
            "startTime": point.get("interval", {}).get("startTime"),
            "endTime": point.get("interval", {}).get("endTime"),
            "value": value,
            "valueUnits": units,
            "replicas": replicas,
            "controller_name": controller_name,
            "controller_type": controller_type,
        }

        # Publish the response to the destination topic
        publish_to_pubsub(message_data )
