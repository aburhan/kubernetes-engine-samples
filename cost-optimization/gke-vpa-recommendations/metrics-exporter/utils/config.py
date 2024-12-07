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

USER_AGENT = "cloud-solutions/gke-wa-vpa-recommender-v1"
CONFIGMAP_PATH="/config/namespace.txt"
SECONDS_IN_A_DAY=86400

PROJECT_ID = os.getenv("PROJECT_ID", None)

BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "gke_metrics_dataset")
BIGQUERY_TABLE = os.getenv("BIGQUERY_TABLE", "gke_vpa_recommendations")
TABLE_ID = f'{BIGQUERY_DATASET}.{BIGQUERY_TABLE}'


DEFAULT_WINDOW_DAYS=int(os.getenv("DEFAULT_WINDOW_DAYS","14"))
MEMORY_RECOMMENDATION_BUFFER = float(os.getenv("MEMORY_RECOMMENDATION_BUFFER",1.10)) #10% on buffer

class MetricConfig:
    """
    A configuration class for metric data.

    :param metric: The name of the metric.
    :param window: The window of time for the metric.
    :param seconds_between_points: The interval between metric points.
    :param data_type: The type of the metric data.
    :param per_series_aligner: The aligner for the metric data series.
    :param cross_series_reducer: The reducer for the metric data series.
    :param columns: The columns to be included in the metric data.
    """

    def __init__(
            self,
            metric: str,
            output_metric_column_name:str,
            resource_type: str,
            data_type: str,
            per_series_aligner: str,
            cross_series_reducer: str,
            container_label: str,
            controller_name_label:[str, str, str],
            controller_type_label :[str, str, str],
            columns: [str]):
        self.metric = metric
        self.output_metric_column_name = output_metric_column_name
        self.resource_type = resource_type
        self.per_series_aligner = per_series_aligner
        self.cross_series_reducer = cross_series_reducer
        self.data_type = data_type
        self.columns = columns
        self.container_label = container_label
        self.controller_name_label = controller_name_label
        self.controller_type_label = controller_type_label 
    @property
    def container_name_label_path(self):
        """ Dynamically determines the container name path based on resource_type. """
        return self.container_label.split(".")
    @property
    def controller_name_label_path(self):
        """ Dynamically determines the container name path based on resource_type. """
        return self.controller_name_label .split(".")
    @property
    def controller_type_label_path(self):
        """ Dynamically determines the container name path based on resource_type. """
        return self.controller_type_label .split(".")

gke_group_by_fields = [
    'resource.label."location"',
    'resource.label."project_id"',
    'resource.label."cluster_name"',
    'resource.label."controller_name"',
    'resource.label."namespace_name"',
    'resource.label."container_name"',
    'metadata.system_labels."top_level_controller_name"',
    'metadata.system_labels."top_level_controller_type"']
scale_group_by_fields = [
    'resource.label."location"',
    'resource.label."project_id"',
    'resource.label."cluster_name"',
    'resource.label."namespace_name"',
    'metric.label."container_name"',
    'resource.label."controller_kind"',
    'resource.label."controller_name"']

NS_QUERY = MetricConfig(
    metric="kubernetes.io/container/cpu/core_usage_time",
    output_metric_column_name="replicas",
    resource_type="k8s_container",
    per_series_aligner="ALIGN_RATE",
    cross_series_reducer="REDUCE_COUNT",
    data_type="doubleValue",
    container_label="resource.labels.container_name",
    controller_name_label="metadata.systemLabels.top_level_controller_name",
    controller_type_label="metadata.systemLabels.top_level_controller_type",
    columns=[
    'resource.label."location"',
    'resource.label."project_id"',
    'resource.label."cluster_name"',
    'resource.label."controller_name"',
    'resource.label."namespace_name"',
    'metadata.system_labels."top_level_controller_name"',
    'metadata.system_labels."top_level_controller_type"']
)

MQL_QUERY = {
    "cpu_usage": MetricConfig(
        metric="kubernetes.io/container/cpu/core_usage_time",
        output_metric_column_name="cpu_core_usage_time",
        resource_type="k8s_container",
        per_series_aligner="ALIGN_RATE",
        cross_series_reducer="REDUCE_PERCENTILE_95",
        data_type="value.doubleValue",
        container_label="resource.labels.container_name",
        controller_name_label="metadata.systemLabels.top_level_controller_name",
        controller_type_label="metadata.systemLabels.top_level_controller_type",
        columns=gke_group_by_fields
    ),
    "cpu_requested_cores": MetricConfig(
        metric="kubernetes.io/container/cpu/request_cores",
        output_metric_column_name="cpu_request_cores",
        resource_type="k8s_container",
        per_series_aligner="ALIGN_MEAN",
        cross_series_reducer="REDUCE_MEAN",
        data_type="value.doubleValue",
        container_label="resource.labels.container_name",
        controller_name_label="metadata.systemLabels.top_level_controller_name",
        controller_type_label="metadata.systemLabels.top_level_controller_type",
        columns=gke_group_by_fields
    ),
    "cpu_limit_cores": MetricConfig(
        metric="kubernetes.io/container/cpu/limit_cores",
        output_metric_column_name="cpu_limit_cores",
        resource_type="k8s_container",
        per_series_aligner="ALIGN_MEAN",
        cross_series_reducer="REDUCE_MEAN",
        data_type="value.doubleValue",
        container_label="resource.labels.container_name",
        controller_name_label="metadata.systemLabels.top_level_controller_name",
        controller_type_label="metadata.systemLabels.top_level_controller_type",
        columns=gke_group_by_fields
    ),
    "memory_usage": MetricConfig(
        metric="kubernetes.io/container/memory/used_bytes",
        output_metric_column_name="memory_used_bytes",
        resource_type="k8s_container",
        per_series_aligner="ALIGN_MAX",
        cross_series_reducer="REDUCE_MAX",
        data_type="value.int64Value",
        container_label="resource.labels.container_name",
        controller_name_label="metadata.systemLabels.top_level_controller_name",
        controller_type_label="metadata.systemLabels.top_level_controller_type",
        columns=gke_group_by_fields
    ),
    "memory_requested_bytes": MetricConfig(
        metric="kubernetes.io/container/memory/request_bytes",
        output_metric_column_name="memory_request_bytes",
        resource_type="k8s_container",
        per_series_aligner="ALIGN_MEAN",
        cross_series_reducer="REDUCE_MEAN",
        data_type="value.doubleValue",
        container_label="resource.labels.container_name",
        controller_name_label="metadata.systemLabels.top_level_controller_name",
        controller_type_label="metadata.systemLabels.top_level_controller_type",
        columns=gke_group_by_fields
    ),
    "memory_limit_bytes": MetricConfig(
        metric="kubernetes.io/container/memory/limit_bytes",
        output_metric_column_name="memory_limit_bytes",
        resource_type="k8s_container",
        per_series_aligner="ALIGN_MEAN",
        cross_series_reducer="REDUCE_MEAN",
        data_type="value.doubleValue",
        container_label="resource.labels.container_name",
        controller_name_label="metadata.systemLabels.top_level_controller_name",
        controller_type_label="metadata.systemLabels.top_level_controller_type",
        columns=gke_group_by_fields
    ),
    "vpa_memory_recommendation": MetricConfig(
        metric="kubernetes.io/autoscaler/container/memory/per_replica_recommended_request_bytes",
        output_metric_column_name="memory_per_replica_recommended_request_bytes",
        resource_type="k8s_scale",
        per_series_aligner="ALIGN_MAX",
        cross_series_reducer="REDUCE_MAX",
        data_type="value.int64Value",
        container_label="metric.labels.container_name",
        controller_name_label="resource.labels.controller_name",
        controller_type_label="resource.labels.controller_kind",
        columns=scale_group_by_fields
    ),
    "vpa_cpu_recommendation": MetricConfig(
        metric="kubernetes.io/autoscaler/container/cpu/per_replica_recommended_request_cores",
        output_metric_column_name="cpu_per_replica_recommended_request_cores",
        resource_type="k8s_scale",
        per_series_aligner="ALIGN_MEAN",
        cross_series_reducer="REDUCE_PERCENTILE_95",
        data_type="value.doubleValue",
        container_label="metric.labels.container_name",
        controller_name_label="resource.labels.controller_name",
        controller_type_label="resource.labels.controller_kind",
        columns=scale_group_by_fields
    )
}
