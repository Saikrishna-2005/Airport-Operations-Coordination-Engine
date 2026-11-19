"""Offline FastAPI route checks; authentication dependency overridden only in tests."""
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import flights as routes

class OpenSkyRouteTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI(); app.include_router(routes.router)
        app.dependency_overrides[routes.get_current_user]=lambda: {'role':'admin'}
        self.client=TestClient(app); self.addCleanup(self.client.close)
        p=patch.object(routes.research_settings,'DATA_MODE','synthetic'); p.start(); self.addCleanup(p.stop)
        self.mocks={}
        for name in ('get_aircraft_in_area','get_arrivals_by_airport','get_departures_by_airport','get_flights_by_aircraft','get_flights_from_interval','get_track_by_aircraft'):
            p=patch.object(routes,name,return_value={'status':'success'}); self.mocks[name]=p.start(); self.addCleanup(p.stop)

    def test_override_blocked(self):
        self.assertEqual(self.client.get('/api/flights/live?mode=live').status_code,403)
        self.mocks['get_aircraft_in_area'].assert_not_called()

    def test_default_synthetic(self):
        self.assertEqual(self.client.get('/api/flights/live').status_code,200)
        self.assertEqual(self.mocks['get_aircraft_in_area'].call_args.kwargs['mode'],'synthetic')

    def test_history_blocked(self):
        for path,name in [('history/arrivals?airport=DEL&begin=100&end=200','get_arrivals_by_airport'),('history/departures?airport=DEL&begin=100&end=200','get_departures_by_airport'),('history/aircraft/abcdef?begin=100&end=200','get_flights_by_aircraft'),('history/interval?begin=100&end=200','get_flights_from_interval'),('tracks/abcdef','get_track_by_aircraft')]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get('/api/flights/'+path).status_code,503)
                self.mocks[name].assert_not_called()

    def test_live_default(self):
        routes.research_settings.DATA_MODE='live'
        self.assertEqual(self.client.get('/api/flights/live').status_code,200)
        self.assertEqual(self.mocks['get_aircraft_in_area'].call_args.kwargs['mode'],'live')

    def test_live_history(self):
        routes.research_settings.DATA_MODE='live'
        self.assertEqual(self.client.get('/api/flights/history/arrivals?airport=DEL&begin=100&end=200').status_code,200)
        self.mocks['get_arrivals_by_airport'].assert_called_once_with('DEL',100,200)

    def test_quota_errors(self):
        routes.research_settings.DATA_MODE='live'
        for code,status in [('BUDGET_EXHAUSTED',429),('RATE_LIMITED',429),('PENDING_REQUEST',503),('QUOTA_UNAVAILABLE',503)]:
            with self.subTest(code=code):
                self.mocks['get_aircraft_in_area'].return_value={'status':'error','error':{'code':code}}
                self.assertEqual(self.client.get('/api/flights/live').status_code,status)
                self.mocks['get_arrivals_by_airport'].return_value={'status':'error','error':{'code':code}}
                self.assertEqual(self.client.get('/api/flights/history/arrivals?airport=DEL&begin=100&end=200').status_code,status)
