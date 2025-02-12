# Changelog

## [0.0.27] -  2025-01-25

-   Added clash count threshold for CPU to allow for a configurable number to be
    accepted.

## [0.0.26] -  2025-01-23

-   Updated simulation code to return an explanation of why no recommendations
    exist.

## [0.0.25] -  2025-01-12

-   Replaced sum_containers_cpu_usage with avg_container_cpu_usage
-   Replaced sum_containers_mem_usage_mi with max_containers_mem_usage_mi

## [0.0.24] -  2025-01-12

-   Replaced simulation loop, removed itertuple with for loop 20x improvement on
    14 days of data.
-   Consolidated all helper logic necessary for simulate_hpa_behaviour to
    improve readablity.
-   Updated the DMR min_replica calculation if max replicas > 50 (value
    configured in config.py), the min replicas range is set to the
    20% percentile (value configured in config.py) of the max replicas.
    Ex. max_replica = 100, min replicas range loops starts at 20.
-   Removed DCR_MEAN algorithm.

## [0.0.23] -  2024-12-20

-   Read Timeseries: Switched from using monitor_v3 client to REST API
    and added async functionality. Execution improvement: 30 -> 14 seconds
-   Read Timeseries time interval changed from points every 30 seconds to every
    60 seconds.
-   HPA Simulation Run: Added multiprocessing to speed up simulation process
    Execution improvement: 165 -> 52 seconds
-   Removed site_id and vertical_id from dataframe

## [0.0.22] -  2024-11-27

-   Simulation plan: by pre-compute computations that are common across
    all plans and by filtered workload_df before computing recommended
    hpa target we got 147% performance improvements (from 25 seconds
    to 0.1737 - this includes 0.0.21 vectorization improvement)
-   Simulation plan: skip plan with slop bigger than hpa scale limit 2.3
-   Simulation plan: skip plan with HPA target CPU < 40% and > 87%
-   Simulation plan: improved logging
-   Fix: build.sh to find the version

## [0.0.21] -  2024-11-18

-   Fix: Added logic to exit simulation loop at first clash
    Execution time improvement: 1225 seconds -> 667 seconds
-   Optimized _calculate_max_usage_slope_up_ratio to improve calculations
    on the DataFrame finding max usage slope
-   Removed unused columns from read_workload_timeseries.py
-   Set dataframe data types to optimizate storage
    hpa_simulation_plan execution time improvement: 25 seconds -> 2 seconds
    hpa_simulation_run execution time improvement: 667 seconds -> 632
-   Refactor hpa simulation unit test to improve readability
-   Refactor hpa simulation run to improve execution time 632 -> 474 seconds

## [0.0.20] -  2024-11-14

-   b/377348358 Add timezone parameter to the metric cli.

## [0.0.19] -  2024-11-12

-   b/378766124 Add performance logging.

## [0.0.18] -  2024-11-08

-   b/377348358 Convert timezone back into timezone used in the client.

## [0.0.17] -  2024-11-06

-   b/376436697 Update to pass a HPAConfig object in the parameters.

## [0.0.16] -  2024-11-05

-   Update DMR rounding (3) for CPU to DMR functions.
-   Fix parameter for _compute_desired_replicas to data type HPAWorkloadPlan
-   b/377497381 __compute_desired_replicas function add MCPU rounding to DMR.

## [0.0.15] -  2024-11-04

-   Fix conflict with colab default libraries.
-   Log execution time of the main functions.
-   Saving files with well defined names to simplify loading.
-   b/377007645 Min replicas now is based on 10th percentile, instead of actualmin.

## [0.0.14] -  2024-11-02

-   Adding metrics_exporter command line available after installing the package.

## [0.0.13] -  2024-11-01

-   Updated the hpa_scale_up_behaviour_to_x_times in HPAWorkloadRecommendation.
-   b/376884237

## [0.0.12] - 2024-11-01

-   Rec HPA target CPU exceeded 100%, fixed bug add added a validation check.
-   b/376866076

## [0.0.11] - 2024-10-30

### Changed

-   Add additional fields in the `analysis_df` DataFrame
-   Updated `output_results` to concatenate using `pd.concat`.
-   Removed unnecessary empty DataFrame check.
