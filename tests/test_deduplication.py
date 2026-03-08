"""
Property-style tests for the deduplication module.

Properties verified:
  1. Idempotency  — deduplicate(deduplicate(L)) == deduplicate(L)
  2. Subset       — every item in result was in the original input
  3. Uniqueness   — all fingerprints in the result are distinct
  4. Single copy  — identical incidents collapse to exactly 1
  5. No loss      — fully distinct incidents are all preserved
"""
import unittest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.scraper.deduplication import (
    create_incident_fingerprint,
    deduplicate_incidents,
)
from src.shared.models import TrafficIncident


# ── helpers ───────────────────────────────────────────────────────────────────

_BASE_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make(
    location="Av. Insurgentes Norte 100",
    incident_type="accident",
    severity="medium",
    description="choque vehicular",
    timestamp=None,
    source="test",
    offset_minutes=0,
) -> TrafficIncident:
    ts = (timestamp or _BASE_TS) + timedelta(minutes=offset_minutes)
    return TrafficIncident(
        incident_id=str(uuid4()),
        type=incident_type,
        location=location,
        description=description,
        severity=severity,
        timestamp=ts,
        source=source,
        coordinates=None,
    )


def _fingerprints(incidents):
    return [create_incident_fingerprint(i) for i in incidents]


# ── test cases ────────────────────────────────────────────────────────────────

class TestDeduplication(unittest.TestCase):

    # Property 1: idempotency
    def test_idempotency_no_duplicates(self):
        incidents = [_make(offset_minutes=i * 60) for i in range(5)]
        once = deduplicate_incidents(incidents)
        twice = deduplicate_incidents(once)
        self.assertEqual(_fingerprints(once), _fingerprints(twice))

    def test_idempotency_with_duplicates(self):
        base = _make()
        incidents = [base, _make(), _make(), base]
        once = deduplicate_incidents(incidents)
        twice = deduplicate_incidents(once)
        self.assertEqual(_fingerprints(once), _fingerprints(twice))

    # Property 2: result ⊆ input
    def test_result_is_subset_of_input(self):
        incidents = [_make(offset_minutes=i * 45) for i in range(6)]
        result = deduplicate_incidents(incidents)
        fp_input = set(_fingerprints(incidents))
        for incident in result:
            self.assertIn(create_incident_fingerprint(incident), fp_input)

    # Property 3: no fingerprint duplicates in result
    def test_no_duplicate_fingerprints_in_result(self):
        i1 = _make(location="Calle A")
        i2 = _make(location="Calle A")   # same location + bucket → duplicate
        i3 = _make(location="Calle B", offset_minutes=120)
        result = deduplicate_incidents([i1, i2, i3])
        fps = _fingerprints(result)
        self.assertEqual(len(fps), len(set(fps)))

    # Property 4: identical incidents → exactly 1 in result
    def test_identical_incidents_collapse_to_one(self):
        base = _make()
        duplicates = [_make() for _ in range(5)]  # same fingerprint
        result = deduplicate_incidents(duplicates)
        self.assertEqual(len(result), 1)

    # Property 5: fully distinct incidents → all preserved
    def test_distinct_incidents_all_preserved(self):
        incidents = [
            _make(location="Loc A", incident_type="accident", offset_minutes=0),
            _make(location="Loc B", incident_type="pothole", offset_minutes=60),
            _make(location="Loc C", incident_type="protest", offset_minutes=120),
            _make(location="Loc A", incident_type="accident", offset_minutes=180),
        ]
        result = deduplicate_incidents(incidents)
        self.assertEqual(len(result), len(incidents))

    # First-seen wins (order preservation)
    def test_first_seen_wins(self):
        first = _make(description="first occurrence")
        second = _make(description="second occurrence")  # same fingerprint as first
        result = deduplicate_incidents([first, second])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].description, "first occurrence")

    # Empty input
    def test_empty_input_returns_empty(self):
        self.assertEqual(deduplicate_incidents([]), [])

    # Single incident
    def test_single_incident_returned_unchanged(self):
        incident = _make()
        result = deduplicate_incidents([incident])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].incident_id, incident.incident_id)

    # Time bucketing: incidents within same 30-min window are duplicates
    def test_same_30min_bucket_are_duplicates(self):
        i1 = _make(offset_minutes=0)   # 12:00
        i2 = _make(offset_minutes=20)  # 12:20 → same bucket (12:00)
        result = deduplicate_incidents([i1, i2])
        self.assertEqual(len(result), 1)

    def test_different_30min_buckets_are_distinct(self):
        i1 = _make(offset_minutes=0)   # 12:00
        i2 = _make(offset_minutes=31)  # 12:31 → next bucket (12:30)
        result = deduplicate_incidents([i1, i2])
        self.assertEqual(len(result), 2)

    # Location normalization: punctuation/case differences → same fingerprint
    def test_location_normalization_collapses_duplicates(self):
        i1 = _make(location="Av. Insurgentes Norte, 100")
        i2 = _make(location="av insurgentes norte 100")
        result = deduplicate_incidents([i1, i2])
        self.assertEqual(len(result), 1)

    # Different types at same location/time are distinct
    def test_different_types_same_location_are_distinct(self):
        i1 = _make(location="Loc X", incident_type="accident")
        i2 = _make(location="Loc X", incident_type="protest")
        result = deduplicate_incidents([i1, i2])
        self.assertEqual(len(result), 2)


class TestCreateIncidentFingerprint(unittest.TestCase):

    def test_same_incident_same_fingerprint(self):
        i1 = _make()
        i2 = _make()
        self.assertEqual(
            create_incident_fingerprint(i1),
            create_incident_fingerprint(i2),
        )

    def test_different_location_different_fingerprint(self):
        i1 = _make(location="Loc A")
        i2 = _make(location="Loc B")
        self.assertNotEqual(
            create_incident_fingerprint(i1),
            create_incident_fingerprint(i2),
        )

    def test_fingerprint_is_hex_string(self):
        fp = create_incident_fingerprint(_make())
        self.assertRegex(fp, r'^[0-9a-f]{32}$')


if __name__ == "__main__":
    unittest.main()
