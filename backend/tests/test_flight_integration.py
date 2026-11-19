"""Offline integration contract tests. Run from backend with unittest discovery."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from app.research_agent.schemas import (
    DataMode, ErrorInfo, FlightLookupStatus, FlightResult,
    FlightOperationalData, FlightFieldSource, SourceRecord,
)
from app.research_agent.tools import flight_integration as integration
from app.research_agent.tools.flight_tool import FlightToolOutput


class FlightIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.tracking_source = SourceRecord(source_id='test-os', provider='opensky', data_type='synthetic', retrieved_at=self.now)
        self.operational_source = SourceRecord(source_id='test-ci', provider='cirium', data_type='synthetic', retrieved_at=self.now)
        self.tracking = FlightResult(requested_identifier='AIC101', status=FlightLookupStatus.found, provider='opensky', source_id='test-os', data_timestamp=self.now, data={'icao24': '8005b1', 'on_ground': False, 'velocity': 140, 'time_position': self.now.timestamp()})
        self.operational = FlightResult(requested_identifier='AI101', status=FlightLookupStatus.found, provider='cirium-synthetic', source_id='test-ci', data_timestamp=self.now, operational_data=FlightOperationalData(flight_number='AI101', callsign='AIC101', icao24='8005b1', status='delayed', arrival_gate='G12', arrival_delay_minutes=30), field_sources={'operational_data.arrival_gate': FlightFieldSource(provider='cirium-synthetic', source_id='test-ci', data_timestamp=self.now)})

    def outage(self, provider, identifier=None):
        return FlightToolOutput(errors=[ErrorInfo(tool=provider, code='TEST_OUTAGE', message='Simulated outage', retryable=True)], flights=[FlightResult(requested_identifier=identifier, status=FlightLookupStatus.error, provider=provider)] if identifier else [])

    def run_case(self, tracking=None, operational=None, identifier='AI101', mode=DataMode.synthetic, tracking_exception=None, operational_exception=None):
        if tracking is None:
            tracking = FlightToolOutput(flights=[self.tracking], sources=[self.tracking_source])
        if operational is None:
            operational = FlightToolOutput(flights=[self.operational], sources=[self.operational_source])
        with patch.object(integration, 'get_flights', return_value=tracking, side_effect=tracking_exception) as os_mock, patch.object(integration, 'get_cirium_flights', return_value=operational, side_effect=operational_exception):
            result = integration.get_integrated_flights('DEL', [identifier], ['aircraft tracking', 'gate assignments', 'flight status'], mode=mode, integration_enabled=True)
            self.assertEqual(len(result.flights), 1)
            return result, os_mock

    def test_01_both_available(self):
        result, mock = self.run_case()
        f = result.flights[0]
        self.assertEqual(f.provider, 'multi-provider')
        self.assertEqual(f.data['velocity'], 140)
        self.assertEqual(f.operational_data.arrival_gate, 'G12')
        self.assertEqual(set(f.source_ids), {'test-os', 'test-ci'})
        self.assertEqual({s.source_id for s in result.sources}, {'test-os', 'test-ci'})
        self.assertEqual(f.field_sources['data.velocity'].source_id, 'test-os')
        self.assertEqual(f.field_sources['operational_data.arrival_gate'].source_id, 'test-ci')
        self.assertFalse(result.errors)
        self.assertEqual(mock.call_args.kwargs['flight_identifiers'], ['AIC101'])
        self.assertEqual(mock.call_args.kwargs['research_requirements'], ['aircraft tracking'])

    def test_02_identity_mismatch(self):
        self.tracking.data['icao24'] = 'abcdef'
        result, _ = self.run_case()
        f = result.flights[0]
        self.assertEqual(f.data, {})
        self.assertIsNotNone(f.operational_data)
        self.assertEqual(len(f.conflicts), 1)
        self.assertEqual(f.conflicts[0].field_name, 'icao24')
        self.assertFalse(f.conflicts[0].resolved)
        self.assertEqual(set(f.source_ids), {'test-os', 'test-ci'})
        self.assertIn('aircraft_tracking', f.missing_fields)

    def test_03_opensky_outage(self):
        result, _ = self.run_case(tracking=self.outage('opensky', 'AIC101'))
        f = result.flights[0]
        self.assertEqual(f.status, FlightLookupStatus.found)
        self.assertIsNotNone(f.operational_data)
        self.assertFalse(f.data)
        self.assertEqual(len(result.errors), 1)

    def test_04_cirium_outage_known_callsign(self):
        result, _ = self.run_case(operational=self.outage('cirium', 'AIC101'), identifier='AIC101')
        f = result.flights[0]
        self.assertEqual(f.status, FlightLookupStatus.found)
        self.assertTrue(f.data)
        self.assertIsNone(f.operational_data)
        self.assertIn('operational_data.status', f.missing_fields)
        self.assertEqual(len(result.errors), 1)

    def test_05_both_outages_with_records(self):
        result, _ = self.run_case(tracking=self.outage('opensky', 'AI101'), operational=self.outage('cirium', 'AI101'))
        self.assertEqual(result.flights[0].status, FlightLookupStatus.error)
        self.assertEqual(len(result.errors), 2)

    def test_06_stale_tracking(self):
        self.tracking.data['time_position'] = self.now.timestamp() - 300
        result, _ = self.run_case(mode=DataMode.live)
        f = result.flights[0]
        self.assertFalse(f.data)
        self.assertIn('fresh_tracking_data', f.missing_fields)
        self.assertIsNotNone(f.operational_data)

    def test_07_missing_operational_fields(self):
        result, _ = self.run_case()
        f = result.flights[0]
        self.assertIn('operational_data.departure_gate', f.missing_fields)
        self.assertNotIn('operational_data.arrival_gate', f.missing_fields)

    def test_08_cirium_exception_isolated(self):
        result, _ = self.run_case(identifier='AIC101', operational_exception=RuntimeError('Mock Cirium exception'))
        self.assertTrue(result.flights[0].data)
        self.assertIsNone(result.flights[0].operational_data)
        self.assertTrue(result.errors)

    def test_09_opensky_exception_isolated(self):
        result, _ = self.run_case(tracking_exception=RuntimeError('Mock OpenSky exception'))
        self.assertIsNotNone(result.flights[0].operational_data)
        self.assertFalse(result.flights[0].data)
        self.assertTrue(result.errors)

    def test_10_both_outages_without_records(self):
        result, _ = self.run_case(tracking=self.outage('opensky'), operational=self.outage('cirium'))
        self.assertEqual(result.flights[0].status, FlightLookupStatus.error)
        self.assertEqual(len(result.errors), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
