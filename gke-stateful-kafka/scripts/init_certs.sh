#!/bin/sh

set -e
set -x

REPLICAS=2

KEYSTORE_PASS="$(openssl rand -hex 6)"
TRUSTSTORE_PASS="$(openssl rand -hex 6)"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

### Create Encrypted RSA Key Pair
openssl genrsa -aes256 -out "$TMPDIR/ca-key" -passout pass:${TRUSTSTORE_PASS} 2048
openssl rsa -in "$TMPDIR/ca-key" -passin pass:${TRUSTSTORE_PASS} -pubout -out "$TMPDIR/ca-key.pub"

### Create CA Root Cert and Self Sign it
openssl req -x509 -sha256 -new -days 3650 -nodes -key "$TMPDIR/ca-key" -out "$TMPDIR/ca-cert" -passin pass:${TRUSTSTORE_PASS} -config helm/ssl/root.cnf

### Verify Cert
openssl x509 -text -in "$TMPDIR/ca-cert"

for x in $(seq 0 $REPLICAS)
do
  ### Create RSA Key Pair
  openssl genrsa -out "$TMPDIR/broker${x}-key" 2048
  openssl rsa -in "$TMPDIR/broker${x}-key" -pubout -out "$TMPDIR/broker0-key.pub"

  ## Convert to PKCS#8
  openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in "$TMPDIR/broker${x}-key" -out "$TMPDIR/broker${x}-pkcs8-key"
  mv "$TMPDIR/broker${x}-pkcs8-key" "$TMPDIR/broker${x}-key"

  ### Create CSR
  openssl req -sha256 -new -nodes -key "$TMPDIR/broker${x}-key" -out "$TMPDIR/broker${x}-csr" -config helm/ssl/broker.cnf

  ### Create CA-Signed Cert for Broker
  openssl x509 -req -in "$TMPDIR/broker${x}-csr" -days 365 -CA "$TMPDIR/ca-cert" -CAkey "$TMPDIR/ca-key" -CAcreateserial -out "$TMPDIR/broker${x}-cert" -sha256 -extfile helm/ssl/broker.cnf -extensions req_ext -passin pass:${TRUSTSTORE_PASS}

  ### Verify Cert
  openssl x509 -text -in "$TMPDIR/broker${x}-cert"
  openssl verify -verbose -CAfile "$TMPDIR/ca-cert" "$TMPDIR/broker${x}-cert"
done

### Create RSA Key Pair
openssl genrsa -out "$TMPDIR/client-key" -passout pass:${TRUSTSTORE_PASS} 2048
openssl rsa -in "$TMPDIR/client-key" -pubout -out "$TMPDIR/client-key.pub"

## Convert to PKCS#8
openssl pkcs8 -topk8 -inform PEM -outform PEM -nocrypt -in "$TMPDIR/client-key" -out "$TMPDIR/client-pkcs8-key"
mv "$TMPDIR/client-pkcs8-key" "$TMPDIR/client-key"

### Create CSR
openssl req -sha256 -new -nodes -key "$TMPDIR/client-key" -out "$TMPDIR/client-csr" -config helm/ssl/client.cnf

### Create CSR for client
openssl x509 -req -in "$TMPDIR/client-csr" -days 365 -CA "$TMPDIR/ca-cert" -CAkey "$TMPDIR/ca-key" -CAcreateserial -out "$TMPDIR/client-cert" -sha256 -extfile helm/ssl/client.cnf -passin pass:${TRUSTSTORE_PASS}

### Verify Cert
openssl x509 -text -in "$TMPDIR/client-cert"
openssl verify -verbose -CAfile "$TMPDIR/ca-cert" "$TMPDIR/client-cert"

### Secrets for Broker TLS
for x in $(seq 0 $REPLICAS)
do
    kubectl -n kafka create secret generic kafka-pem-${x} \
        --from-file=ca.crt="$TMPDIR/ca-cert" \
        --from-file=tls.crt="$TMPDIR/broker${x}-cert" \
        --from-file=tls.key="$TMPDIR/broker${x}-key"
    kubectl -n kafka label secret kafka-pem-${x} app.kubernetes.io/name=kafka
done

### Secrets for Kafka Client TLS
kubectl -n kafka create secret generic client-pem \
    --from-file=ca.crt="$TMPDIR/ca-cert" \
    --from-file=tls.crt="$TMPDIR/client-cert" \
    --from-file=tls.key="$TMPDIR/client-key"
kubectl -n kafka label secret client-pem app.kubernetes.io/name=kafka

### Root CA
#openssl pkcs12 -export -in ca-cert -inkey ca-key -out ca-cert.p12
#keytool -importkeystore -srckeystore ca-cert.p12 -srcstoretype pkcs12 -destkeystore ca-cert.jks

### At the time of writting, the Zookeeper dependency chart could not consume the client cert and key in pem format from the client-pem secret created above, but rather required certs and keys to be in JKS format. So, the below is required as well prior to deploying the kafka chart.
### The passphrases must be at least 6 characters

openssl pkcs12 -export -in "$TMPDIR/client-cert" \
    -passout pass:${KEYSTORE_PASS} \
    -inkey "$TMPDIR/client-key" \
    -out "$TMPDIR/keystore.p12"
keytool -importkeystore -srckeystore "$TMPDIR/keystore.p12" \
    -srcstoretype PKCS12 \
    -srcstorepass ${KEYSTORE_PASS} \
    -deststorepass ${KEYSTORE_PASS} \
    -destkeystore "$TMPDIR/zookeeper.keystore.jks"

keytool -import -file "$TMPDIR/ca-cert" \
    -keystore "$TMPDIR/zookeeper.truststore.jks" \
    -storepass ${TRUSTSTORE_PASS} \
    -noprompt

kubectl -n kafka create secret generic kafka-zookeeper-client-certs \
    --from-file=zookeeper.keystore.jks="$TMPDIR/zookeeper.keystore.jks" \
    --from-file=zookeeper.truststore.jks="$TMPDIR/zookeeper.truststore.jks"
kubectl -n kafka label secret kafka-zookeeper-client-certs app.kubernetes.io/name=kafka
kubectl -n kafka create secret generic kafka-zookeeper-client-certs-pass \
    --from-literal=keystore-password=${KEYSTORE_PASS} \
    --from-literal=truststore-password=${TRUSTSTORE_PASS}
kubectl -n kafka label secret kafka-zookeeper-client-certs-pass app.kubernetes.io/name=kafka
