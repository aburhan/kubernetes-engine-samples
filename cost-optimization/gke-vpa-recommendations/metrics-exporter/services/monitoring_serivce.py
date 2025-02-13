import logging
import aiohttp
import pytz
from datetime import datetime
from google.auth.transport.requests import Request
from google.auth import default
import pandas as pd
from utils.config import MetricConfig, USER_AGENT, PROJECT_ID, DEFAULT_WINDOW_DAYS, SECONDS_IN_A_DAY
from utils.helpers import _process_time_series_data

logger = logging.getLogger(__name__)

async def _fetch_timeseries_data(namespace: str, metric_config: MetricConfig, start_datetime: datetime, end_datetime: datetime) -> pd.DataFrame:
    """
    Fetch time-series data for a single namespace and metric asynchronously.

    Parameters:
        namespace (str): The namespace to fetch data for.
        metric_config (MetricConfig): The configuration for the metric.
        start_datetime (datetime): The start time for the query.
        end_datetime (datetime): The end time for the query.

    Returns:
        pd.DataFrame: A DataFrame containing the fetched data for the specified metric and namespace.
    """
    try:
        logger.info(f"Starting async data fetch for namespace '{namespace}' and metric '{metric_config.metric}'.")
        logger.debug(f"Query date range: {start_datetime} - {end_datetime}")

        # Authentication
        credentials, _ = default()
        logger.debug("Refreshing Google Cloud credentials.")
        credentials.refresh(Request())
        access_token = credentials.token

        headers = {'Authorization': f'Bearer {access_token}', 'User-Agent': USER_AGENT}

        base_url = f'https://monitoring.googleapis.com/v3/projects/{PROJECT_ID}/timeSeries'
        utc_start_datetime = start_datetime.astimezone(pytz.UTC).isoformat()
        utc_end_datetime = end_datetime.replace(second=0, microsecond=0).astimezone(pytz.UTC).isoformat()
        logger.debug(f"Formatted UTC start: {utc_start_datetime}, end: {utc_end_datetime}")

        all_time_series = []
        logger.info(f"Fetching data from URL: {base_url}")

        # Query parameters
        params = {
            'aggregation.alignmentPeriod': f'{DEFAULT_WINDOW_DAYS * SECONDS_IN_A_DAY}s',
            'aggregation.crossSeriesReducer': metric_config.cross_series_reducer,
            'aggregation.perSeriesAligner': metric_config.per_series_aligner,
            'aggregation.groupByFields': metric_config.columns,
            'filter': f'metric.type="{metric_config.metric}" AND resource.type="{metric_config.resource_type}" AND resource.labels.namespace_name="{namespace}"',
            'interval.startTime': utc_start_datetime,
            'interval.endTime': utc_end_datetime,
            'view': 'FULL',
        }

        async with aiohttp.ClientSession() as session:
            while True:
                logger.debug("Sending async request to Monitoring API.")
                async with session.get(base_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        logger.info("Async API call successful.")
                        data = await response.json()
                        logger.debug(f"Received response: {data}")

                        processed_data = _process_time_series_data(data.get("timeSeries", []), metric_config)
                        if not processed_data.empty:
                            logger.info(f"Processed data for metric '{metric_config.metric}' contains {len(processed_data)} rows.")
                            all_time_series.append(processed_data)
                        else:
                            logger.warning(f"No time-series data found for metric '{metric_config.metric}' in namespace '{namespace}'.")

                        next_page_token = data.get('nextPageToken')
                        if not next_page_token:
                            logger.debug("No next page token. Ending data fetch loop.")
                            break
                        logger.info(f"Next page token found: {next_page_token}. Fetching more data.")
                        params['pageToken'] = next_page_token
                    else:
                        logger.error(f"Async API call failed for namespace '{namespace}' and metric '{metric_config.metric}' with status {response.status}: {await response.text()}")
                        break

        result_df = pd.concat(all_time_series, ignore_index=True) if all_time_series else pd.DataFrame()
        logger.info(f"Final DataFrame for namespace '{namespace}' and metric '{metric_config.metric}' contains {len(result_df)} rows.")
        return result_df

    except Exception as e:
        logger.error(f"Error fetching data for metric '{metric_config.metric}' in namespace '{namespace}': {e}", exc_info=True)
        return pd.DataFrame()
