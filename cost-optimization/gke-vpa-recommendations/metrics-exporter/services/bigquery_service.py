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
import pandas_gbq
import datetime
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def _check_latest_recommendation_date(project_id: str, table_id: str) -> bool:
    """
    Checks if today's date matches the latest run_date in the BigQuery table.
    If there is no data in the table, or the latest run_date is not today's date,
    returns True (as if data does not exist).

    Args:
        project_id (str): The GCP project ID.
        table_id (str): The BigQuery table ID in the format "dataset.table".

    Returns:
        bool: True if today's date matches the latest run_date or if no date exists, False otherwise.
    """
    try:
        # Get today's date
        today_date = datetime.date.today()

        # Query to fetch the latest run_date from the BigQuery table
        sql = f"""
            SELECT MAX(run_date) as latest_run_date
            FROM `{project_id}.{table_id}`
        """
        fetch_latest_date = pandas_gbq.read_gbq(sql, project_id=project_id)
        
        # Check if the table has any data
        if fetch_latest_date.empty or fetch_latest_date['latest_run_date'].iloc[0] is None:
            logger.info("No latest run_date found in the table. Proceeding as if data does not exist.")
            return True  # No data exists in the table

        # Convert the fetched run_date to a timestamp
        latest_run_date = fetch_latest_date['latest_run_date'].iloc[0]
        
        # Compare the latest run_date with today's date
        if today_date == latest_run_date:
            logger.info(f"Today's date ({today_date}) matches the latest run_date in the table.")
            return True  # Today's date matches the latest run_date

        logger.info(f"Latest run_date ({latest_run_date}) does not match today's date ({today_date}).")
        return False

    except Exception as e:
        logger.error(f"Error checking latest recommendation date: {e}")
        raise RuntimeError(f"Failed to check latest recommendation date: {e}")



def _ensure_resources_exist(project_id: str, bq_table_id: str):
    """
    Ensures that the BigQuery table exists.

    Args:
        project_id (str): The GCP project ID.
        bq_table_id (str): The BigQuery table ID in the format "dataset.table".

    Raises:
        RuntimeError: If the BigQuery table does not exist.
    """
    bigquery_client = bigquery.Client(project=project_id)
    table_id = f"{project_id}.{bq_table_id}"
    try:
        bigquery_client.get_table(table_id)
        logger.info(f"BigQuery table '{table_id}' exists.")
    except NotFound:
        raise RuntimeError(f"The BigQuery table '{table_id}' does not exist.")
    except Exception as e:
        raise RuntimeError(f"Unexpected error while checking BigQuery table: {e}")


def _write_dataframe_to_bigquery(df: pd.DataFrame, project_id: str, table_id: str):
    """
    Writes a DataFrame to a BigQuery table using pandas_gbq.

    Args:
        df (pd.DataFrame): The DataFrame to write to BigQuery.
        project_id (str): The GCP project ID.
        table_id (str): The BigQuery table ID in the format "dataset.table".

    Raises:
        RuntimeError: If the write operation fails.
    """

    pandas_gbq.to_gbq(df,
        destination_table=table_id,
        project_id=project_id,
        if_exists='append'
    )
    logger.info(f"Successfully written DataFrame to BigQuery table: {table_id}")