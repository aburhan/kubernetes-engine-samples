# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import logging
import pandas as pd
import pandas_gbq
from datetime import datetime, timedelta
from services.monitoring_serivce import _fetch_timeseries_data
from services.bigquery_service import (
    _ensure_resources_exist, _check_latest_recommendation_date, _write_dataframe_to_bigquery
)
from utils.config import MQL_QUERY, MetricConfig, USER_AGENT, PROJECT_ID, BIGQUERY_TABLE, BIGQUERY_DATASET,  TABLE_ID
from utils.helpers import (
    _get_start_date_for_query,
    _read_namespaces_from_configmap,
    _merge_dataframes, 
     _build_vpa_workload_recommendations
)


# Setup logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def main():
    """
    Main function to process namespaces, merge data, and save the output.
    """
    try:
        # Ensure resources exist
        _ensure_resources_exist(PROJECT_ID, TABLE_ID)
        logger.info("BigQuery table exists. Proceeding with the code.")
    except RuntimeError as e:
        logger.error(f"Resource check failed: {e}")
        return 

    # Check if today's recommendations already exist
    if _check_latest_recommendation_date(PROJECT_ID, TABLE_ID):
        logger.info("Recommendations for today's date already exist. Exiting program.")
        return

    # Get the start and end date range for querying metrics
    start_datetime, end_datetime = _get_start_date_for_query()
    logger.info(f"Creating recommendations for date range: {start_datetime} - {end_datetime}")

    # Read namespaces from the configmap
    configmap_path = os.getenv("CONFIGMAP_PATH", "namespace.txt")
    namespaces = _read_namespaces_from_configmap(configmap_path)
    if not namespaces:
        logger.warning(f"No namespaces found in configmap {configmap_path}.")
        return

    # Process each namespace
    for namespace in namespaces:
        logger.info(f"Processing namespace: {namespace}")
        namespace_dataframes = []
        data = pd.DataFrame()

        # Fetch data for each metric
        for metric_name, metric_config in MQL_QUERY.items():
            data = _fetch_timeseries_data(data, namespace, metric_config, start_datetime, end_datetime)
            if not data.empty:
                namespace_dataframes.append(data)
            else:
                logger.warning(f"No data found for metric {metric_name} in namespace {namespace}")
        
        # Merge the dataframes for the namespace
        if namespace_dataframes:
            merged_df = _merge_dataframes(namespace_dataframes)

            vpa_recommendations_df = _build_vpa_workload_recommendations(
                merged_df, 
                start_datetime,
                end_datetime
            )
            _write_dataframe_to_bigquery( vpa_recommendations_df, PROJECT_ID, TABLE_ID)

        
        else:
            logger.warning(f"No data to merge for namespace '{namespace}'")
        
if __name__ == "__main__":
    main()

