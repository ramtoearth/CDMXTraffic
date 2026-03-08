"""
Deduplication for traffic incidents.

Two incidents are considered duplicates when they share the same:
  - normalized location
  - incident type
  - 30-minute time bucket

Requirements:
  - 3.6: Remove duplicate incidents before returning to orchestrator
"""
import hashlib
import re
from typing import List

from src.shared.models import TrafficIncident


def create_incident_fingerprint(incident: TrafficIncident) -> str:
    """
    Create a stable hash fingerprint for an incident.

    Location is normalized (lowercase, no punctuation, collapsed whitespace).
    Timestamp is bucketed to 30-minute windows so near-duplicate reports match.
    """
    location_normalized = re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', '', incident.location.lower())).strip()
    bucket = incident.timestamp.replace(
        minute=(incident.timestamp.minute // 30) * 30,
        second=0,
        microsecond=0,
    )
    raw = f"{location_normalized}|{bucket.isoformat()}|{incident.type}"
    return hashlib.md5(raw.encode()).hexdigest()


def deduplicate_incidents(incidents: List[TrafficIncident]) -> List[TrafficIncident]:
    """
    Remove duplicate incidents using fingerprints. First-seen wins.
    Preserves original order of unique incidents.
    """
    seen: set = set()
    result: List[TrafficIncident] = []
    for incident in incidents:
        fp = create_incident_fingerprint(incident)
        if fp not in seen:
            seen.add(fp)
            result.append(incident)
    return result
