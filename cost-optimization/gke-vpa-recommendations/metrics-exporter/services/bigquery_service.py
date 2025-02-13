import pandas_gbq
import datetime
from google.cloud import bigquery
from google.api_core.exceptions import NotFound
import pandas as pd
import logging

from google.protobuf import descriptor_pb2
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types, writer
from utils.config import PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE
from .bigquery_record_pb2 import BigQueryRecord

# Global logger configuration
logger = logging.getLogger("bigquery_module")
logger.setLevel(logging.DEBUG)

def _check_latest_recommendation_date(project_id: str, table_id: str, namespace: str) -> bool:
    try:
        logger.info(f"Checking latest recommendation date for namespace: {namespace}")
        today_date = datetime.date.today()

        sql = f"""
            SELECT MAX(run_date) as latest_run_date
            FROM `{project_id}.{table_id}`
            WHERE namespace_name = "{namespace}"
        """
        logger.debug(f"Executing SQL: {sql}")
        fetch_latest_date = pandas_gbq.read_gbq(sql, project_id=project_id)

        if fetch_latest_date.empty or fetch_latest_date['latest_run_date'].iloc[0] is None:
            logger.info(f"No run_date found in table '{table_id}' for namespace '{namespace}'.")
            return True

        latest_run_date = fetch_latest_date['latest_run_date'].iloc[0]
        if today_date == latest_run_date:
            logger.info(f"Today's date ({today_date}) matches latest run_date ({latest_run_date}).")
            return True

        logger.info(f"Latest run_date is {latest_run_date}, which does not match today ({today_date}).")
        return False
    except Exception as e:
        logger.error(f"Failed to check latest recommendation date for {namespace}: {e}", exc_info=True)
        raise

def _ensure_resources_exist(project_id: str, bq_table_id: str):
    table_id = f"{project_id}.{bq_table_id}"
    try:
        logger.info(f"Checking if BigQuery table '{table_id}' exists...")
        bigquery_client = bigquery.Client(project=project_id)
        bigquery_client.get_table(table_id)
        logger.info(f"BigQuery table '{table_id}' exists.")
    except NotFound:
        logger.error(f"BigQuery table '{table_id}' does not exist.")
        raise RuntimeError(f"Table '{table_id}' does not exist.")
    except Exception as e:
        logger.error(f"Error checking BigQuery table: {e}", exc_info=True)
        raise

def serialize_row(row: pd.Series) -> bytes:
    try:
        logger.debug(f"Serializing row: {row.to_dict()}")
        record = BigQueryRecord()
        record.run_date = row["run_date"].strftime("%Y-%m-%d")
        record.start_datetime = row["start_datetime"].isoformat()
        record.end_datetime = row["end_datetime"].isoformat()
        record.project_id = row["project_id"]
        record.location = row["location"]
        record.cluster_name = row["cluster_name"]
        record.namespace_name = row["namespace_name"]
        record.controller_name = row["controller_name"]
        record.controller_type = row["controller_type"]
        record.container_name = row["container_name"]

        record.cpu_mcore_usage = row["cpu_mcore_usage"]
        record.cpu_requested_mcores = row["cpu_requested_mcores"]
        record.cpu_limit_mcores = row["cpu_limit_mcores"]
        record.memory_mib_usage_max = row["memory_mib_usage_max"]
        record.memory_requested_mib = row["memory_requested_mib"]
        record.memory_limit_mib = row["memory_limit_mib"]
        record.cpu_request_utilization = row["cpu_request_utilization"]
        record.memory_request_utilization = row["memory_request_utilization"]
        record.cpu_requested_recommendation = row["cpu_requested_recommendation"]
        record.cpu_limit_recommendation = row["cpu_limit_recommendation"]
        record.memory_requested_recommendation = row["memory_requested_recommendation"]
        record.memory_limit_recommendation = row["memory_limit_recommendation"]
        record.priority = row["priority"]

        serialized = record.SerializeToString()
        logger.debug("Row serialized successfully.")
        return serialized
    except Exception as e:
        logger.error(f"Failed to serialize row: {e}", exc_info=True)
        raise

def _write_dataframe_to_bigquery(df: pd.DataFrame):
    write_client = bigquery_storage_v1.BigQueryWriteClient()
    parent = write_client.table_path(PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE)
    logger.info(f"Writing DataFrame to BigQuery table: {BIGQUERY_TABLE}")

    write_stream = types.WriteStream(type_=types.WriteStream.Type.PENDING)
    write_stream = write_client.create_write_stream(parent=parent, write_stream=write_stream)
    stream_name = write_stream.name

    proto_schema = types.ProtoSchema()
    proto_descriptor = descriptor_pb2.DescriptorProto()
    BigQueryRecord.DESCRIPTOR.CopyToProto(proto_descriptor)
    proto_schema.proto_descriptor = proto_descriptor

    append_rows_stream = writer.AppendRowsStream(
        write_client, types.AppendRowsRequest(write_stream=stream_name, proto_rows=types.AppendRowsRequest.ProtoData(writer_schema=proto_schema))
    )

    try:
        logger.info(f"Serializing all rows...")
        serialized_rows = df.apply(serialize_row, axis=1).tolist()
        proto_rows = types.ProtoRows(serialized_rows=serialized_rows)
        request = types.AppendRowsRequest(proto_rows=types.AppendRowsRequest.ProtoData(rows=proto_rows))

        response_future = append_rows_stream.send(request)
        logger.debug(f"Response from server: {response_future.result()}")
    except Exception as e:
        logger.error(f"Error writing rows to BigQuery: {e}", exc_info=True)
        raise
    finally:
        # Shutdown background threads and close the streaming connection.
        append_rows_stream.close()

    try:
        # Finalize the write stream
        logger.info("Finalizing write stream...")
        write_client.finalize_write_stream(name=write_stream.name)

        # Commit the stream
        logger.info("Committing write stream...")
        batch_commit_write_streams_request = types.BatchCommitWriteStreamsRequest(
            parent=parent,
            write_streams=[write_stream.name]
        )
        write_client.batch_commit_write_streams(batch_commit_write_streams_request)
        logger.info(f"Writes to stream: '{write_stream.name}' have been committed.")
    except Exception as e:
        logger.error(f"Error finalizing or committing write stream: {e}", exc_info=True)
        raise

    logger.info("DataFrame successfully written to BigQuery.")
