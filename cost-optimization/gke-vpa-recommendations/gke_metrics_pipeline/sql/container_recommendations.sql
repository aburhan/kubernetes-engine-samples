/*
# Copyright 2025 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
*/
WITH gke_metrics AS (
  SELECT * FROM
  ( 
    SELECT
    LAST_VALUE(
      DATE(PARSE_DATETIME('%Y-%m-%dT%H:%M:%SZ',startTime))
    )
    OVER (PARTITION BY project_id, location, cluster_name, controller_name, controller_type, namespace_name, container_name, metric ORDER BY startTime) AS run_date,
    metric,
    project_id,
    location,
    cluster_name,
    controller_name,
    controller_type,
    namespace_name,
    container_name,
    CAST(replicas AS INT64) AS replicas,
    CAST(value AS FLOAT64) AS value,
  FROM `['YOUR TABLE HERE']`)
  PIVOT(AVG(value) 
  FOR metric IN 
    (
    'kubernetes.io/container/cpu/core_usage_time' AS cpu_mcores_usage,
    'kubernetes.io/container/memory/used_bytes' AS memory_mib_usage_max,
    'kubernetes.io/container/cpu/request_cores' AS cpu_requested_mcores,
    'kubernetes.io/container/cpu/limit_cores' AS cpu_limit_mcores,
    'kubernetes.io/container/memory/request_bytes' AS memory_requested_mib,
    'kubernetes.io/container/memory/limit_bytes' AS memory_limit_mib
    )
  )
),recommendations AS (
  SELECT *,
  ROUND(COALESCE(SAFE_DIVIDE(cpu_mcores_usage, cpu_requested_mcores), 100), 2) AS cpu_request_utilization,
  ROUND(COALESCE(SAFE_DIVIDE(memory_mib_usage_max, memory_requested_mib), 100), 2) AS mem_request_utilization,
  /*
  Recommended practices for setting Kubernetes container resources:
  
  Aim for equal memory requests and limits, while allowing for a larger or unbounded CPU limit, especially for burstable workloads.
  
  Calculations based on 14+ day usage data:
  
  * **Memory Request & Limit:** Use the same value, calculated as `(maximum memory usage) * 1.30` (adding a 30% buffer).
  * **CPU Request:** Calculated as `(99th percentile CPU usage) * 1.30` (adding a 30% buffer).
  * **CPU Limit:** Should be set higher than the request. For burstable workloads, a guideline is `(99th percentile CPU usage) * 2.00` (adding a 100% buffer).
  
  For more details, see:
  https://cloud.google.com/architecture/best-practices-for-running-cost-effective-kubernetes-applications-on-gke#set_appropriate_resource_requests_and_limits
  */
  CEIL( cpu_mcores_usage * 1.30) AS cpu_requested_recommendation, 
  CEIL( cpu_mcores_usage * 2.00) AS cpu_limit_recommendation,
  CEIL( memory_mib_usage_max * 1.30) AS memory_requested_recommendation, 
  CEIL( memory_mib_usage_max * 1.30) AS memory_limit_recommendation,
  FROM gke_metrics
)
SELECT * EXCEPT(replicas),
  ((cpu_requested_mcores-cpu_requested_recommendation) + ((memory_requested_mib - memory_requested_recommendation)/13.4)) * replicas AS priority
FROM recommendations

