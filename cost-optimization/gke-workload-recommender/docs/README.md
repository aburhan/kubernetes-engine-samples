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

---

## Required Roles

Ensure you have the following Google Cloud roles:

-   `roles/monitoring.viewer`

Authenticate using the Google Cloud SDK:

```bash
gcloud auth application-default login
```

## Deployment Instructions

1. Set configuration environment variables:

```sh
PROJECT_ID=gke-rightsize
REGION=us-central1
ARTIFACT_REPO=workload-forecast-registry
SERVICE_ACCOUNT_NAME="bq-service-account"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"

gcloud config set project $PROJECT_ID
```

1. Enable services:

- Artifact Registry

```sh
gcloud services enable artifactregistry.googleapis.com

```

1. Create the service account:

```sh
gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
    --display-name "BigQuery Service Account"

# Assign IAM roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.dataViewer"

# Print the service account email
echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"
``


1. Deploy instructure:

- Bigquery dataset and table
- Artifact registry to store image
- Service account for Bigquery

```sh
terraform init deploy
terraform apply -var project_id=$PROJECT_ID -var=service_account_email=$SERVICE_ACCOUNT_EMAIL deploy
```

1. Set the pyton package repository:

```sh
gcloud config set artifacts/repository $ARTIFACT_REPO
gcloud config set artifacts/location $REGION
```

1. Install required packages to build and publish the Python package:

```sh
pip3 install twine
pip3 install build
python3 -m build
python3 -m twine upload --repository-url https://$REGION-python.pkg.dev/$PROJECT_ID/$ARTIFACT_REPO/ dist/*
```

1. Run the following command to print the repository configuration to add to your Python project:


