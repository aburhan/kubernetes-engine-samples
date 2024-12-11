## Instructions
## Prereq
1. A k8 service account bound to a GCP service account with metric following permissions
    BigQuery Data Editor
    BigQuery Data Viewer
    BigQuery Job User
    Monitoring Metric Writer
    Monitoring Viewer

1. Build image

  ```sh
    cd kubernetes-engine-samples/cost-optimization/gke-vpa-recommendations
    export PROJECT_ID=gke-rightsize
    export REGION=us-central1
    export ZONE=us-central1-f
    export IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/main/workload-vpa-recs-image:latest
    gcloud auth configure-docker $REGION-docker.pkg.dev
    gcloud builds submit metrics-exporter --region=$REGION --tag $IMAGE
  ```

2. Create the bigquery table

```sh
bq mk --table \
  $PROJECT_ID:gke_metrics_dataset.gke-vpa-recommendations2 \
  scripts/sql/bigquery_schema.json
```

3. Create config map

  ```sh
  kubectl create configmap namespace-config \
  --namespace=default \
  --from-literal=PROJECT_ID=gke-rightsize \
  --from-literal=BIGQUERY_DATASET=gke_metrics_dataset \
  --from-literal=BIGQUERY_TABLE=gke_vpa_recommendations \
  --from-literal=DEFAULT_WINDOW_DAYS=14 \
  --from-literal=MEMORY_RECOMMENDATION_BUFFER=1.10 \
  --from-file=namespace.txt=/home/admin_/kubernetes-engine-samples/cost-optimization/gke-vpa-recommendations/metrics-exporter/namespace.txt

  ```

4. Update the image, serviceaccount and Deploy Cronjob

  ```sh
  kubectl apply -f k8s/cronjob.yaml
  ```

Bigquery schema

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
