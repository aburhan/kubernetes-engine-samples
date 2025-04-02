import json
import pandas as pd
import logging
from pubsub import publish_to_pubsub
from config import METRIC_QUERIES
from config import LOGGING_CONFIG

# Configure logging
logger = logging.basicConfig(**LOGGING_CONFIG)

def process_monitoring_data(time_series_data):
    """
    Processes monitoring data and groups by key fields to create Pub/Sub messages.
    """
    df = pd.json_normalize(
        time_series_data,
        record_path="points",
        meta=[
            ["resource", "labels", "project_id"],
            ["resource", "labels", "location"],
            ["resource", "labels", "cluster_name"],
            ["resource", "labels", "namespace_name"],
            ["metadata", "systemLabels", "top_level_controller_name"],
            ["metadata", "systemLabels", "top_level_controller_type"],
        ],
    )

    df.rename(
        columns={
            "metadata.systemLabels.top_level_controller_name": "controller_name",
            "metadata.systemLabels.top_level_controller_type": "controller_type",
            "value.int64Value": "replicas",
        },
        inplace=True,
    )

    grouped_df = df.groupby(
        [
            "resource.labels.project_id",
            "resource.labels.namespace_name",
            "resource.labels.cluster_name",
            "resource.labels.location",
        ]
    )

    for (project_id, namespace_name, cluster_name, location), group in grouped_df:
        controller_dict = {
            f"{k[0]}|{k[1]}": v
            for k, v in (
                group[["controller_name", "controller_type", "replicas"]]
                .dropna()
                .set_index(["controller_name", "controller_type"])["replicas"]
                .to_dict()
                .items()
            )
        }

        message = {
            "project": project_id,
            "cluster": cluster_name,
            "namespace": namespace_name,
            "location": location,
            "controller_dict": controller_dict,
        }

        for query in METRIC_QUERIES:
            message["cloud_monitoring_query"] = query
            publish_to_pubsub(message)
