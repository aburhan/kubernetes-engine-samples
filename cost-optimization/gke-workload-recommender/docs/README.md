# Workload Recommender Module

This repository contains modules to recommend Horizontal Pod Autoscaler
(HPA) or static Vertical Pod Autoscaler (VPA) configurations for Kubernetes
workloads in Google Kubernetes Engine (GKE) based on cost efficiency and
reliability.

## Overview

The solution evaluates GKE workloads using historical metric data. It
simulates both HPA and VPA recommendations to determine the best fit for
a given workload. HPA recommendations are prioritized, but if HPA is not
suitable, the fallback is a static VPA recommendation.

Users can specify the analysis period based on known workload patterns to
maximize accuracy. For example:

-   **Short-term patterns:** Select 3 days if the workload operates
    cyclically over that period.
-   **Unknown patterns:** Use a default period of 14 days.

> **Note:** This solution is currently tested only for Kubernetes
> Deployments.

## Key Features

-   Fetch and aggregate workload CPU and memory metrics from Cloud
    Monitoring.
-   Calculate workload startup time by considering pod initialization and
    cluster autoscaler delays.
-   Simulate resource scaling using DMR (Dynamic Minimum Replicas) and DCR
    (Dynamic CPU Requests) algorithms.
-   Generate resource recommendations for both HPA and VPA.

## Modules and Public Functions

### `get_workload_startup_time`

Calculates the total workload startup time, including processing time and
cluster autoscaler delays.

**Parameters:**

-   `_config`: Configuration object with run parameters.
-   `workload`: A `WorkloadDetails` object.

**Returns:** A `StartupTime` object representing startup time in seconds.

---

### `get_workload_agg_timeseries`

Fetches CPU and memory usage metrics for a GKE workload and returns them
as a grouped DataFrame.

**Parameters:**

-   `_config`: Configuration object.
-   `workload`: A `WorkloadDetails` object.
-   `start_datetime`: Start of the analysis period.
-   `end_datetime`: End of the analysis period.

**Returns:** A pandas DataFrame containing timeseries metrics.

---

### `get_simulation_plans`

Generates HPA or VPA recommendations using DMR and DCR algorithms.

**Parameters:**

-   `workload_df`: Timeseries DataFrame.
-   `workload_details`: Details of the GKE workload.

**Returns:** A list of `HPAWorkloadPlan` objects representing resource scaling
recommendations.

---

### `run_simulation_plan`

Runs the simulation based on the provided scaling plans.

**Parameters:**

-   `workload_df`: Timeseries DataFrame.
-   `workload_details`: Details of the workload.
-   `_plans`: List of `HPAWorkloadPlan` objects.

**Returns:** A tuple containing an analysis DataFrame and a
`RecommendationsSummary` object.

---

## Data Classes

### `WorkloadDetails`

Holds resource labels for querying Kubernetes workload assets.

**Attributes:**

-   `project_id`: GCP Project ID.
-   `cluster_name`: Kubernetes cluster name.
-   `location`: Cluster location (region or zone).
-   `namespace`: Namespace of the workload.
-   `controller_name`: Controller managing the workload.

---

### `HPAWorkloadPlan`

Represents simulation results and recommendations.

**Attributes:**

-   `method`: Recommendation algorithm (DMR or DCR).
-   `recommended_cpu_request`: Recommended CPU request.
-   `recommended_mem_request_and_limits_mi`: Recommended memory in MiB.
-   `recommended_min_replicas`: Minimum replicas.
-   `recommended_max_replicas`: Maximum replicas.
-   `recommended_target_cpu`: Target CPU utilization.

---

### `WorkloadRecommendations`

Summarizes simulation results, including cost savings.

**Attributes:**

-   `analysis_period_start`: Start of the analysis period.
-   `analysis_period_end`: End of the analysis period.
-   `recommendation`: Recommended configuration.
-   `min_replicas`: Minimum replicas observed.
-   `max_replicas`: Maximum replicas observed.
-   `avg_saving_in_cpus_1d_mean`: Average CPU savings per day.

---

## Required Roles

Ensure you have the following Google Cloud roles:

-   `roles/monitoring.viewer`

Authenticate using the Google Cloud SDK:

```bash
gcloud auth application-default login
