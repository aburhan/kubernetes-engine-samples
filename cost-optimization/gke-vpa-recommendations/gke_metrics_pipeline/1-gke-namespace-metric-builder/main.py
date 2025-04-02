import logging
from monitoring import call_cloud_monitoring_api
from process import process_monitoring_data
from config import LOGGING_CONFIG

# Configure logging
logging.basicConfig(**LOGGING_CONFIG)


def main():
    """
    Main function to call the Cloud Monitoring API and process data.
    """
    logging.info("Fetching data from Cloud Monitoring API...")
    monitoring_data = call_cloud_monitoring_api()

    if monitoring_data and "timeSeries" in monitoring_data:
        logging.info("Processing monitoring data...")
        process_monitoring_data(monitoring_data["timeSeries"])
    else:
        logging.warning("No time series data returned.")


if __name__ == "__main__":
    main()
