from datetime import datetime,timezone
from unittest.mock import patch
from copy import deepcopy
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APITestCase
from routing.api.views import get_services
from routing.api.limits import reset_limits
from routing.tests.test_api import INPUT
class DemoEndpointTests(APITestCase):
    def setUp(self):
        cache.clear();get_services.cache_clear();reset_limits()
        self.clock=patch('routing.api.views.get_current_time',return_value=datetime(2026,10,13,12,tzinfo=timezone.utc));self.clock.start();self.addCleanup(self.clock.stop)
    def test_load_boundaries_and_all_checkpoint_spacings_through_the_api(self):
        for load,spacing,blocked,central_risk,count in (
            (30000,10,False,'high',16),
            (30000.01,25,True,'high',7),
            (40000,50,True,'high',4),
            (40000.01,10,True,'severe',16),
        ):
            with self.subTest(load=load,spacing=spacing):
                payload=dict(INPUT,destination={'longitude':-98,'latitude':40},load_lb=load,spacing_miles=spacing)
                response=self.client.post('/api/trips/evaluate/',payload,format='json')
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.data['load_lb'],load)
                self.assertEqual(response.data['spacing_miles'],spacing)
                self.assertEqual(len(response.data['routes']),3)
                north,central,_=response.data['routes']
                self.assertEqual(north['blocked'],blocked)
                self.assertEqual(len(north['checkpoints']),count)
                self.assertEqual(north['arrival_at'],'2026-10-13T15:00:00Z')
                self.assertEqual(central['checkpoints'][0]['wind_level'],central_risk)
                self.assertEqual(response.data['recommendation']['route_id'],'demo-south')
    @override_settings(PROVIDER_MODE='live',LIVE_ROUTING_PROVIDER='osrm')
    def test_live_endpoints_use_photon_osrm_without_credentials(self):
        self.assert_live_endpoints('https://router.project-osrm.org/')
    @override_settings(PROVIDER_MODE='live',LIVE_ROUTING_PROVIDER='valhalla')
    def test_live_endpoints_use_photon_valhalla_without_credentials(self):
        self.assert_live_endpoints('https://valhalla1.openstreetmap.de/')
    def assert_live_endpoints(self,routing_host):
        from routing.tests.test_photon import PAYLOAD as places
        from routing.tests.test_osrm import PAYLOAD as routes
        from routing.tests.test_open_meteo import PAYLOAD as weather
        calls=[]
        def transport(url,params):
            calls.append(url)
            self.assertNotIn('access_token',params)
            if url.startswith('https://photon.komoot.io/'):
                return deepcopy(places)
            if url.startswith(routing_host):
                return deepcopy(routes)
            self.assertEqual(url,'https://api.open-meteo.com/v1/forecast')
            values=[dict(deepcopy(weather),latitude=float(lat),longitude=float(lon)) for lat,lon in zip(params['latitude'].split(','),params['longitude'].split(','))]
            return values[0] if len(values)==1 else values
        with patch('routing.providers.http.request_json',side_effect=transport):
            candidate=self.client.get('/api/geocode/',{'q':'Example'})
            self.assertEqual(candidate.status_code,200)
            self.assertEqual(candidate.data[0]['candidate_id'],'photon:N:123')
            self.assertEqual(candidate.data[0]['coordinate'],[-100,40])
            trip=self.client.post('/api/trips/evaluate/',dict(INPUT,departure_at='2026-10-13T14:00:00Z'),format='json')
            self.assertEqual(trip.status_code,200)
            self.assertEqual(trip.data['mode'],'live')
            self.assertEqual(len(trip.data['routes']),1)
            self.assertIn('fewer_than_three_routes',trip.data['warnings'])
            self.assertTrue(trip.data['routes'][0]['complete'])
            self.assertIsNotNone(trip.data['recommendation']['route_id'])
            self.assertEqual(len(calls),3)
    def test_complete_trip_and_49_hour_corridor(self):
        payload=dict(INPUT,destination={'longitude':-98,'latitude':40})
        trip=self.client.post('/api/trips/evaluate/',payload,format='json')
        self.assertEqual(trip.status_code,200);self.assertEqual(len(trip.data['routes']),3)
        corridor=self.client.post('/api/weather/corridor/',{'routes':[r['geometry'] for r in trip.data['routes']],'load_lb':payload['load_lb'],'base_time':'2026-10-13T12:00:00Z'},format='json')
        self.assertEqual(corridor.status_code,200);self.assertEqual(len(corridor.data['frames']),49)
        self.assertLessEqual(len(corridor.data['locations']),150)
        self.assertEqual(corridor.data['coverage']['total_samples'],len(corridor.data['locations'])*49)
    def test_bad_base_time_never_calls_weather(self):
        with patch('routing.api.views.get_services') as services:
            for base in ('2026-10-13T12:01:00Z','2026-10-12T12:00:00Z'):
                response=self.client.post('/api/weather/corridor/',{'routes':[{'type':'LineString','coordinates':[[-100,40],[-98,40]]}],'load_lb':0,'base_time':base},format='json')
                self.assertEqual(response.status_code,400);self.assertEqual(response.data['code'],'invalid_base_time')
            services.assert_not_called()
    def test_busy_admission_and_expired_deadline(self):
        from routing.services.budget import admission,check_deadline
        from routing.providers.base import ProviderError
        with admission(),admission():
            payload=dict(INPUT,destination={'longitude':-98,'latitude':40})
            response=self.client.post('/api/trips/evaluate/',payload,format='json')
            self.assertEqual(response.status_code,503);self.assertEqual(response.data['code'],'service_busy')
        with patch('routing.services.budget.time.monotonic',side_effect=[0,46]):
            with self.assertRaises(ProviderError):
                with admission():check_deadline()
