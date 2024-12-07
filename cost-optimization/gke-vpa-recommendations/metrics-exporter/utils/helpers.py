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
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, date
from google.cloud import bigquery
from utils.config import MetricConfig, DEFAULT_WINDOW_DAYS

logger = logging.getLogger(__name__)

def _read_namespaces_from_configmap(configmap_path: str) -> list:
    """
    Read namespaces from the ConfigMap file.
    """
    try:
        with open(configmap_path, "r") as configmap_file:
            return [line.strip() for line in configmap_file if line.strip()]
    except FileNotFoundError:
        logger.error(f"ConfigMap not found: {configmap_path}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading ConfigMap: {e}")
        return []

def _get_start_date_for_query() -> tuple:
    """
    Determines the start and end dates for querying GKE metrics.

    Returns:
        tuple: A tuple containing the start date and end date as datetime objects.
    """
    try:
        start_datetime = datetime.combine(
            (datetime.now() - timedelta(days=DEFAULT_WINDOW_DAYS)).date(),
            datetime.min.time(),
        )
        end_datetime = datetime.combine(
            (datetime.now() - timedelta(days=1)).date(),
            datetime.min.time(),
        )
        return start_datetime, end_datetime
    except Exception as e:
        logger.error(f"Error calculating start and end dates: {e}")
        raise

def _process_time_series_data(all_time_series: list, metric_config: MetricConfig) -> pd.DataFrame:
    """
    Process the time series data and pivot metric_name into columns with metric_value.
    """

    if not all_time_series:
        logger.warning("No time series data to process.")
        return pd.DataFrame()

    try:
        # Flatten the time series data dynamically
        flat_data = pd.json_normalize(
            all_time_series,
            record_path="points",
            meta=[
                ["metric", "type"],
                ["resource", "labels", "project_id"],
                ["resource", "labels", "location"],
                ["resource", "labels", "cluster_name"],
                metric_config.controller_name_label_path,
                metric_config.controller_type_label_path,
                metric_config.container_name_label_path,
            ],
            errors="ignore"
        )
        if not flat_data.empty:

            # Pivot the data: Turn metric_name into columns with metric_value
            flat_data  = flat_data.pivot(
                index=[
                    "interval.startTime",
                    "interval.endTime",
                    "resource.labels.project_id",
                    "resource.labels.location",
                    "resource.labels.cluster_name",
                    f"{metric_config.controller_name_label}",
                    f"{metric_config.controller_type_label}",
                    f"{metric_config.container_label}"

                ],
                columns="metric.type",
                values=f"{metric_config.data_type}",
            ).reset_index()

            # Rename columns for readability
            flat_data.rename(
                columns={
                    "interval.startTime": "start_datetime",
                    "interval.endTime": "end_datetime",
                    "resource.labels.project_id": "project_id",
                    "resource.labels.location": "location",
                    "resource.labels.cluster_name": "cluster_name",
                    f"{metric_config.container_label}": "container_name",
                    f"{metric_config.data_type}": "metric_value",
                    f"{metric_config.controller_name_label}": "controller_name",
                    f"{metric_config.controller_type_label}": "controller_type",
                    f"{metric_config.metric}": f"{metric_config.output_metric_column_name}",
                },
                inplace=True,
                )

        return flat_data
    except Exception as e:
        logger.error(f"Error processing time series data: {e}")
        return pd.DataFrame()

def _merge_dataframes(dataframes: list) -> pd.DataFrame:
    """
    Merges a list of DataFrames that share common columns except for the last column.
    """
    # Start with the first DataFrame
    merged_df = dataframes[0]
    # Iteratively merge the DataFrames
    for i, df in enumerate(dataframes[1:], start=1):
        # Merge the current DataFrame with the merged DataFrame
        merged_df = pd.merge(
            merged_df,
            df,
            on=[
                "start_datetime", "end_datetime",
                "project_id", "location", "cluster_name",
                "controller_name", "controller_type", "container_name"
            ],
            how="outer"  # Use outer join to handle different row counts
        )

    return merged_df

def _build_vpa_workload_recommendations(df: pd.DataFrame, start_datetime: datetime, end_datetime: datetime)->pd.DataFrame:
    """
    Process a DataFrame with metrics data to convert units, calculate utilization, 
    and generate output recommendations for Deployment controller types.
    """
    
    # coerce all values that might be zero
    df["cpu_request_cores"] = pd.to_numeric(df["cpu_request_cores"], errors="coerce").fillna(0)
    df["cpu_limit_cores"] = pd.to_numeric(df["cpu_limit_cores"], errors="coerce").fillna(0)
    df["memory_used_bytes"] = pd.to_numeric(df["memory_used_bytes"], errors="coerce").fillna(0)
    df["memory_request_bytes"] = pd.to_numeric(df["memory_request_bytes"], errors="coerce").fillna(0)
    df["memory_limit_bytes"] = pd.to_numeric(df["memory_limit_bytes"], errors="coerce").fillna(0)
    df["memory_per_replica_recommended_request_bytes"]=pd.to_numeric(df["memory_per_replica_recommended_request_bytes"], errors="coerce").fillna(0)
    df["cpu_per_replica_recommended_request_cores"] = pd.to_numeric(df["cpu_per_replica_recommended_request_cores"], errors="coerce").fillna(0)
    
    df["run_date"] = start_datetime.strftime("%Y-%m-%d")
    df["start_datetime"] = start_datetime.isoformat()
    df["end_datetime"] = end_datetime.isoformat()

    # Convert CPU units from cores to mCores (1 core = 1000 mCores)
    df["cpu_mcore_usage"] = df["cpu_core_usage_time"] * 1000
    df["cpu_requested_mcores"] = df["cpu_request_cores"] * 1000
    df["cpu_limit_mcores"] = df["cpu_limit_cores"] * 1000

    # Convert memory units from bytes to MiB (1 MiB = 2^20 bytes)
    df["memory_mib_usage_max"] = (df["memory_used_bytes"] / (1024 ** 2))
    df["memory_requested_mib"] = df["memory_request_bytes"] / (1024 ** 2)
    df["memory_limit_mib"] = df["memory_limit_bytes"] / (1024 ** 2)

    # Calculate CPU utilization, handling division by zero
    df["cpu_request_utilization"] = np.where(
        df["cpu_requested_mcores"] == 0,
        1.0,  # 100% utilization if request is 0
        df["cpu_mcore_usage"] / df["cpu_requested_mcores"],
    )

    # Calculate memory utilization, handling division by zero
    df["memory_request_utilization"] = np.where(
        df["memory_request_bytes"] == 0,
        1.0,  # 100% utilization if request is 0
        df["memory_used_bytes"] / df["memory_request_bytes"],
    )

    # Apply VPA recommendations for Deployments
    df["cpu_requested_recommendation"] = np.where(
        df["controller_type"] == "Deployment",
        df["cpu_per_replica_recommended_request_cores"] * 1000,
        df["cpu_requested_mcores"],
    )

    df["cpu_limit_recommendation"] = np.where(
        df["controller_type"] == "Deployment",
        df["cpu_per_replica_recommended_request_cores"] * 1000 * 2.5,  # Example: 2.5x scaling for limits
        df["cpu_limit_mcores"],
    )
    df["memory_requested_recommendation"] = np.where(
        df["controller_type"] == "Deployment",
        df["memory_per_replica_recommended_request_bytes"] / (1024 ** 2),
        df["memory_requested_mib"],
    )
    df["memory_limit_recommendation"] = np.where(
        df["controller_type"] == "Deployment",
        df["memory_per_replica_recommended_request_bytes"] / (1024 ** 2),
        df["memory_limit_mib"],
    )

    # Calculate priority score (arbitrary calculation for demonstration)
    df["priority"] = (df["cpu_request_utilization"]*7.5) - df["memory_request_utilization"]

    # List of columns to drop
    columns_to_drop = [
        "cpu_core_usage_time",
        "cpu_request_cores",
        "cpu_limit_cores",
        "memory_used_bytes",
        "memory_request_bytes",
        "memory_limit_bytes",
        "memory_per_replica_recommended_request_bytes",
        "cpu_per_replica_recommended_request_cores"
    ]
    df["start_datetime"]= pd.to_datetime(df["start_datetime"])
    df["end_datetime"]= pd.to_datetime(df["end_datetime"])
    df["run_date"] = date.today()
    # Drop the columns from the DataFrame
    df = df.drop(columns=columns_to_drop)
    return df
