#!/bin/bash

# What gets created:
# 1. A global VPC network.
# 2. 2x subnets, each with 2x Secondary CIDR Ranges, in 2x regions; us-central1 & us-west1.
# 3. GCP Service Account to be used by GKE clusters, as well as IAM Policy Bindings.
# 4. Docker type repository in Artifact Registry, as well as IAM Policy Bindings for the Service Account.
# 5. 2x GKE private regional clusters, with backup agent enabled, as well as Workload Identity. Each cluster resides in one region; us-central1 & us-west1.
# 6. At least 2x node pools for each cluster (for System and App Pods), distributed across the zones of the region where a cluster resides.

# Update PROJECT_ID Variable below, and uncomment export command.
# export PROJECT_ID=CHANGEME
export LOCATION=us
export REGION=us-central1
export ART_REG_REPO_NAME=main
export VPC_NAME=vpc-gke-kafka
export SUBNET_NAME=snet-gke-kafka-$REGION
export SUBNET_RANGE=10.0.0.0/17
export SUBNET_REGION=$REGION
export SUBNET_SECONDARY_RANGES=ip-range-pods-$REGION=192.168.0.0/18,ip-range-svc-$REGION=192.168.64.0/18
export SERVICE_ACCOUNT_NAME=gke-kafka-sa
export SERVICE_ACCOUNT_ROLES="logging.logWriter monitoring.metricWriter monitoring.viewer stackdriver.resourceMetadata.writer"
export GKE_CLUSTER_NAME=gke-kafka-$REGION
export GKE_MASTER_CIDR=172.16.0.0/28
export GKE_POD_CIDR=192.168.0.0/18
export GKE_POD_RANGE_NAME=ip-range-pods-$REGION
export GKE_SVC_CIDR=192.168.64.0/18
export GKE_SVC_RANGE_NAME=ip-range-svc-$REGION
export GKE_OAUTH_SCOPES=https://www.googleapis.com/auth/cloud-platform
export GKE_RELEASE_CHANNEL=rapid
export GKE_CLUSTER_VERSION_ARGS="--cluster-version=1.25"

## Variables for DR Region
export DR_CREATE=true
export DR_LOCATION=us
export DR_REGION=us-west1
export DR_SUBNET_NAME=snet-gke-kafka-$DR_REGION
export DR_SUBNET_RANGE=10.0.128.0/17
export DR_SUBNET_REGION=$DR_REGION
export DR_SUBNET_SECONDARY_RANGES=ip-range-pods-$DR_REGION=192.168.128.0/18,ip-range-svc-$DR_REGION=192.168.192.0/18
export DR_GKE_CLUSTER_NAME=gke-kafka-$DR_REGION
export DR_GKE_MASTER_CIDR=172.16.0.16/28
export DR_GKE_POD_CIDR=192.168.128.0/18
export DR_GKE_POD_RANGE_NAME=ip-range-pods-$DR_REGION
export DR_GKE_SVC_CIDR=192.168.192.0/18
export DR_GKE_SVC_RANGE_NAME=ip-range-svc-$DR_REGION
export DR_GKE_OAUTH_SCOPES=https://www.googleapis.com/auth/cloud-platform

create_subnet ()
{
  # https://cloud.google.com/sdk/gcloud/reference/compute/networks/subnets/create
  echo Creating subnet $SUBNET_NAME...
  gcloud compute networks subnets create $SUBNET_NAME \
    --project $PROJECT_ID \
    --network=$VPC_NAME \
    --range=$SUBNET_RANGE \
    --region=$REGION \
    --enable-private-ip-google-access \
    --purpose=PRIVATE \
    --stack-type=IPV4_ONLY \
    --secondary-range $SUBNET_SECONDARY_RANGES
}

check_cluster_status ()
{
  for i in {1..30}
  do
    unset CLUSTER_STATUS
    CLUSTER_STATUS=$(gcloud container clusters describe $GKE_CLUSTER_NAME \
        --project $PROJECT_ID \
        --region=$REGION \
        --format json | jq -r .status)
    if [ "$CLUSTER_STATUS" == "RUNNING" ]
    then
      echo Cluster in "Running" State
      break
    else
      echo Waiting on Cluster to be in "Running" State...
      sleep 60
    fi
  done

  if [ "$CLUSTER_STATUS" != "RUNNING" ]
  then
    echo $1
    echo exiting script
    exit 1
  fi
}

create_cluster ()
{
  # https://cloud.google.com/sdk/gcloud/reference/beta/container/clusters/create
  echo Creating GKE cluster $GKE_CLUSTER_NAME...
  gcloud beta container clusters create-auto $GKE_CLUSTER_NAME \
      --project $PROJECT_ID \
      --region $REGION \
      --release-channel $GKE_RELEASE_CHANNEL \
      $GKE_CLUSTER_VERSION_ARGS \
      --service-account $SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com \
      --enable-private-nodes \
      --no-enable-master-authorized-networks \
      --master-ipv4-cidr $GKE_MASTER_CIDR \
      --network $VPC_NAME \
      --subnetwork $SUBNET_NAME \
      --cluster-secondary-range-name $GKE_POD_RANGE_NAME \
      --services-secondary-range-name $GKE_SVC_RANGE_NAME
}

if [ -z "$PROJECT_ID" ]
then
  echo "Please update and export Environment variable PROJECT_ID at top of this script."
else
  echo "Working on project: $PROJECT_ID"

  # Enable necessary APIs for the project
  echo Enabling required Service APIs...
  gcloud services --project $PROJECT_ID enable artifactregistry.googleapis.com
  gcloud services --project $PROJECT_ID enable compute.googleapis.com
  gcloud services --project $PROJECT_ID enable container.googleapis.com
  gcloud services --project $PROJECT_ID enable iam.googleapis.com


  # https://cloud.google.com/sdk/gcloud/reference/iam/service-accounts/create
  echo Creating Service Account $SERVICE_ACCOUNT_NAME...
  gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
        --project $PROJECT_ID \
        --display-name="Service Account for cluster $GKE_CLUSTER_NAME"

  # https://cloud.google.com/sdk/gcloud/reference/projects/add-iam-policy-binding
  SERVICE_ACCOUNT_ROLES_ARRAY=($SERVICE_ACCOUNT_ROLES)
  for ROLE in "${SERVICE_ACCOUNT_ROLES_ARRAY[@]}"
  do
    echo Creating iam policy binding to SA $SERVICE_ACCOUNT_NAME and role $ROLE...
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
      --role="roles/$ROLE"
  done

  # https://cloud.google.com/sdk/gcloud/reference/artifacts/repositories/create
  echo Creating Art Reg $ART_REG_REPO_NAME...
  gcloud artifacts repositories create $ART_REG_REPO_NAME \
        --project $PROJECT_ID \
        --location=$LOCATION \
        --repository-format docker

  echo Adding iam-policy-binding for SA $SERVICE_ACCOUNT_NAME on Registry $ART_REG_REPO_NAME...
  gcloud artifacts repositories add-iam-policy-binding $ART_REG_REPO_NAME \
         --project $PROJECT_ID \
         --location=$LOCATION \
         --member="serviceAccount:$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com" \
         --role="roles/artifactregistry.reader"

  # https://cloud.google.com/sdk/gcloud/reference/compute/networks/create
  echo Creating VPC $VPC_NAME...
  gcloud compute networks create $VPC_NAME \
    --project $PROJECT_ID \
    --bgp-routing-mode=global \
    --subnet-mode=custom

  create_subnet
  create_cluster

  if [[ $DR_CREATE ]]
  then
    echo Creating DR Components...
    export LOCATION=$DR_LOCATION
    export REGION=$DR_REGION
    export SUBNET_NAME=$DR_SUBNET_NAME
    export SUBNET_RANGE=$DR_SUBNET_RANGE
    export SUBNET_REGION=$DR_SUBNET_REGION
    export SUBNET_SECONDARY_RANGES=$DR_SUBNET_SECONDARY_RANGES
    export GKE_CLUSTER_NAME=$DR_GKE_CLUSTER_NAME
    export GKE_MASTER_CIDR=$DR_GKE_MASTER_CIDR
    export GKE_POD_CIDR=$DR_GKE_POD_CIDR
    export GKE_POD_RANGE_NAME=$DR_GKE_POD_RANGE_NAME
    export GKE_SVC_CIDR=$DR_GKE_SVC_CIDR
    export GKE_SVC_RANGE_NAME=$DR_GKE_SVC_RANGE_NAME
    export GKE_OAUTH_SCOPES=$DR_GKE_OAUTH_SCOPES

    create_subnet
    create_cluster
  fi
fi