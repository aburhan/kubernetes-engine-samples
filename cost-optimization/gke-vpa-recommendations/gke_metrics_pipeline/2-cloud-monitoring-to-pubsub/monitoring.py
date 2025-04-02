import logging
import requests
from config import BASE_URL, METRICS_SCOPE, USER_AGENT
from utils import get_auth_token
from datetime import datetime, timedelta, timezone

def build_cloud_monitoring_param(message_data):
    """
    Calls the Cloud Monitoring API to get the number of replicas
    for the controllers in the message.
    """
    project_id = message_data["project"]
    cluster = message_data["cluster"]
    namespace = message_data["namespace"]
    location = message_data["location"]
    cloud_monitoring_query = message_data["cloud_monitoring_query"]
    metric_from_message = cloud_monitoring_query["metric"]
    window_from_message = cloud_monitoring_query["window"]
    columns_from_message = cloud_monitoring_query["columns"]

    filter_expression = (
        f'resource.labels.project_id="{project_id}" AND '
        f'resource.labels.cluster_name="{cluster}" AND '
        f'resource.labels.namespace_name="{namespace}" AND '
        f'resource.labels.location="{location}"'
    )
    window_seconds = window_from_message

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(seconds=window_seconds)
    start_time_str = start_time.isoformat(timespec='seconds').replace('+00:00', 'Z')
    end_time_str = end_time.isoformat(timespec='seconds').replace('+00:00', 'Z')

    group_by_fields = columns_from_message

    params = {
        "filter": f'metric.type="{metric_from_message}" AND {filter_expression}',
        "interval.startTime": start_time_str,
        "interval.endTime": end_time_str,
        "aggregation.alignmentPeriod": f"{window_seconds}s",
        "aggregation.perSeriesAligner": cloud_monitoring_query.get("per_series_aligner"),
        "aggregation.crossSeriesReducer": cloud_monitoring_query.get("cross_series_reducer"),
        "aggregation.groupByFields": list(set(group_by_fields)),
    }

    return params


def query_cloud_monitoring(params):
    """
    Queries Cloud Monitoring API with the given query and returns the results.

    Args:
        query (str): Query string to send to Cloud Monitoring API.

    Returns:
        dict: Cloud Monitoring API response.
    """
    access_token = get_auth_token()

    # Define headers for the API request
    headers = {
        "Authorization": f"Bearer {access_token}",
        'User-Agent': USER_AGENT
    }

    # Define request payload
    url = f"{BASE_URL}/timeSeries"

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error querying Cloud Monitoring API: {e}")
        return {"error": str(e)}
