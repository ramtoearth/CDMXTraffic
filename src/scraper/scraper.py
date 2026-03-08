"""
Traffic source scrapers for CDMX.

Each source scraper is independent; failures are logged and swallowed so that
the remaining sources continue to run (Req 3.5).

Sources:
  - waze_cdmx  — OpenWeb Ninja Waze API for Mexico City

Requirements:
  - 3.1: Scrape traffic incidents from at least 2 sources
  - 3.4: Normalize incidents into a standard TrafficIncident format
  - 3.5: Single source failure must not abort the whole job
  - 10.2: Structured error log per failed source
"""
import logging
import os
from datetime import datetime, timezone
from typing import List, Tuple
from uuid import uuid4

import requests

from src.scraper.deduplication import deduplicate_incidents
from src.shared.models import TrafficIncident

logger = logging.getLogger(__name__)

SOURCES = [
    ("waze_cdmx", "_scrape_waze_cdmx"),
]

TOTAL_SOURCES = len(SOURCES)

# ── keyword maps ─────────────────────────────────────────────────────────────

_WAZE_TYPE_MAP = {
    "ACCIDENT": "accident",
    "HAZARD": "pothole",
    "HAZARD_ON_ROAD": "pothole",
    "HAZARD_ON_ROAD_CONSTRUCTION": "pothole",
    "HAZARD_ON_ROAD_LANE_CLOSED": "pothole",
    "HAZARD_ON_SHOULDER": "pothole",
    "ROAD_CLOSED": "protest",
    "JAM": "accident",
}


# ── public entry point ────────────────────────────────────────────────────────

def scrape_traffic_sources() -> List[TrafficIncident]:
    """
    Scrape all configured sources, deduplicate, and return the merged list.

    A source that raises any exception is counted as failed; remaining sources
    are still executed (Req 3.5).
    """
    all_incidents: List[TrafficIncident] = []
    sources_failed = 0

    source_fns = {
        "waze_cdmx": _scrape_waze_cdmx,
    }

    for source_name, scrape_fn in source_fns.items():
        try:
            incidents = scrape_fn()
            logger.info("[scraper] %s: %d incidents", source_name, len(incidents))
            all_incidents.extend(incidents)
        except Exception as exc:
            sources_failed += 1
            logger.error(
                "[scraper] source=%s status=failed error=%s",
                source_name,
                str(exc),
            )

    if sources_failed == TOTAL_SOURCES:
        logger.warning("[scraper] All sources failed — returning empty list")

    return deduplicate_incidents(all_incidents)


# ── Waze CDMX (OpenWeb Ninja API) ────────────────────────────────────────────

_WAZE_API_URL = "https://api.openwebninja.com/waze/alerts-and-jams"
# Mexico City bounding box
_CDMX_BOTTOM_LEFT = "19.2,-99.35"
_CDMX_TOP_RIGHT = "19.6,-98.95"


def _scrape_waze_cdmx() -> List[TrafficIncident]:
    """
    Scrape Waze traffic data for Mexico City using OpenWeb Ninja API.
    """
    api_key = os.environ.get("WAZE_API_KEY")
    if not api_key:
        raise ValueError("WAZE_API_KEY environment variable not set")

    params = {
        "bottom_left": _CDMX_BOTTOM_LEFT,
        "top_right": _CDMX_TOP_RIGHT,
        "max_alerts": 100,
        "max_jams": 50,
    }
    headers = {"x-api-key": api_key}

    resp = requests.get(_WAZE_API_URL, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "OK":
        raise ValueError(f"Waze API returned status: {data.get('status')}")

    incidents: List[TrafficIncident] = []
    
    # Process alerts
    for alert in data.get("data", {}).get("alerts", []):
        incident_type = _map_waze_type(alert.get("type"), alert.get("subtype"))
        location = _format_waze_location(alert)
        description = alert.get("description") or f"{alert.get('type')} at {location}"
        severity = _assign_waze_severity(alert)
        timestamp = _parse_waze_timestamp(alert.get("publish_datetime_utc"))
        
        coords: Tuple[float, float] | None = None
        if alert.get("latitude") and alert.get("longitude"):
            coords = (float(alert["latitude"]), float(alert["longitude"]))

        incidents.append(
            TrafficIncident(
                incident_id=str(uuid4()),
                type=incident_type,
                location=location,
                description=description,
                severity=severity,
                timestamp=timestamp,
                source="waze_cdmx",
                coordinates=coords,
            )
        )
    
    # Process jams (traffic congestion)
    for jam in data.get("data", {}).get("jams", []):
        if jam.get("level", 0) < 3:  # Only include moderate to severe jams
            continue
            
        location = _format_waze_jam_location(jam)
        description = f"Traffic jam - Level {jam.get('level')}, {jam.get('length_meters')}m, {jam.get('delay_seconds')}s delay"
        severity = "high" if jam.get("level", 0) >= 4 else "medium"
        timestamp = _parse_waze_timestamp(jam.get("publish_datetime_utc"))
        
        coords: Tuple[float, float] | None = None
        line_coords = jam.get("line_coordinates", [])
        if line_coords:
            # Use first coordinate as representative location
            coords = (float(line_coords[0]["lat"]), float(line_coords[0]["lon"]))

        incidents.append(
            TrafficIncident(
                incident_id=str(uuid4()),
                type="accident",  # Jams often indicate accidents
                location=location,
                description=description,
                severity=severity,
                timestamp=timestamp,
                source="waze_cdmx",
                coordinates=coords,
            )
        )

    return incidents


def _map_waze_type(alert_type: str, subtype: str | None) -> str:
    """Map Waze alert type to our incident type."""
    if subtype and subtype in _WAZE_TYPE_MAP:
        return _WAZE_TYPE_MAP[subtype]
    if alert_type in _WAZE_TYPE_MAP:
        return _WAZE_TYPE_MAP[alert_type]
    return "accident"  # default


def _format_waze_location(alert: dict) -> str:
    """Format location string from Waze alert."""
    parts = []
    if alert.get("street"):
        parts.append(alert["street"])
    if alert.get("city"):
        parts.append(alert["city"])
    elif alert.get("country"):
        parts.append(alert["country"])
    return ", ".join(parts) if parts else "CDMX"


def _format_waze_jam_location(jam: dict) -> str:
    """Format location string from Waze jam."""
    parts = []
    if jam.get("street"):
        parts.append(jam["street"])
    if jam.get("city"):
        parts.append(jam["city"])
    return ", ".join(parts) if parts else "CDMX"


def _assign_waze_severity(alert: dict) -> str:
    """Assign severity based on Waze alert data."""
    alert_type = alert.get("type", "")
    reliability = alert.get("alert_reliability", 0)
    
    if alert_type == "ACCIDENT":
        return "high"
    elif alert_type == "ROAD_CLOSED":
        return "high"
    elif reliability >= 8:
        return "medium"
    else:
        return "low"


def _parse_waze_timestamp(timestamp_str: str | None) -> datetime:
    """Parse Waze ISO timestamp."""
    if not timestamp_str:
        return datetime.now(tz=timezone.utc)
    try:
        # Waze uses ISO format: "2026-03-07T05:04:20.000Z"
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(tz=timezone.utc)
