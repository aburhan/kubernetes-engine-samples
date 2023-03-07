## Table of Contents
- [Create PKI](#create-pki)
- [Populate Artifact Registry with required Docker images](#populate-artifact-registry-with-required-docker-images)
- [Deploy Kafka onto GKE](#deploy-kafka-onto-gke)

## Create PKI
While this task is usually goverened/executed by internal systems and prceedures, the below PKI generation serves to demo SSL/TLS communication between the different components of kafka, in order not to have anything in PLAINTEXT.
### Create CA Root Cert
_workdir is {RepoRoot}/kafka/helm/ssl_
```
### Create Encrypted RSA Key Pair
### Create CA Root Cert and Self Sign it
openssl req -x509 -sha256 -new -days 3650 -nodes -keyout ca-key -out ca-cert -config root.cnf

### Verify Cert
openssl x509 -text -in ca-cert
```

### Create Signed Cert for Brokers
_workdir is {RepoRoot}/kafka/helm/ssl_
```
for x in 0 1 2
do
  ### Create RSA Key Pair
  openssl genrsa -out broker${x}-key 2048
  openssl rsa -in broker${x}-key -pubout -out broker0-key.pub

  ## Convert to PKCS#8
  openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in broker${x}-key -out broker${x}-pkcs8-key
  mv broker${x}-pkcs8-key broker${x}-key

  ### Create CSR
  openssl req -sha256 -new -nodes -key broker${x}-key -out broker${x}-csr -config broker.cnf

  ### Create CA-Signed Cert for Broker
  openssl x509 -req -in broker${x}-csr -days 365 -CA ca-cert -CAkey ca-key -CAcreateserial -out broker${x}-cert -sha256 -extfile broker.cnf -extensions req_ext

  ### Verify Cert
  openssl x509 -text -in broker${x}-cert
  openssl verify -verbose -CAfile ca-cert broker${x}-cert
done
```

### Create Signed Cert for Kafka Client
_workdir is {RepoRoot}/kafka/helm/ssl_
```
### Create RSA Key Pair
openssl genrsa -out client-key 2048
openssl rsa -in client-key -pubout -out client-key.pub

## Convert to PKCS#8
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in client-key -out client-pkcs8-key
mv client-pkcs8-key client-key

### Create CSR
openssl req -sha256 -new -nodes -key client-key -out client-csr -config client.cnf

### Create CSR for client
openssl x509 -req -in client-csr -days 365 -CA ca-cert -CAkey ca-key -CAcreateserial -out client-cert -sha256 -extfile client.cnf

### Verify Cert
openssl x509 -text -in client-cert
openssl verify -verbose -CAfile ca-cert client-cert
```

## Populate Artifact Registry with required Docker images
Using the below commands:
```
SOURCE_REG=docker.io
DESTINATION_REG=us-docker.pkg.dev/$PROJECT_ID/main

for IMAGE_TAG in bitnami/kafka:3.2.1 bitnami/zookeeper:3.8.0 bitnami/kafka-exporter:1.6.0 bitnami/jmx-exporter:0.17.0
do
  docker pull --platform linux/amd64 $SOURCE_REG/$IMAGE_TAG
  docker tag $SOURCE_REG/$IMAGE_TAG $DESTINATION_REG/$IMAGE_TAG
  docker push $DESTINATION_REG/$IMAGE_TAG
done
```
populate Artifact registry with the below docker images:
- IMAGE: bitnami/kafka
  TAG: 3.2.1
- IMAGE: bitnami/zookeeper
  TAG: 3.8.0
- IMAGE: bitnami/kafka-exporter
  TAG: 1.6.0
- IMAGE: bitnami/jmx-exporter
  TAG: 0.17.0

## Deploy Kafka onto GKE

Fetch credentials
```
gcloud container clusters get-credentials kafka1-auto-central --region us-central1
```

### Create 'kafka' namespace
```
kubectl create namespace kafka
```

### Create K8s Secrets
_workdir is {RepoRoot}/kafka/helm/ssl_
```
### Secrets for Broker TLS
for x in 0 1 2
do
    kubectl -n kafka create secret generic kafka-pem-${x} \
        --from-file=ca.crt=./ca-cert \
        --from-file=tls.crt=./broker${x}-cert \
        --from-file=tls.key=./broker${x}-key
    kubectl -n kafka label secret kafka-pem-${x} app.kubernetes.io/name=kafka
done

### Secrets for Kafka Client TLS
kubectl -n kafka create secret generic client-pem \
    --from-file=ca.crt=./ca-cert \
    --from-file=tls.crt=./client-cert \
    --from-file=tls.key=./client-key
kubectl -n kafka label secret client-pem app.kubernetes.io/name=kafka

### At the time of writting, the Zookeeper dependency chart could not consume the client cert and key in pem format from the client-pem secret created above, but rather required certs and keys to be in JKS format. So, the below is required as well prior to deploying the kafka chart.
### The passphrases must be at least 6 characters
KEYSTORE_PASS=... (enter required pass)
TRUSTSTORE_PASS=... (enter required pass)
openssl pkcs12 -export -in client-cert \
    -passout pass:${KEYSTORE_PASS} \
    -inkey client-key \
    -out keystore.p12
keytool -importkeystore -srckeystore keystore.p12 \
    -srcstoretype PKCS12 \
    -srcstorepass ${KEYSTORE_PASS} \
    -deststorepass ${KEYSTORE_PASS} \
    -destkeystore zookeeper.keystore.jks
rm keystore.p12
keytool -import -file ca-cert \
    -keystore zookeeper.truststore.jks \
    -storepass ${TRUSTSTORE_PASS} \
    -noprompt

kubectl -n kafka create secret generic kafka-zookeeper-client-certs \
    --from-file=zookeeper.keystore.jks=./zookeeper.keystore.jks \
    --from-file=zookeeper.truststore.jks=./zookeeper.truststore.jks
kubectl -n kafka label secret kafka-zookeeper-client-certs app.kubernetes.io/name=kafka
kubectl -n kafka create secret generic kafka-zookeeper-client-certs-pass \
    --from-literal=keystore-password=${KEYSTORE_PASS} \
    --from-literal=truststore-password=${TRUSTSTORE_PASS}
kubectl -n kafka label secret kafka-zookeeper-client-certs-pass app.kubernetes.io/name=kafka
```
_the labelling of the secrets is required for **Backup for GKE** in the case that ProtectedApplication is configured rather than backing up of entire namespace, and that is to include the secrets in the backup as part of the Protected App_

### Deploy Kafka helm chart
_workdir is {RepoRoot}//kafka/helm/kafka-bootstrap_
```
### resolve and fetch chart dependencies.
helm dependency update
### make sure chart renders successfully.
helm -n kafka template kafka .
### Install the Chart (releasename=kafka)
helm -n kafka upgrade --install kafka ./ \
  --set global.imageRegistry=us-docker.pkg.dev/$PROJECT_ID/main
```
