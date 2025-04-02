from google.cloud import bigquery
from google.api_core.client_info import ClientInfo
import pandas as pd
import logging
from config import PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE, USER_AGENT

def write_to_bigquery(data, lookup):
    """
    Writes data to BigQuery given project, dataset, and table names.
    """
    try:
        client = bigquery.Client(
            project=PROJECT_ID,
            client_info=ClientInfo(user_agent=USER_AGENT))

        df = pd.json_normalize(
        data['timeSeries'],
        record_path='points',
        meta = [
        ['valueType'],
        ['metric','type'],
        ['resource','labels','location'], 
        ['resource','labels','project_id'],
        ['resource','labels','namespace_name'], 
        ['resource','labels','cluster_name'],
        ['resource','labels','container_name'],
        ['metadata','systemLabels','top_level_controller_type'],
        ['metadata','systemLabels','top_level_controller_name']
        ])
        # Apply transformation based on valueType

        df.columns = [
            'startTime', 'endTime', 'value', 'valueType',
            'metric_type', 'location', 'project_id',
            'namespace_name', 'cluster_name',
            'container_name',
            'controller_type',
            'controller_name'
        ]
        
        df["replicas"] = df.apply(
            lambda row: lookup.get(
                f"{row['controller_name']}|{row['controller_type']}"),
            axis=1
        )
        # Apply transformation
        df["value"] = df.apply(
            lambda row: row["value"] * 1000 if row["valueType"] == "DOUBLE"
            else row["value"] / (1024 ** 2),  # Convert bytes to MiB
            axis=1
        )
        if not data:
            logging.info("No data to write.")
            return

        table_ref = f"{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}"

        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND",
            autodetect=True,
        )

        load_job = client.load_table_from_dataframe(
            df, table_ref, job_config=job_config
            )
        load_job.result()

        print(f"Wrote {len(df)} rows to {table_ref}")
        logging.info(f"Successfully wrote {len(df)} rows to {table_ref}")
        return f"Success: {len(df)} rows written"
    except Exception as e:
        logging.error(f"BigQuery write failed: {e}", exc_info=True)
        raise RuntimeError(f"BigQuery error: {str(e)}")
