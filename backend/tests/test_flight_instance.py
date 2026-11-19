"""Offline flight-instance verification tests."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from app.research_agent.tools.flight_instance import (
    FlightInstanceEvidence, FlightInstanceStatus as Status, verify_flight_instance,
)


class FlightInstanceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 18, 15, tzinfo=timezone.utc)
        self.operational = FlightInstanceEvidence(
            provider='cirium', icao24='ab349f', callsign='AAL292',
            origin='KJFK', destination='VIDP',
            actual_runway_departure=self.now-timedelta(hours=12),
            independently_observed=True)
        self.tracking = replace(self.operational, provider='opensky',
                                observed_at=self.now-timedelta(seconds=30))

    def check(self, status, reason, **changes):
        result = verify_flight_instance(self.operational,
                    replace(self.tracking, **changes), now=self.now)
        self.assertEqual(result.status, status)
        self.assertIn(reason, result.reasons)

    def test_01_matching_evidence(self):
        self.check(Status.unverified, 'unique_flight_instance_linkage_required')

    def test_02_icao24_mismatch(self):
        self.check(Status.mismatch, 'icao24', icao24='abcdef')

    def test_03_callsign_mismatch(self):
        self.check(Status.mismatch, 'callsign', callsign='AAL293')

    def test_04_origin_mismatch(self):
        self.check(Status.mismatch, 'origin', origin='KLAX')

    def test_05_destination_mismatch(self):
        self.check(Status.mismatch, 'destination', destination='VABB')

    def test_06_departure_mismatch(self):
        self.check(Status.mismatch, 'actual_runway_departure',
                   actual_runway_departure=self.tracking.actual_runway_departure+timedelta(seconds=301))

    def test_07_stale_tracking(self):
        self.check(Status.stale, 'tracking_observation_outside_window',
                   observed_at=self.now-timedelta(seconds=121))

    def test_08_future_tracking(self):
        self.check(Status.stale, 'tracking_observation_outside_window',
                   observed_at=self.now+timedelta(seconds=1))

    def test_09_missing_icao24(self):
        self.check(Status.unverified, 'icao24', icao24=None)

    def test_10_missing_departure(self):
        self.check(Status.unverified, 'actual_runway_departure', actual_runway_departure=None)

    def test_11_same_provider(self):
        self.check(Status.unverified, 'independent_provider_evidence', provider=' CIRIUM ')

    def test_12_non_independent(self):
        self.check(Status.unverified, 'independent_provider_evidence', independently_observed=False)

    def test_13_missing_tracking_timestamp(self):
        self.check(Status.unverified, 'missing_tracking_timestamp', observed_at=None)

    def test_14_departure_after_observation(self):
        self.check(Status.mismatch, 'departure_after_observation', actual_runway_departure=self.now)

    def test_15_invalid_policy(self):
        for policy in ({'max_age_seconds': 121}, {'departure_tolerance_seconds': 301},
                       {'max_age_seconds': 0}, {'departure_tolerance_seconds': -1}):
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                verify_flight_instance(self.operational, self.tracking, now=self.now, **policy)


if __name__ == '__main__':
    unittest.main()
