import logging
from pubsub import consume_messages

from config import (
    PUBSUB_SUBSCRIPTION_ID,
    LOGGING_CONFIG,
)

# Configure logging
logging.basicConfig(**LOGGING_CONFIG)


def main():
    """
    Main function that consumes messages, processes queries,
    calls Cloud Monitoring API, and publishes results.
    """
    logging.info("Starting Pub/Sub consumer to process monitoring queries...")
    consume_messages(PUBSUB_SUBSCRIPTION_ID)


if __name__ == "__main__":
    main()
