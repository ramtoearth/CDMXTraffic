"""
Traffic source scrapers for CDMX.

Each source scraper is independent; failures are logged and swallowed so that
the remaining sources continue to run (Req 3.5).

Sources:
  - ovial_cdmx  — OVIAL CDMX RSS / HTML feed
  - c5_cdmx     — C5 CDMX open-data JSON endpoint

Requirements:
  - 3.1: Scrape traffic incidents from at least 2 sources
  - 3.4: Normalize incidents into a standard TrafficIncident format
  - 3.5: Single source failure must not abort the whole job
  - 10.2: Structured error log per failed source
"""
import logging
import re
from datetime import datetime, timezone
from typing import List, Tuple
from uuid import uuid4

import requests
from bs4 import BeautifulSoup

from src.scraper.deduplication import deduplicate_incidents
from src.shared.models import TrafficIncident

logger = logging.getLogger(__name__)

SOURCES = [
    ("ovial_cdmx", "_scrape_ovial_cdmx"),
    ("c5_cdmx", "_scrape_c5_cdmx"),
]

TOTAL_SOURCES = len(SOURCES)

# ── keyword maps ─────────────────────────────────────────────────────────────

_ACCIDENT_KEYWORDS = [
    "accidente", "choque", "colisión", "atropello", "volcadura", "derrape",
    "accident", "crash", "collision",
]
_POTHOLE_KEYWORDS = [
    "bache", "hundimiento", "socavón", "pavimento", "pothole", "sinkhole",
]
_PROTEST_KEYWORDS = [
    "manifestación", "marcha", "bloqueo", "protesta", "cierre", "corte de calle",
    "protest", "demonstration", "blockade",
]

_HIGH_KEYWORDS = [
    "volcadura", "atropello", "múltiple", "graves", "fallecido", "muerto",
    "sinkhole", "socavón",
]
_LOW_KEYWORDS = ["leve", "menor", "pequeño", "bache", "pothole"]


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
        "ovial_cdmx": _scrape_ovial_cdmx,
        "c5_cdmx": _scrape_c5_cdmx,
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


# ── OVIAL CDMX ────────────────────────────────────────────────────────────────

_OVIAL_RSS_URL = "https://ovial.cdmx.gob.mx/incidentes_viales/rss"
_OVIAL_HTML_URL = "https://ovial.cdmx.gob.mx/incidentes_viales"


def _scrape_ovial_cdmx() -> List[TrafficIncident]:
    """
    Scrape OVIAL CDMX — tries RSS first, falls back to HTML table.
    """
    try:
        return _scrape_ovial_rss()
    except Exception:
        return _scrape_ovial_html()


def _scrape_ovial_rss() -> List[TrafficIncident]:
    resp = requests.get(_OVIAL_RSS_URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "xml")
    items = soup.find_all("item")
    if not items:
        raise ValueError("No RSS items found")

    incidents: List[TrafficIncident] = []
    for item in items:
        title = _text(item, "title")
        description = _text(item, "description") or title
        location = _extract_location(title) or title
        pub_date = _parse_rss_date(_text(item, "pubDate"))
        incident_type = _classify_incident_type(f"{title} {description}")
        severity = _assign_severity(incident_type, description)
        coords = _extract_coordinates(item)

        incidents.append(
            TrafficIncident(
                incident_id=str(uuid4()),
                type=incident_type,
                location=location,
                description=description or title,
                severity=severity,
                timestamp=pub_date,
                source="ovial_cdmx",
                coordinates=coords,
            )
        )
    return incidents


def _scrape_ovial_html() -> List[TrafficIncident]:
    resp = requests.get(_OVIAL_HTML_URL, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    incidents: List[TrafficIncident] = []
    rows = soup.select("table tbody tr") or soup.select(".incidente")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        location = cells[0].get_text(strip=True)
        description = cells[1].get_text(strip=True) if len(cells) > 1 else location
        incident_type = _classify_incident_type(f"{location} {description}")
        severity = _assign_severity(incident_type, description)

        incidents.append(
            TrafficIncident(
                incident_id=str(uuid4()),
                type=incident_type,
                location=location or "CDMX",
                description=description or location,
                severity=severity,
                timestamp=datetime.now(tz=timezone.utc),
                source="ovial_cdmx",
                coordinates=None,
            )
        )
    return incidents


# ── C5 CDMX ───────────────────────────────────────────────────────────────────

_C5_URL = (
    "https://datos.cdmx.gob.mx/api/3/action/datastore_search"
    "?resource_id=d360b2b1-ab71-4187-8d73-2f8dab13dcf1&limit=100"
)


def _scrape_c5_cdmx() -> List[TrafficIncident]:
    """
    Scrape C5 CDMX open-data JSON endpoint (CKAN datastore).
    """
    resp = requests.get(_C5_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    records = data.get("result", {}).get("records", [])
    if not records:
        logger.info("[scraper] c5_cdmx: no records returned")
        return []

    incidents: List[TrafficIncident] = []
    for rec in records:
        description = (
            rec.get("TIPIFICACION_INCIDENTE")
            or rec.get("TIPO_INCIDENTE")
            or rec.get("descripcion")
            or ""
        )
        location = (
            rec.get("ALCALDIA")
            or rec.get("COLONIA")
            or rec.get("alcaldia")
            or "CDMX"
        )
        colonia = rec.get("COLONIA") or rec.get("colonia") or ""
        if colonia and colonia not in location:
            location = f"{colonia}, {location}"

        raw_ts = (
            rec.get("FECHA_CREACION")
            or rec.get("fecha_creacion")
            or rec.get("FECHA")
            or ""
        )
        timestamp = _parse_c5_date(raw_ts)

        lat = _safe_float(rec.get("LATITUD") or rec.get("latitud"))
        lon = _safe_float(rec.get("LONGITUD") or rec.get("longitud"))
        coords: Tuple[float, float] | None = (lat, lon) if lat and lon else None

        incident_type = _classify_incident_type(description)
        severity = _assign_severity(incident_type, description)

        incidents.append(
            TrafficIncident(
                incident_id=str(uuid4()),
                type=incident_type,
                location=location,
                description=description or location,
                severity=severity,
                timestamp=timestamp,
                source="c5_cdmx",
                coordinates=coords,
            )
        )
    return incidents


# ── classifiers ───────────────────────────────────────────────────────────────

def _classify_incident_type(text: str) -> str:
    """Keyword-based classification. Returns 'accident' | 'pothole' | 'protest'."""
    lower = text.lower()
    for kw in _PROTEST_KEYWORDS:
        if kw in lower:
            return "protest"
    for kw in _POTHOLE_KEYWORDS:
        if kw in lower:
            return "pothole"
    for kw in _ACCIDENT_KEYWORDS:
        if kw in lower:
            return "accident"
    return "accident"  # default


def _assign_severity(incident_type: str, description: str) -> str:
    """Rule-based severity assignment. Returns 'low' | 'medium' | 'high'."""
    lower = description.lower()
    for kw in _HIGH_KEYWORDS:
        if kw in lower:
            return "high"
    if incident_type == "pothole":
        for kw in _LOW_KEYWORDS:
            if kw in lower:
                return "low"
        return "low"
    if incident_type == "protest":
        return "medium"
    for kw in _LOW_KEYWORDS:
        if kw in lower:
            return "low"
    return "medium"


# ── helpers ───────────────────────────────────────────────────────────────────

def _text(tag, name: str) -> str:
    el = tag.find(name)
    return el.get_text(strip=True) if el else ""


def _extract_location(text: str) -> str:
    """Try to pull a street/colonia reference from a title string."""
    match = re.search(r'(?:en|calle|av\.?|avenida)\s+([^,.]+)', text, re.IGNORECASE)
    return match.group(1).strip() if match else text


def _extract_coordinates(item) -> "Tuple[float, float] | None":
    """Try to read geo:lat / geo:long from an RSS item."""
    lat_tag = item.find("geo:lat") or item.find("lat")
    lon_tag = item.find("geo:long") or item.find("lon") or item.find("long")
    lat = _safe_float(lat_tag.get_text(strip=True) if lat_tag else None)
    lon = _safe_float(lon_tag.get_text(strip=True) if lon_tag else None)
    return (lat, lon) if lat and lon else None


def _safe_float(value) -> "float | None":
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_rss_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now(tz=timezone.utc)
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(tz=timezone.utc)


def _parse_c5_date(date_str: str) -> datetime:
    if not date_str:
        return datetime.now(tz=timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.now(tz=timezone.utc)
