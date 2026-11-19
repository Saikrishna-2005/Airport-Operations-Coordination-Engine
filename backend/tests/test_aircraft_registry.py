"""Offline tests: no provider calls or production registry writes."""
import csv
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timezone

from app.research_agent.tools import aircraft_registry as registry
from app.research_agent.tools import flight_integration as integration
from app.research_agent.schemas import DataMode, FlightLookupStatus, FlightResult, FlightOperationalData


class RegistryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / 'registry.db'
        source = Path(temp.name) / 'fixture.csv'
        with source.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(registry.COLUMNS), quotechar="'", quoting=csv.QUOTE_ALL)
            writer.writeheader()
            for reg, address in [('N123AB','abcdef'), ('N123AB','abcdef'), ('N456CD','123456'), ('N456CD','654321'), ('','abcdef'), ('N999ZZ','invalid')]:
                writer.writerow({'registration': reg, 'icao24': address})
        self.stats = registry.build_registry(source, self.db)

    def lookup(self, value):
        return registry.lookup_registration(value, self.db)

    def test_01_valid(self):
        self.assertEqual(self.lookup('N123AB')['candidates'], ['abcdef'])
        self.assertEqual(self.lookup('N123AB')['status'], 'candidate')

    def test_02_normalization(self):
        self.assertEqual(self.lookup(' n123-ab ')['candidates'], ['abcdef'])

    def test_03_unknown(self):
        self.assertEqual(self.lookup('N000ZZ')['status'], 'not_found')

    def test_04_invalid(self):
        self.assertEqual(self.lookup('!!!')['status'], 'invalid')

    def test_05_ambiguous(self):
        result = self.lookup('N456CD')
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(result['candidates'], ['123456','654321'])

    def test_06_missing_database(self):
        self.assertEqual(registry.lookup_registration('N123AB', self.db.with_name('missing.db'))['status'], 'unavailable')

    def test_07_duplicates_and_invalid_rows(self):
        self.assertEqual(self.stats['accepted_rows'], 4)
        self.assertEqual(self.stats['skipped_rows'], 2)
        self.assertEqual(len(self.lookup('N123AB')['candidates']), 1)


class IntegrationRegistryTests(unittest.TestCase):
    def diagnostic(self, address='abcdef', registration='N123AB'):
        operational = SimpleNamespace(data={'aircraft_registration': registration})
        tracking = SimpleNamespace(status=FlightLookupStatus.found, data={'icao24': address})
        return integration._registry_diagnostics(operational, tracking)

    @patch.object(integration, 'lookup_registration', return_value={'status':'candidate','candidates':['abcdef']})
    def test_08_match(self, lookup):
        self.assertEqual(self.diagnostic()['comparison'], 'candidate_match')
        lookup.assert_called_once_with('N123AB')

    @patch.object(integration, 'lookup_registration', return_value={'status':'candidate','candidates':['abcdef']})
    def test_09_mismatch(self, lookup):
        self.assertEqual(self.diagnostic('123456')['comparison'], 'candidate_mismatch')

    @patch.object(integration, 'lookup_registration')
    def test_10_missing_registration(self, lookup):
        self.assertEqual(self.diagnostic(registration=None)['status'], 'missing_registration')
        lookup.assert_not_called()

    @patch.object(integration, 'lookup_registration', side_effect=sqlite3.DatabaseError('fixture failure'))
    def test_11_failure_isolation(self, lookup):
        self.assertEqual(self.diagnostic()['status'], 'unavailable')

    @patch.object(integration, 'lookup_registration', return_value={'status':'candidate','candidates':['abcdef']})
    def test_12_candidate_does_not_authorize_fusion(self, lookup):
        now = datetime.now(timezone.utc)
        operational = FlightResult(requested_identifier='AA292', status=FlightLookupStatus.found, provider='cirium', data={'aircraft_registration':'N123AB'}, operational_data=FlightOperationalData(icao24=None))
        tracking = FlightResult(requested_identifier='AAL292', status=FlightLookupStatus.found, provider='opensky', data={'icao24':'abcdef','time_position':now.timestamp(),'latitude':28.5}, data_timestamp=now)
        result = integration._merge_flight('AA292', tracking, operational, [], DataMode.live)
        self.assertEqual(result.data['aircraft_registry']['comparison'], 'candidate_match')
        self.assertNotIn('latitude', result.data)
        self.assertNotIn('icao24', result.data)
        self.assertIsNone(result.operational_data.icao24)
        self.assertIn('verified_aircraft_identity', result.missing_fields)
        self.assertNotIn('opensky', result.providers)


if __name__ == '__main__':
    unittest.main()
