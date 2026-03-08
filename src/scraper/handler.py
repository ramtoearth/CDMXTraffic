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
from datetime import datetime, timezone

from src.scraper.scraper import TOTAL_SOURCES, scrape_traffic_sources

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
