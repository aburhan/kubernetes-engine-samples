import os
import logging
import sys
import asyncio
import pandas as pd
import psutil
import time
from services.monitoring_serivce import _fetch_timeseries_data
from services.bigquery_service import (
    _ensure_resources_exist,
    _write_dataframe_to_bigquery,
)
from utils.config import MQL_QUERY, CONFIGMAP_PATH
from utils.helpers import (
    _get_start_date_for_query,
    _read_namespaces_from_configmap,
    _merge_dataframes,
    _build_vpa_workload_recommendations,
)
from utils.performance import profile_execution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(funcName)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log everything to stdout
        logging.FileHandler("metrics_exporter.log", mode="a"),  # Rotating file handler
    ]
)
logger = logging.getLogger(__name__)

# Global variables for success/failure tracking
successful_namespaces = []
failed_namespaces = []

# Configurable settings
MAX_CONCURRENT_NAMESPACES = int(os.getenv("MAX_CONCURRENT_NAMESPACES", 100))  # Default batch size
METRIC_FETCH_TIMEOUT = int(os.getenv("METRIC_FETCH_TIMEOUT", 30))  # Default fetch timeout in seconds
BIGQUERY_BATCH_SIZE = int(os.getenv("BIGQUERY_BATCH_SIZE", 500))  # Default BigQuery batch size


def log_resource_usage():
    """
    Logs CPU and memory usage of the current process.
    """
    process = psutil.Process(os.getpid())
    cpu_usage = process.cpu_percent(interval=1)
    memory_info = process.memory_info()
    memory_usage_mb = memory_info.rss / (1024 * 1024)
    logger.info(f"Resource Usage: CPU = {cpu_usage:.2f}%, Memory = {memory_usage_mb:.2f} MB")

async def fetch_metric_with_retries(namespace, metric_name, metric_config, start_datetime, end_datetime, retries=3, delay=5):
    """
    Fetch metrics with retry logic using exponential backoff.
    """
    for attempt in range(1, retries + 1):
        try:
            result = await asyncio.wait_for(
                _fetch_timeseries_data(namespace, metric_config, start_datetime, end_datetime),
                timeout=METRIC_FETCH_TIMEOUT,
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"[Namespace: {namespace}, Metric: {metric_name}] Timeout on attempt {attempt}")
        except Exception as e:
            logger.error(f"[Namespace: {namespace}, Metric: {metric_name}] Error on attempt {attempt}: {e}")
        if attempt < retries:
            await asyncio.sleep(delay * attempt)  # Exponential backoff
    logger.error(f"[Namespace: {namespace}, Metric: {metric_name}] Failed after {retries} retries")
    return None

async def process_namespace(namespace, start_datetime, end_datetime):
    """
    Process a single namespace: fetch metrics concurrently, merge dataframes, and write recommendations to BigQuery.
    Logs resource usage and handles failures gracefully.
    """
    try:
        logger.info(f"[Namespace: {namespace}] Starting processing")
        log_resource_usage()

        # Fetch timeseries data concurrently
        fetch_tasks = [
            fetch_metric_with_retries(namespace, metric_name, metric_config,start_datetime, end_datetime)
            for metric_name, metric_config in MQL_QUERY.items()
        ]

        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        print("###########################################################\n")
        print(results)
        print("###########################################################\n")
        namespace_dataframes = [
            res for res in results if isinstance(res, pd.DataFrame) and not res.empty
        ]

        if not namespace_dataframes:
            logger.warning(f"[Namespace: {namespace}] No valid dataframes retrieved. Marking as failed.")
            failed_namespaces.append(namespace)
            return

        logger.info(f"[Namespace: {namespace}] Merging dataframes")
        merged_df = _merge_dataframes(namespace_dataframes)
        print("###########################################################\n")
        print(merged_df)
        print("###########################################################\n")
        logger.info(f"[Namespace: {namespace}] Building VPA recommendations")
        vpa_recommendations_df = _build_vpa_workload_recommendations(merged_df, start_datetime, end_datetime)

        logger.info(f"[Namespace: {namespace}] Writing recommendations to BigQuery")
        await write_to_bigquery_with_retries(vpa_recommendations_df, namespace)

        successful_namespaces.append(namespace)
        logger.info(f"[Namespace: {namespace}] Successfully processed")
    except Exception as e:
        logger.error(f"[Namespace: {namespace}] Unexpected error: {e}", exc_info=True)
        failed_namespaces.append(namespace)
    finally:
        log_resource_usage()
        logger.info(f"[Namespace: {namespace}] Finished processing")


async def write_to_bigquery_with_retries(df, namespace, retries=3, delay=5):
    """
    Writes a dataframe to BigQuery with retries.
    """
    for attempt in range(1, retries + 1):
        try:
            _write_dataframe_to_bigquery(df)
            return
        except Exception as e:
            logger.error(f"[Namespace: {namespace}] BigQuery write error on attempt {attempt}: {e}")
        if attempt < retries:
            await asyncio.sleep(delay * attempt)  # Exponential backoff
    logger.error(f"[Namespace: {namespace}] BigQuery write failed after {retries} retries")
    failed_namespaces.append(namespace)


@profile_execution
async def main():
    """
    Main async function to process namespaces, merge data, and save the output.
    
    try:
        _ensure_resources_exist(os.getenv("PROJECT_ID"), os.getenv("TABLE_ID"))
        logger.info("BigQuery table exists. Proceeding with namespace processing.")
    except RuntimeError as e:
        logger.error(f"Resource check failed: {e}")
        return
    """
    # Get start and end dates for metrics
    start_datetime, end_datetime = _get_start_date_for_query()
    logger.info(f"Processing metrics for date range: {start_datetime} to {end_datetime}")

    # Fetch namespaces dynamically
    #namespaces = _read_namespaces_from_configmap(CONFIGMAP_PATH)
    namespaces = ['default'] * 1000
    logger.info(f"Found {len(namespaces)} namespaces to process")

    if not namespaces:
        logger.warning("No namespaces found to process. Exiting.")
        return

    # Process namespaces in batches
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_NAMESPACES)
    async def process_with_semaphore(ns):
        async with semaphore:
            await process_namespace(ns, start_datetime, end_datetime)

    tasks = [process_with_semaphore(ns) for ns in namespaces]
    await asyncio.gather(*tasks)

    # Summary logs
    logger.info(f"Processing completed: {len(successful_namespaces)} successful, {len(failed_namespaces)} failed.")
    if failed_namespaces:
        logger.warning(f"Failed namespaces: {failed_namespaces}")
    log_resource_usage()


if __name__ == "__main__":
    start_time = time.monotonic()
    asyncio.run(main())
    elapsed_time = time.monotonic() - start_time
    logger.info(f"Finished processing in {elapsed_time:.2f} seconds")
