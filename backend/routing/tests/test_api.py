from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import patch
from copy import deepcopy
from rest_framework.test import APITestCase
from routing.services.trips import TripService
from routing.services.cache import RawDataCache,MemoryCache
from routing.tests.test_trips import RoutingFake,WeatherFake
INPUT={'origin':{'longitude':-100,'latitude':40},'destination':{'longitude':-99,'latitude':40},'departure_at':'2026-10-13T12:00:00Z','load_lb':30000,'spacing_miles':10}
class ApiTests(APITestCase):
    def setUp(self):
        from routing.api.limits import reset_limits
        reset_limits();self.routing=RoutingFake();self.weather=WeatherFake()
        services=SimpleNamespace(trip=TripService(self.routing,self.weather,RawDataCache(MemoryCache()),'demo'),mode='demo')
        self.service_patch=patch('routing.api.views.get_services',return_value=services);self.service_patch.start();self.addCleanup(self.service_patch.stop)
        self.clock=patch('routing.api.views.get_current_time',return_value=datetime(2026,10,13,11,tzinfo=timezone.utc));self.clock.start();self.addCleanup(self.clock.stop)
    def test_health_no_provider_and_evaluation_contract(self):
        self.assertEqual(self.client.get('/api/health/').status_code,200);self.assertEqual(self.routing.calls,0)
        response=self.client.post('/api/trips/evaluate/',INPUT,format='json')
        self.assertEqual(response.status_code,200);self.assertEqual(response.data['mode'],'demo')
        self.assertEqual(response.data['routes'][0]['checkpoints'][0]['level'],'severe')
        self.assertEqual(response.data['routes'][0]['intervals'][0]['geometry']['type'],'LineString')
    def test_invalid_input_does_not_reach_provider(self):
        cases=[]
        for key,value in [('departure_at','2026-10-13T12:00:00'),('load_lb',True),('load_lb','30000'),('load_lb',float('inf')),('spacing_miles',True),('extra',1)]:
            item=deepcopy(INPUT);item[key]=value;cases.append(item)
        item=deepcopy(INPUT);item['origin']['latitude']=True;cases.append(item)
        for item in cases:
            with self.subTest(item=str(item)):
                response=self.client.post('/api/trips/evaluate/',item,format='json') if item.get('load_lb')!=float('inf') else self.client.generic('POST','/api/trips/evaluate/', '{"load_lb":Infinity}',content_type='application/json')
                self.assertEqual(response.status_code,400);self.assertEqual(response.data['code'],'invalid_input')
        self.assertEqual(self.routing.calls,0)
    def test_past_departure_rejected(self):
        response=self.client.post('/api/trips/evaluate/',dict(INPUT,departure_at='2026-10-13T10:00:00Z'),format='json')
        self.assertEqual(response.status_code,400);self.assertEqual(response.data['code'],'departure_in_past')
    def test_invalid_json_and_oversize(self):
        self.assertEqual(self.client.generic('POST','/api/trips/evaluate/','{',content_type='application/json').status_code,400)
        response=self.client.generic('POST','/api/trips/evaluate/','x'*(2*1024*1024+1),content_type='application/json')
        self.assertEqual(response.status_code,413);self.assertEqual(self.routing.calls,0)
    def test_throttle_eleventh_request(self):
        for _ in range(10):self.assertEqual(self.client.post('/api/trips/evaluate/',INPUT,format='json').status_code,200)
        response=self.client.post('/api/trips/evaluate/',INPUT,format='json')
        self.assertEqual(response.status_code,429);self.assertEqual(response.data['code'],'rate_limited');self.assertIn('Retry-After',response)
        self.assertEqual(self.routing.calls,1)
    def test_dst_offsets_remain_distinct(self):
        from routing.api.serializers import TripInputSerializer
        results=[]
        for offset in ('-04:00','-05:00'):
            serializer=TripInputSerializer(data=dict(INPUT,departure_at='2026-11-01T01:30:00'+offset),context={'now':datetime(2026,10,13,tzinfo=timezone.utc)})
            self.assertTrue(serializer.is_valid(),serializer.errors);results.append(serializer.validated_data['departure_at'])
        self.assertEqual((results[1]-results[0]).total_seconds(),3600)

    def test_corridor_route_count_rejected_before_nested_geometry_validation(self):
        from routing.api.serializers import CorridorInputSerializer
        serializer=CorridorInputSerializer(data={'routes':[{}]*4,'load_lb':1},context={'now':datetime(2026,10,13,11,tzinfo=timezone.utc)})
        self.assertFalse(serializer.is_valid())
        self.assertIsInstance(serializer.errors['routes'],dict)
        self.assertIn('non_field_errors',serializer.errors['routes'])
        self.assertEqual(serializer.errors['routes']['non_field_errors'][0].code,'max_length')

    def test_corridor_total_vertex_limit_precedes_coordinate_validation(self):
        from routing.api.serializers import CorridorInputSerializer
        serializer=CorridorInputSerializer(data={'routes':[
            {'type':'LineString','coordinates':[['invalid']]*10001},
            {'type':'LineString','coordinates':[['invalid']]*10000},
        ],'load_lb':1},context={'now':datetime(2026,10,13,11,tzinfo=timezone.utc)})
        self.assertFalse(serializer.is_valid())
        self.assertIsInstance(serializer.errors['routes'],dict)
        self.assertIn('non_field_errors',serializer.errors['routes'])
        self.assertEqual(serializer.errors['routes']['non_field_errors'][0].code,'max_length')

    def test_repeated_invalid_corridor_requests_are_rate_limited(self):
        payload={'routes':[{}]*4,'load_lb':1}
        for _ in range(5):
            self.assertEqual(self.client.post('/api/weather/corridor/',payload,format='json').status_code,400)
        response=self.client.post('/api/weather/corridor/',payload,format='json')
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.data['code'],'rate_limited')

    def test_busy_corridor_rejects_before_parsing_geometry(self):
        from routing.services.budget import admission
        with admission(),admission():
            response=self.client.post('/api/weather/corridor/',{'routes':[{}]*4,'load_lb':1},format='json')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.data['code'],'service_busy')
