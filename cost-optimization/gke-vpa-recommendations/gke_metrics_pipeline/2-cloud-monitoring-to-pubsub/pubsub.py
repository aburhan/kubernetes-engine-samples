import json
import logging
from google.cloud import pubsub_v1
from monitoring import query_cloud_monitoring, build_cloud_monitoring_param
from utils import (
    get_first_point, get_value_from_point, process_metric_value
)
from config import PROJECT_ID, DESTINATION_PUBSUB_TOPIC_ID


def consume_messages(subscription_id):
    """
    Consumes messages from a Pub/Sub subscription, processes them, and
    publishes results to another Pub/Sub topic.

    Args:
        subscription_id (str): The ID of the Pub/Sub subscription to consume messages.
        destination_topic (str): The ID of the Pub/Sub topic to publish query results.
    """
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(PROJECT_ID, subscription_id)

    def callback(message):
        try:
            # Decode message
            message_data = json.loads(message.data.decode("utf-8"))
            logging.info(
                f"\nNamespace: {message_data['namespace']}"
                f"Received message: {message_data['cloud_monitoring_query']['metric']}")

            # Extract the query field
            query = build_cloud_monitoring_param(message_data)
            logging.debug(query)

            if not query:
                logging.warning("No 'query' field found in message. Skipping...")
                return

            # Call Cloud Monitoring API with the query
            monitoring_response = query_cloud_monitoring(query)

            # Enrich data
            message_data = enrich_message_and_publish_message(
                monitoring_response, message_data["controller_dict"],)

        except Exception as e:
            logging.error(f"Error processing message: {e}")
        finally:
            message.ack()

    # Start the subscription
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
    logging.info(f"Listening for messages on {subscription_path}...")

    # Keep the subscriber running
    with subscriber:
        try:
            streaming_pull_future.result()
        except KeyboardInterrupt:
            streaming_pull_future.cancel()

def enrich_message_and_publish_message(monitoring_data, replica_lookup):

    for item in monitoring_data.get("timeSeries", []):
        point = get_first_point(item)

        # Extract controller name/type for lookup
        system_labels = item.get("metadata", {}).get("systemLabels", {})
        controller_name = system_labels.get("top_level_controller_name")
        controller_type = system_labels.get("top_level_controller_type")

        # Lookup replicas
        replicas = replica_lookup.get(f"{controller_name}|{controller_type}")

        metric_type = item.get("metric", {}).get("type")

        double_value = get_value_from_point(point, "doubleValue")
        int64_value = get_value_from_point(point, "int64Value")

        value, units = process_metric_value(metric_type, double_value, int64_value)

        message = {
            "metric": item.get("metric", {}).get("type"),
            **item.get("resource", {}).get("labels", {}),
            "startTime": point.get("interval", {}).get("startTime"),
            "endTime": point.get("interval", {}).get("endTime"),
            "value": str(value),
            "valueUnits": units,
            "replicas": str(replicas),
            "controller_name": controller_name,
            "controller_type": controller_type,
        }
    publish_to_pubsub(message)


def publish_to_pubsub(message):
    """
    Publishes a message with monitoring data to the destination Pub/Sub topic.

    Args:
        topic_name (str): Name of the destination Pub/Sub topic.
        message_data (dict): Monitoring API response to publish.

    Returns:
        None
    """
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, DESTINATION_PUBSUB_TOPIC_ID)

    # Encode each metric data point as JSON
    data = json.dumps(message, default=str).encode("utf-8")

    try:
        # Publish the individual message
        future = publisher.publish(topic_path, data=data)
        future.result()  # Block until publish is successful
        logging.info(f"Published metric data to {DESTINATION_PUBSUB_TOPIC_ID}: {data}")
    except Exception as e:
        logging.error(f"Error publishing metric data: {e}")
