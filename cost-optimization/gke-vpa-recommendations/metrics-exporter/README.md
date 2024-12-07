## Instructions

1. Build image

  ```sh
    export PROJECT_ID=gke-rightsize
    export REGION=us-central1
    export ZONE=us-central1-f
    export IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/main/workload-vpa-recs-image:latest
    gcloud auth configure-docker $REGION-docker.pkg.dev
    gcloud builds submit metrics-exporter --region=$REGION --tag $IMAGE
  ```

2. Create table

  ```json
  [
  {
      "name": "run_date",
      "type": "DATE",
      "mode": "NULLABLE"
    },
    {
      "name": "start_datetime",
      "type": "DATETIME",
      "mode": "NULLABLE"
    },
    {
      "name": "end_datetime",
      "type": "DATETIME",
      "mode": "NULLABLE"
    },
    {
      "name": "project_id",
      "type": "STRING",
      "mode": "NULLABLE"
    },
    {
      "name": "location",
      "type": "STRING",
      "mode": "NULLABLE"
    },
    {
      "name": "cluster_name",
      "type": "STRING",
      "mode": "NULLABLE"
    },
    {
      "name": "controller_name",
      "type": "STRING",
      "mode": "NULLABLE"
    },
    {
      "name": "controller_type",
      "type": "STRING",
      "mode": "NULLABLE"
    },
    {
      "name": "container_name",
      "type": "STRING",
      "mode": "NULLABLE"
    },
    {
      "name": "cpu_mcore_usage",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "cpu_requested_mcores",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "cpu_limit_mcores",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "memory_mib_usage_max",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "memory_requested_mib",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "memory_limit_mib",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "cpu_request_utilization",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "memory_request_utilization",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "cpu_requested_recommendation",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "cpu_limit_recommendation",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "memory_requested_recommendation",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "memory_limit_recommendation",
      "type": "FLOAT",
      "mode": "NULLABLE"
    },
    {
      "name": "priority",
      "type": "FLOAT",
      "mode": "NULLABLE"
    }
  ]

  ```

3. Deploy Config Map and Cron job

```sh
  kubectl apply -f gke-vpa-recommendations/k8s/cronjob.yaml
```
