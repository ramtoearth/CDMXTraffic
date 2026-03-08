"""
Scraper Lambda Handler

Scrapes traffic incidents from multiple CDMX sources, deduplicates them,
and returns a structured JSON response to the orchestrator.

Requirements:
  - 3.1: Collect incidents from at least 2 sources
  - 3.5: Single source failure must not abort the job
  - 3.7: Empty list is a valid return value
"""
import json
import logging
import os
from datetime import datetime, timezone

import boto3

from src.scraper.scraper import TOTAL_SOURCES, scrape_traffic_sources

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_secrets_client = boto3.client("secretsmanager")


def lambda_handler(event, context):
    """
    Entry point for the Scraper Lambda.

    Returns:
        {
            "statusCode": 200,
            "body": JSON string with keys:
                - incidents:       list of serialized TrafficIncident dicts
                - scraped_at:      ISO 8601 timestamp
                - sources_count:   number of sources attempted
                - incidents_count: number of deduplicated incidents returned
        }
    """
    logger.info("[handler] Starting traffic data scraping")

    # Load Waze API key from Secrets Manager
    secret_arn = os.environ.get("WAZE_API_KEY_SECRET")
    if secret_arn:
        try:
            response = _secrets_client.get_secret_value(SecretId=secret_arn)
            secret_data = json.loads(response["SecretString"])
            os.environ["WAZE_API_KEY"] = secret_data["api_key"]
            logger.info("[handler] Waze API key loaded from Secrets Manager")
        except Exception as e:
            logger.error("[handler] Failed to load Waze API key: %s", str(e))

    incidents = scrape_traffic_sources()
    scraped_at = datetime.now(tz=timezone.utc)

    logger.info(
        "[handler] Scraping complete: incidents=%d sources=%d",
        len(incidents),
        TOTAL_SOURCES,
    )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "incidents": [i.to_dict() for i in incidents],
                "scraped_at": scraped_at.isoformat(),
                "sources_count": TOTAL_SOURCES,
                "incidents_count": len(incidents),
            }
        ),
    }
