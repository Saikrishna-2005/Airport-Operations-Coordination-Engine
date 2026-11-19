"""Offline integration checks for flight-tool delegation."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch, Mock
import httpx
from app.research_agent.tools import flight_tool as ft
from app.research_agent.tools.opensky_dispatcher import DispatchError

class FlightToolTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock(spec=httpx.Client)
        self.airport = SimpleNamespace(iata='DEL', icao='VIDP', latitude=28.56, longitude=77.1, name='Delhi')
        for name, value in [('get_airport', self.airport), ('dispatch', httpx.Response(200,json={'states':[]}))]:
            p=patch.object(ft,name,return_value=value); setattr(self,name,p.start()); self.addCleanup(p.stop)
        self.addCleanup(self.client.get.assert_not_called)
        self.addCleanup(self.client.post.assert_not_called)

    def test_synthetic_lookup(self):
        self.assertEqual(ft.get_flights('DEL',['AIC101'],[],mode='synthetic',client=self.client).flights[0].status.value,'found')
        self.dispatch.assert_not_called()

    def test_synthetic_area(self):
        self.assertEqual(ft.get_aircraft_in_area('DEL',mode='synthetic',client=self.client)['provider'],'synthetic')
        self.dispatch.assert_not_called()

    def test_invalid_mode(self):
        self.assertEqual(ft.get_flights('DEL',['AIC101'],[],mode='invalid',client=self.client).errors[0].code,'INVALID_DATA_MODE')
        self.dispatch.assert_not_called()

    def test_live_lookup(self):
        result=ft.get_flights('DEL',['AIC101'],[],mode='live',client=self.client)
        self.assertEqual(result.flights[0].status.value,'not_found')
        self.dispatch.assert_called_once_with(self.client,ft.OPENSKY_STATES_URL,{'lamin':28.06,'lamax':29.06,'lomin':76.6,'lomax':77.6})

    def test_live_area(self):
        self.assertEqual(ft.get_aircraft_in_area('DEL',mode='live',client=self.client)['status'],'success')
        self.dispatch.assert_called_once()

    def test_lookup_error(self):
        self.dispatch.side_effect=DispatchError('BUDGET_EXHAUSTED','blocked')
        self.assertEqual(ft.get_flights('DEL',['AIC101'],[],mode='live',client=self.client).errors[0].code,'BUDGET_EXHAUSTED')
        self.dispatch.assert_called_once()

    def test_area_error(self):
        self.dispatch.side_effect=DispatchError('PENDING_REQUEST','blocked')
        self.assertEqual(ft.get_aircraft_in_area('DEL',mode='live',client=self.client)['error']['code'],'PENDING_REQUEST')
        self.dispatch.assert_called_once()

    def test_history_delegation(self):
        self.dispatch.return_value=httpx.Response(200,json=[])
        for fn,args,path in [(ft.get_arrivals_by_airport,('DEL',100,200),'arrival'),(ft.get_departures_by_airport,('DEL',100,200),'departure'),(ft.get_flights_by_aircraft,('abcdef',100,200),'aircraft'),(ft.get_flights_from_interval,(100,200),'all')]:
            with self.subTest(path=path):
                self.dispatch.reset_mock()
                self.assertEqual(fn(*args,client=self.client)['status'],'success')
                self.dispatch.assert_called_once()
                self.assertEqual(self.dispatch.call_args.args[1],ft.OPENSKY_FLIGHTS_URL+'/'+path)

    def test_track_delegation(self):
        self.dispatch.return_value=httpx.Response(200,json={'path':[]})
        self.assertEqual(ft.get_track_by_aircraft('abcdef',0,client=self.client)['status'],'success')
        self.dispatch.assert_called_once_with(self.client,ft.OPENSKY_TRACKS_URL,{'icao24':'abcdef','time':0})

    def test_history_error(self):
        self.dispatch.side_effect=DispatchError('LIVE_DISABLED','blocked')
        self.assertEqual(ft.get_arrivals_by_airport('DEL',100,200,client=self.client)['error']['code'],'LIVE_DISABLED')
        self.dispatch.assert_called_once()
