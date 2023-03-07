## Table of Contents
- [Directory Structure](#directory-structure)
- [Setting Some Env vars](#setting-some-env-vars)
- [Deploying Kafka](#deploying-kafka)
- [Monitoring Kafka](#monitoring-kafka)
- [Produce and Consume from Kafka](#produce-and-consume-from-kafka)
- [Benchmarking Kafka](#benchmarking-kafka)
- [Backup for GKE](#backup-for-gke)
- [GKE Upgrade](#gke-upgrade)
- [Application Upgrade](#application-upgrade)
- [Failover](#failover)

## Directory Structure
```
├── README.md     --> This README.
├── gcloud        --> Includes shell scripts to spin up the required infrastructure using gcloud (Option1).
├── terraform     --> Includes Terraform plan to spin up the required infrastructure (Option2).
├── helm          --> Includes a pre-configured kafka bootstraping Helm Chart which can be deployed on Kubernetes/GKE.
└── dashboards    --> Includes Google Cloud Monitoring dashboards (JSON files) for Kafka and GKE.
```

## Setting Some Env vars
_Setting some environment variables which are using throughout this README_
```
export PROJECT_ID=sada-reference-guides
export REGION=us-central1
export CLUSTER_NAME=gke-kafka-$REGION
export DR_REGION=us-west1
export DR_CLUSTER_NAME=gke-kafka-$DR_REGION

export KAFKA_IMAGE=us-docker.pkg.dev/$PROJECT_ID/main/bitnami/kafka:3.2.1
```

## Deploying Kafka
Kafka is deployed to GKE using a **kafka-bootstrap** helm chart, which has Bitnami's [Kafka Helm Chart](https://artifacthub.io/packages/helm/bitnami/kafka/) as a dependency in its Chart.yaml file. Please refer to the `README.md` under `helm` folder for details.
The **monitoring-stack-bootstrap** helm chart should be deployed prior to deploying **kafka-bootstrap** Helm Chart, since the **kafka-bootstrap** chart also deploys _ServiceMonitor_ custom resources whose CRDs are part of the Prometheus Operator embedded in the **monitoring-stack-bootstrap**.

## Monitoring Kafka
Monitoring Kafka means monitoring the Kafka Application as well as the hosting Infrastructure (i.e. the GKE Cluster where Kafka is deployed). As part of the kafka helm chart deployment, _ServiceMonitor_ objects are created in GKE for Kafka metrics, Zookeeper metrics, and JMX metrics. The Prometheus Instance will scrape the targets specified in those _ServiceMonitor_ objects, and push the collected metrics to _Managed Service for Prometheus_. Once metrics are in _Managed Service for Prometheus_, they can be visualized using Cloud Monitoring Dashboards.
Dashboards can be directly created in Google Cloud Console, and then exported and kept in git repo ( **{CURRENT_FOLDER}/dashboards** ); In the dashboard toolbar, open the _JSON editor_ and download the Dashboard JSON file.
To import a dashboard from a JSON file, this can also be done in Google Cloud Console (Click _+Create Dashboard_ and upload dashboard json content via _JSON editor_ menu), or via the gcloud command below:

```
gcloud monitoring dashboards create \
        --config-from-file DASHBOARD_JSON_FILE \
        --project $PROJECT_ID
```

### Alerting

```
### Create Email type notification channel, and note down the returned fully qualified identifier for the notification_channel, which should be in the format projects/$PROJECT_ID/notificationChannels/CHANNEL_ID
gcloud alpha monitoring channels create \
        --project=$PROJECT_ID \
        --display-name="Kafka Email Notification Channel" \
        --type=email \
        --channel-labels=email_address=EMAIL_ADDRESS

### Create the alert policies from json files.
for POLICY_FILE in $(find alert-policies/ -name '*.json')
do
  gcloud alpha monitoring policies create \
        --project=$PROJECT_ID \
        --notification-channels=NOTIFICATION_CHANNEL_IDENTIFIER \
        --policy-from-file=$POLICY_FILE
done
```

## Produce and Consume from Kafka
The producer & consumer scripts can be found in the same kafka docker image provided by bitnami and declared in the kafka chart. They can be found under _/opt/bitnami/kafka/bin/_ along with other provded scripts.
These scripts can also be found when manually downloading the .tgz kafka package straight from https://kafka.apache.org/downloads.

To test produce/consume messages from kafka, one can deploy a long running kafka pod as below:
```
cat <<EOF | kubectl -n kafka apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: kafka-test-pod
spec:
  containers:
  - name: kafka
    image: $KAFKA_IMAGE
    # Just spin & wait forever
    command: [ "/bin/bash", "-c", "--" ]
    args: [ "while true; do sleep 30; done;" ]
EOF
```

and then exec into that pod and start producing/consuming messages
```
### Bulk produce random strings into topic "topic1"
ALLOW_PLAINTEXT_LISTENER=yes
for x in {0..200}; do
  echo $x: the lucky number is $(( RANDOM % 1000000 ));
done | kafka-console-producer.sh \
            --broker-list kafka-0.kafka-headless.kafka.svc.cluster.local:9092,kafka-1.kafka-headless.kafka.svc.cluster.local:9092,kafka-2.kafka-headless.kafka.svc.cluster.local:9092 \
            --topic topic1 \
            --property parse.key=true \
            --property key.separator=":"
### Consume from topic "topic1" from all partitions.
kafka-console-consumer.sh \
            --bootstrap-server kafka.kafka.svc.cluster.local:9092 \
            --topic topic1 \
            --property print.key=true \
            --property key.separator=" : " \
            --from-beginning;

for x in {0..200}; do
  echo $x: the lucky number is $(( RANDOM % 1000000 ));
done | kafka-console-producer.sh \
            --producer.config ${CLIENT_PROPS_FILE} \
            --broker-list kafka-0.kafka-headless.kafka.svc.cluster.local:9092,kafka-1.kafka-headless.kafka.svc.cluster.local:9092,kafka-2.kafka-headless.kafka.svc.cluster.local:9092 \
            --topic topic1 \
            --property parse.key=true \
            --property key.separator=":"

### Consume from topic "topic1" from all partitions.
kafka-console-consumer.sh \
            --consumer.config ${CLIENT_PROPS_FILE} \
            --bootstrap-server kafka.kafka.svc.cluster.local:9092 \
            --topic topic1 \
            --property print.key=true \
            --property key.separator=" : " \
            --from-beginning;
```
where the variable CLIENT_PROPS_FILE points to a config properties file passed on to the script and includes configs like SSL, in our case. Below is an example.
```
cat << EOF >/opt/bitnami/client.properties
security.protocol=SSL
ssl.keystore.type=PEM
ssl.keystore.certificate.chain=-----BEGIN CERTIFICATE-----\nMIIDK....Mz/tXR\n-----END CERTIFICATE-----
ssl.keystore.key=-----BEGIN PRIVATE KEY-----\nMIIE....2kEY5\n-----END PRIVATE KEY-----
ssl.truststore.type=PEM
ssl.truststore.certificates=-----BEGIN CERTIFICATE-----\nMIIDD....IEh3\n-----END CERTIFICATE-----
EOF

export CLIENT_PROPS_FILE=/opt/bitnami/client.properties
```

## Benchmarking Kafka
In order to accurately model a use case, a simulation of the expected load on the cluster is performed. Depending on the app at hand, a specific benchmarking tool is used to perform this performance test. These load generation tools usually ship with the app vendor, and so is the case for Kafka. Kafka package includes the kafka-producer-perf-test and kafka-consumer-perf-test scripts in the bin folder.
```

### Fire Traffic
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic <TOPIC_NAME> \
                        --num-records 10000000 \
                        --throughput -1 \
                        --producer-props bootstrap.servers=${KAFKA_SERVICE:-kafka.kafka.svc.cluster.local:9092} \
                                        batch.size=<BATCH_SIZE> \
                                        acks=<ACKS> \
                                        linger.ms=<LINGER_TIME> \
                                        compression.type=<COMPRESSION> \
                        --producer.config ${CLIENT_PROPS_FILE} \
                        --record-size <RECORD_SIZE> \
                        --print-metrics
```

Below is an example:
```
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic topic-1 \
                        --num-records 10000000 \
                        --throughput -1 \
                        --producer-props bootstrap.servers=kafka.kafka.svc.cluster.local:9092 \
                                        batch.size=16384 \
                                        acks=all \
                                        linger.ms=500 \
                                        compression.type=uncompressed \
                        --producer.config ${CLIENT_PROPS_FILE} \
                        --record-size 100 \
                        --print-metrics
```

## Backup for GKE
### Setting Some Env vars
```
export BACKUP_PLAN_NAME=kafka-protected-app
export BACKUP_NAME=protected-app-backup-1
export RESTORE_PLAN_NAME=kafka-protected-app
export RESTORE_NAME=protected-app-restore-1

```
### Create Backup plan
_the below assumes Protected application manifests already deployed to cluster and "ready for backup"._
```
gcloud beta container backup-restore backup-plans create $BACKUP_PLAN_NAME \
    --project=$PROJECT_ID \
    --location=$DR_REGION \
    --cluster=projects/$PROJECT_ID/locations/$REGION/clusters/$CLUSTER_NAME \
    --selected-applications=kafka/kafka,kafka/zookeeper \
    --include-secrets \
    --include-volume-data \
    --cron-schedule="0 3 * * *" \
    --backup-retain-days=7 \
    --backup-delete-lock-days=0
```
### Manually create a Backup
_while scheduled backups are governed by the cron-schedule in the backup plan, the below serves as a one-time backup initiation._
```
gcloud beta container backup-restore backups create $BACKUP_NAME \
    --project=$PROJECT_ID \
    --location=$DR_REGION \
    --backup-plan=$BACKUP_PLAN_NAME \
    --wait-for-completion
```
### Create Restore Plan
```
gcloud beta container backup-restore restore-plans create $RESTORE_PLAN_NAME \
    --project=$PROJECT_ID \
    --location=$DR_REGION \
    --backup-plan=projects/$PROJECT_ID/locations/$DR_REGION/backupPlans/$BACKUP_PLAN_NAME \
    --cluster=projects/$PROJECT_ID/locations/$DR_REGION/clusters/$DR_CLUSTER_NAME \
    --cluster-resource-conflict-policy=use-existing-version \
    --namespaced-resource-restore-mode=delete-and-restore \
    --volume-data-restore-policy=restore-volume-data-from-backup \
    --selected-applications=kafka/kafka,kafka/zookeeper \
    --cluster-resource-restore-scope="storage.k8s.io/StorageClass"
```
### Restore from Backup
```
gcloud beta container backup-restore restores create $RESTORE_NAME \
    --project=$PROJECT_ID \
    --location=$DR_REGION \
    --restore-plan=$RESTORE_PLAN_NAME \
    --backup=projects/$PROJECT_ID/locations/$DR_REGION/backupPlans/$BACKUP_PLAN_NAME/backups/$BACKUP_NAME
```

## GKE Upgrade
By default, automatic upgrades are enabled for GKE clusters (both control planes and node pools). The control plane and nodes do not necessarily run the same version at all times; they are in fact upgraded separately.
In order to showcase how an optimally configured stateful application deployment (i.e Kafka in this case) behaves during GKE control plane and node pool upgrades, manual upgrades can be triggered using the below snippet while noting different metrics.

```
### Get current master and node pool k8s versions.
gcloud container clusters describe \
      $CLUSTER_NAME \
      --region $REGION \
      --project $PROJECT_ID

### Create test topics (executed from "kafka-test-pod" created above)
for TOPIC in topic-cluster-upgrade topic-zookeeper-pool-upgrade topic-kafka-pool-upgrade
do
      /opt/bitnami/kafka/bin/kafka-topics.sh \
                          --create \
                          --if-not-exists \
                          --bootstrap-server kafka.kafka:9092 \
                          --replication-factor 3 \
                          --partitions 3 \
                          --config compression.type=uncompressed \
                          --topic $TOPIC
done
```

### Control Plane Upgrade
```
### Figure out the GKE version to upgrade to. [Available versions](https://cloud.google.com/kubernetes-engine/versioning#use_to_check_versions) can be listed via the command:
gcloud container get-server-config \
  		--project=$PROJECT_ID \
	  	--region=$REGION \
  		--flatten="channels" \
      --filter="channels.channel=REGULAR"

### Start test traffic, writing to topic "topic-cluster-upgrade" (executed from "kafka-test-pod" created above)
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic topic-cluster-upgrade \
                        --num-records 10000000000000 \
                        --throughput -1 \
                        --producer-props bootstrap.servers=kafka.kafka.svc.cluster.local:9092 \
                                        batch.size=1000 \
                                        acks=all \
                                        linger.ms=0 \
                                        compression.type=none \
                        --record-size 100 \
                        --print-metrics

### Start Control Plane upgrade.
K8S_VERSION=1.23.5-gke.1503
gcloud container clusters upgrade $CLUSTER_NAME \
      --region $REGION \
      --cluster-version "$K8S_VERSION" \
      --master \
      --project $PROJECT_ID
```

### Zookeeper Node Pool Upgrade (Surge upgrade)
```
### Start test traffic, writing to topic "topic-zookeeper-pool-upgrade" (executed from "kafka-test-pod" created above)
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic topic-zookeeper-pool-upgrade \
                        --num-records 10000000000000 \
                        --throughput -1 \
                        --producer-props bootstrap.servers=kafka.kafka.svc.cluster.local:9092 \
                                        batch.size=1000 \
                                        acks=all \
                                        linger.ms=0 \
                                        compression.type=none \
                        --producer.config ${CLIENT_PROPS_FILE} \
                        --record-size 100 \
                        --print-metrics

### Start Zookeeper Node Pool upgrade.
gcloud container clusters upgrade $CLUSTER_NAME \
      --region $REGION \
      --node-pool=pool-zookeeper \
      --project $PROJECT_ID
```

### Kafka Broker Node Pool Upgrade (Surge upgrade)
```
### Start test traffic, writing to topic "topic-kafka-pool-upgrade" (executed from "kafka-test-pod" created above)
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic topic-kafka-pool-upgrade \
                        --num-records 10000000000000 \
                        --throughput -1 \
                        --producer-props bootstrap.servers=kafka.kafka.svc.cluster.local:9092 \
                                        batch.size=1000 \
                                        acks=all \
                                        linger.ms=0 \
                                        compression.type=none \
                        --producer.config ${CLIENT_PROPS_FILE} \
                        --record-size 100 \
                        --print-metrics

### Start Kafka Broker Node Pool upgrade.
gcloud container clusters upgrade $CLUSTER_NAME \
      --region $REGION \
      --node-pool=pool-kafka \
      --project $PROJECT_ID
```

## Application Upgrade
The below table summarizes an application (Zookeeper & Kafka) upgrade test case, highlighting the FROM and TO Versions.
| Change                          	| FROM                    	| TO                       	| Change Method                        	| Corresponding Step(s)                        	  |
|---------------------------------	|-------------------------	|--------------------------	|--------------------------------------	|------------------------------------------------ |
| Helm Chart                      	| bitnami/kafka:16.3.2    	| bitnami/kafka:18.2.0     	| Direct (kafka-bootstrap Chart.yaml)  	| 2 & 5  	                                        |
| Kafka version(Docker image)     	| bitnami/kafka:3.1.1     	| bitnami/kafka:3.2.1      	| By change of Helm Chart version      	| 3, 6, & 7                                       |
| Helm Chart                      	| bitnami/zookeeper:9.1.5 	| bitnami/zookeeper:10.1.1 	| By chart dependency                  	| Indirect (as a result of changes made in row 2) |
| Zookeeper version(Docker image) 	| bitnami/zookeeper:3.7.1 	| bitnami/zookeeper:3.8.0  	| Direct (kafka-bootstrap values.yaml) 	| 3 & 6 	                                        |


Below are the steps followed to accomplish the upgrade as per table above (_workdir is {RepoRoot}/kafka/helm/kafka-bootstrap_):
```
### 1. Change into the kafka-bootstrap chart directory
cd {REPO_ROOT}/kafka/helm/kafka-bootstrap

### 2. Update the dependency in Chart.yaml of kafka-bootstrap helm chart to the FROM Version (i.e. 16.3.2).
dependencies:
- name: kafka
  repository: https://charts.bitnami.com/bitnami
  version: 16.3.2

### 3. Resolve the dependency and deploy.
rm -rf Chart.lock charts && \
helm dependency update && \
helm -n kafka upgrade --install kafka ./ \
		  --set kafka.image.tag=3.1.1,kafka.zookeeper.image.tag=3.7.1

### 4. From a test pod, create a test topic, and start producer test traffic.
/opt/bitnami/kafka/bin/kafka-topics.sh \
                          --create \
                          --if-not-exists \
                          --bootstrap-server kafka.kafka:9092 \
                          --replication-factor 3 \
                          --partitions 3 \
                          --command-config ${CLIENT_PROPS_FILE} \
                          --config compression.type=uncompressed \
                          --topic topic-app-upgrade
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic topic-app-upgrade \
                        --num-records 10000000000000 \
                        --throughput -1 \
                        --producer-props bootstrap.servers=kafka.kafka.svc.cluster.local:9092 \
                                        batch.size=1000 \
                                        acks=all \
                                        linger.ms=0 \
                                        compression.type=none \
                        --producer.config ${CLIENT_PROPS_FILE} \
                        --record-size 100 \
                        --print-metrics


### 5. Update the dependency in Chart.yaml of kafka-bootstrap helm chart to the TO Version (i.e. 18.2.0).
      dependencies:
	    - name: kafka
	      repository: https://charts.bitnami.com/bitnami
	      version: 18.2.0

### 6. Following the vendor documentation regarding the upgrade of the versions listed in the table, set the property inter.broker.protocol.version to the current kafka version (i.e. 3.1.1), resolve new dependency, and deploy chart with the new kafka & Zookeeper images in them, as follows:
rm -rf Chart.lock charts && \
helm dependency update && \
helm -n kafka upgrade --install kafka ./ \
      --set kafka.image.tag=3.2.1,kafka.zookeeper.image.tag=3.8.0 \
      --set "kafka.extraEnvVars[0].name=KAFKA_CFG_INTER_BROKER_PROTOCOL_VERSION" \
      --set "kafka.extraEnvVars[0].value=3.1.1"

### 7. Once the new Chart and docker images have been deployed, update the kafka property inter.broker.protocol.version again to the new kafka version (i.e 3.2.1) and re-deploy.
helm -n kafka upgrade --install kafka ./ \
      --set kafka.image.tag=3.2.1,kafka.zookeeper.image.tag=3.8.0 \
      --set "kafka.extraEnvVars[0].name=KAFKA_CFG_INTER_BROKER_PROTOCOL_VERSION" \
      --set "kafka.extraEnvVars[0].value=3.2.1"
```

## Failover
A failover simulation was performed which mimics the destruction of a Google Cloud Zone (i.e. non graceful termination of k8s nodes and deletion of Disks).

### Prerequisites
```
### For the VPC where the GKE Cluster is deployed, create a firewall rule which allows ingress from Identity-Aware Proxy (IAP) Service to node pools. This is required to SSH into private node pools, as in following steps.
gcloud compute firewall-rules create allow-ingress-from-iap
      --direction=INGRESS \
      --priority=1000 \
      --network=<VPC_NAME> \
      --action=ALLOW \
      --rules=tcp:22 \
      --source-ranges=35.235.240.0/20 \
      --project=$PROJECT_ID

### For each of the zookeeper and broker node pools, disable node auto-repair to prevent a new node coming up while the simulation is going.
gcloud container node-pools update <NODE_POOL_NAME> \
		  --cluster $CLUSTER_NAME \
		  --region=$REGION \
		  --no-enable-autorepair \
		  --project=$PROJECT_ID
```

### Steps
```
### Create topic "topic-failover-test" and produce test traffic.
/opt/bitnami/kafka/bin/kafka-topics.sh --create --if-not-exists \
		  --bootstrap-server kafka.kafka:9092 \
		  --replication-factor 3 --partitions 3 \
		  --command-config ${CLIENT_PROPS_FILE} \
		  --config compression.type=uncompressed \
		  --topic topic-failover-test
KAFKA_HEAP_OPTS="-Xms4g -Xmx4g" kafka-producer-perf-test.sh --topic topic-failover-test \
      --num-records 10000000000000 \
      --throughput -1 \
      --producer-props bootstrap.servers=kafka.kafka.svc.cluster.local:9092 \
            batch.size=1000 \
            acks=all \
            linger.ms=0 \
            compression.type=none \
      --producer.config ${CLIENT_PROPS_FILE} \
      --record-size 100 \
      --print-metrics

### SSH into the nodes of Zookeeper and Broker pool, in a specific zone, and shutdown the NIC, to simulate non-graceful zonal outage.
gcloud compute ssh <NODE_NAME> \
		  --zone <NODE_ZONE> \
		  --project $PROJECT_ID
sudo ifconfig eth0 down

### For each of the zookeeper and broker node pools, delete the VM in the Managed-Instance Group (MIG) for that zone.
gcloud compute instance-groups managed delete-instances <MIG_NAME> \
		  --instances <NODE_NAME> \
		  --zone <NODE_ZONE> \
		  --project $PROJECT_ID

### To simulate destruction of a bound PV as part of Zone failure, delete the PVCs (as well as PVs, since the reclaimPolicy is “Retain”) associated with the pods whose nodes were deleted; There should be 2 PVCs and 2 PVs, for broker and zookeeper.
kubectl -n kafka delete pvc <PVC_NAME>
kubectl patch pv <PV_NAME> --type='merge' -p '{"spec":{"claimRef": null}}'
kubectl delete pv <PV_NAME>
gcloud compute disks delete <PV_NAME> --project=$PROJECT_ID

### For each of the zookeeper and broker node pools, resize the MIG back up to 1 to simulate zone recovery or utilization of a new zone.
gcloud container clusters resize $CLUSTER_NAME \
		  --num-nodes=1 \
		  --node-pool=<NODE_POOL_NAME> \
		  --region=$REGION \
		  --project=$PROJECT_ID

### Delete the kafka and zookeeper pods, which will be stuck in pending state, to force a new PVC (and so a new PV) to be created by the new pod.
kubectl -n kafka delete pod <POD_NAME>

### Stop test traffic to topic "topic-failover-test".

### For each of the zookeeper and broker node pools, re-enable node auto-repair.
gcloud container node-pools update <NODE_POOL_NAME> \
		  --cluster $CLUSTER_NAME \
		  --region=$REGION \
		  --enable-autorepair \
		  --project=$PROJECT_ID
```