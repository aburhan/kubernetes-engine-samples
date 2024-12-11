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
import sys
import asyncio
import pandas as pd
from services.monitoring_serivce import _fetch_timeseries_data
from services.bigquery_service import (
    _ensure_resources_exist,
    _check_latest_recommendation_date,
    _write_dataframe_to_bigquery,
)
from utils.config import MQL_QUERY, PROJECT_ID, TABLE_ID, CONFIGMAP_PATH
from utils.helpers import (
    _get_start_date_for_query,
    _read_namespaces_from_configmap,
    _merge_dataframes,
    _build_vpa_workload_recommendations,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Default logging level
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)  # Log everything to stdout
    ]
)

logger = logging.getLogger(__name__)

async def process_namespace(namespace, start_datetime, end_datetime):
    """
    Process a single namespace: fetch metrics, merge dataframes, and write recommendations to BigQuery.
    """
    logger.info(f"Processing namespace: {namespace}")
    # Check if today's recommendations already exist
    if _check_latest_recommendation_date(PROJECT_ID, TABLE_ID, namespace):
        logger.info("Recommendations for today's date already exist. Exiting program.")
        return
    namespace_dataframes = []

    # Fetch data for each metric asynchronously
    fetch_tasks = [
        _fetch_timeseries_data(namespace, metric_config, start_datetime, end_datetime)
        for metric_name, metric_config in MQL_QUERY.items()
    ]

    # Wait for all fetch tasks to complete
    fetch_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

    # Process fetched data
    for idx, data in enumerate(fetch_results):
        if isinstance(data, Exception):
            logger.info(f"Error fetching data for metric {list(MQL_QUERY.keys())[idx]}: {data}")
        elif not data.empty:
            namespace_dataframes.append(data)
        else:
            logger.info(f"No data found for metric {list(MQL_QUERY.keys())[idx]} in namespace {namespace}")

    # Merge and build recommendations
    if namespace_dataframes:
        merged_df = _merge_dataframes(namespace_dataframes)

        vpa_recommendations_df = _build_vpa_workload_recommendations(
            merged_df,
            start_datetime,
            end_datetime,
        )
        _write_dataframe_to_bigquery(vpa_recommendations_df, PROJECT_ID, TABLE_ID)
    else:
        logger.info(f"No data to merge for namespace '{namespace}'")

async def main_async():
    """
    Main async function to process namespaces, merge data, and save the output.
    """
    try:
        # Ensure resources exist
        _ensure_resources_exist(PROJECT_ID, TABLE_ID)
        logger.info("BigQuery table exists. Proceeding with the code.")
    except RuntimeError as e:
        logger.error(f"Resource check failed: {e}")
        return

    # Get the start and end date range for querying metrics
    start_datetime, end_datetime = _get_start_date_for_query()
    logger.info(f"Creating recommendations for date range: {start_datetime} - {end_datetime}")

    # Read namespaces from the configmap
    #configmap_path = CONFIGMAP_PATH
    namespaces = ['default','gmp-system']
    logging.info("Namespaces found %s", namespaces)
    if not namespaces:
        logger.info(f"No namespaces found in configmap {configmap_path}.")
        return

    # Process each namespace asynchronously
    tasks = [process_namespace(namespace, start_datetime, end_datetime) for namespace in namespaces]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    logging.info("Project ID set to %s",os.getenv("PROJECT_ID"))
    logging.info("Files in director: \n")
    logging.info(os.listdir("."))
    asyncio.run(main_async())
