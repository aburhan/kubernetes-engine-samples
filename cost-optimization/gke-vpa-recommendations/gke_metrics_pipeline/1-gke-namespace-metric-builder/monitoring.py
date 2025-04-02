import requests
from config import (
    BASE_URL, METRIC_TYPE, METRIC_WINDOW, GROUP_BY_FIELDS, USER_AGENT)
from utils import (
    get_auth_token,
    get_time_interval,
    build_namespace_filter,
    build_included_objects_filter
    )


def call_cloud_monitoring_api():
    """
    Calls the Cloud Monitoring API and returns time series data.
    """
    filter_expression = (
        f'{build_namespace_filter()} AND {build_included_objects_filter()}')
    start_time, end_time = get_time_interval(METRIC_WINDOW)

    params = {
        "filter": f'metric.type="{METRIC_TYPE}" AND {filter_expression}',
        "interval.startTime": start_time,
        "interval.endTime": end_time,
        "aggregation.alignmentPeriod": f"{METRIC_WINDOW}s",
        "aggregation.perSeriesAligner": "ALIGN_RATE",
        "aggregation.crossSeriesReducer": "REDUCE_SUM",
        "aggregation.groupByFields": GROUP_BY_FIELDS + ['resource.label.pod_name'],
        "secondaryAggregation.crossSeriesReducer": "REDUCE_COUNT",
        "secondaryAggregation.groupByFields": GROUP_BY_FIELDS,
    }

    headers = {
        "Authorization": f"Bearer {get_auth_token()}",
        'User-Agent': USER_AGENT
    }

    try:
        response = requests.get(f"{BASE_URL}/timeSeries", headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Error calling Cloud Monitoring API: {e}")
