# Setup

1. Set project 

```sh
export PROJECT_ID="your-gcp-project-id"
export DATASET="gke-metric-dataset"
export TABLE="metrics"
export PUBSUB_TOPIC_ID="gke-namespace"
export DESTINATION_PUBSUB_TOPIC_ID="gke-metric-to-bq"
export PUBSUB_SUBSCRIPTION_ID="gke-namespace-sub"
export BIGQUERY_SUBSCRIPTION_ID="gke-metric-to-bq-sub"
export PUBSUB_SCHEMA_FILE="schemas/pubsub_schema.json"
export BIGQUERY_SCHEMA_FILE="schemas/bigquery_schema.json"
export CLUSTER_NAME="your-cluster"
export REGION="us-central1"

# To exclude namespaces
export EXCLUDED_NS="namespace1,namespace2,..."

# To only get specfic namespaces
export INCLUDED_NS="namespace3,namespace4,..."

# To include k8s objects
export INCLUDED_OBJECTS="CronJob,..."
gcloud config set project $PROJECT_ID
gcloud auth application-default login
```

1. Create BigQuery Dataset

```bash
gcloud bigquery datasets create $DATASET \
  --project=$PROJECT_ID
```

1. Create BigQuery Table

Use this if you have a BigQuery schema (`schema.json`):

```bash
bq mk --table \
  --project_id=$PROJECT_ID \
  --schema=$BIGQUERY_SCHEMA_FILE \
  $DATASET.$TABLE
```

> Skip or modify this if your schema comes from the Pub/Sub Avro message.


1. Create Pub/Sub Topics

```bash
gcloud pubsub topics create $PUBSUB_TOPIC_ID --project=$PROJECT_ID
gcloud pubsub topics create $DESTINATION_PUBSUB_TOPIC_ID --project=$PROJECT_ID
```

1. Create Pull Subscription for `gke-namespace`

```bash
gcloud pubsub subscriptions create $PUBSUB_SUBSCRIPTION_ID\
  --topic=$PUBSUB_TOPIC_ID \
  --project=$PROJECT_ID \
  --ack-deadline=30
```

1. Create BigQuery Subscription with Avro Schema

Make sure `pubsub_schema.json` contains a **valid Avro schema**.

```bash
gcloud pubsub subscriptions create $BIGQUERY_SUBSCRIPTION_ID \
  --topic=$DESTINATION_PUBSUB_TOPIC_ID \
  --bigquery-table=$PROJECT_ID:$DATASET.$TABLE \
  --use-topic-schema \
  --message-format=avro \
  --avro-schema-file=$SCHEMA_FILE \
  --project=$PROJECT_ID
```

1. Create an artifact repository (If we don't already have one)

```sh
gcloud artifacts repositories create main \
    --repository-format=docker \
    --location=us-central1
```

1. Build images

```sh
gcloud builds submit --config cloudbuild.yaml .
```

1. Grant permissions

```sh
gcloud iam service-accounts create metrics-accessor \
  --description="Access to Cloud Monitoring for K8s Job" \
  --display-name="metrics-accessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:metrics-accessor@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/monitoring.viewer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:metrics-accessor@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/iam.workloadIdentityUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:metrics-accessor@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:metrics-accessor@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/pubsub.subscriber"

gcloud iam service-accounts add-iam-policy-binding \
   --role roles/iam.workloadIdentityUser \
   --member "serviceAccount:${PROJECT_ID}.svc.id.goog[NAMESPACE/KSA]" \
   metrics-accessor@{$PROJECT_ID}.iam.gserviceaccount.com

```

1. Apply manifests

```sh
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION --project $PROJECT_ID
kubectl apply -f k8s/
```

1. Manually run the cronjob

```sh
kubectl create job manual-test --from=cronjob/gke-namespace-metric-builder-cronjob
```
