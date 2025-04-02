# Setup

1. Create an artifact repository

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
   --member "serviceAccount:gke-vpa-optimization.svc.id.goog[default/metrics-job]" \
   metrics-accessor@gke-vpa-optimization.iam.gserviceaccount.com

```

1. Apply manifests

```sh
kubectl apply -f k8s/
```

1. Manually run the cronjob

```sh
kubectl create job manual-test --from=cronjob/gke-namespace-metric-builder-cronjob
```
