import json
import logging
from google.cloud import pubsub_v1
from google.api_core import gapic_v1
from config import PROJECT_ID, PUBSUB_TOPIC_ID, USER_AGENT


def publish_to_pubsub( message_data):
    """
    Publishes a message to a specified Pub/Sub topic.
    """
    client_info = gapic_v1.client_info.ClientInfo(
        user_agent=USER_AGENT
    )
    try:
        publisher = pubsub_v1.PublisherClient(
            client_info=client_info)
        topic_path = publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC_ID)

        data = json.dumps(message_data, default=str).encode("utf-8")
        future = publisher.publish(topic_path, data=data)
        future.result()

        logging.info(
            f"Published message to {PUBSUB_TOPIC_ID}:\
                \n {json.dumps(message_data, indent=2)}")
    except Exception as e:
        logging.error(f"Error publishing message to {PUBSUB_TOPIC_ID}: {e}")
