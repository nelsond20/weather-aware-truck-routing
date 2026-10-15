import unittest
from copy import deepcopy
from routing.domain.models import Coordinate
from routing.providers.base import ProviderError
from routing.providers.osrm import OSRMRoutingProvider
PAYLOAD={'code':'Ok','routes':[{'distance':24140.16,'duration':1500,'geometry':{'type':'LineString','coordinates':[[-100,40],[-99.5,40],[-99,40]]},'legs':[{'duration':1500,'annotation':{'distance':[16093.44,8046.72],'duration':[600,900]}}]}]}
class OSRMTests(unittest.TestCase):
    def test_requested_parameters_and_segment_alignment(self):
        calls=[]
        def request(url,params):
            calls.append((url,params));return deepcopy(PAYLOAD)
        routes=OSRMRoutingProvider(request).routes(Coordinate(-100,40),Coordinate(-99,40))
        self.assertEqual(len(routes),1)
        self.assertEqual(routes[0].segments[1].duration_s,900)
        self.assertEqual(calls[0][1]['alternatives'],'2')
        self.assertEqual(calls[0][1]['geometries'],'geojson')
        self.assertNotIn('access_token',calls[0][1])
        self.assertTrue(calls[0][0].startswith('https://router.project-osrm.org/route/v1/driving/'))
        self.assertEqual(calls[0][1]['overview'],'full')
        self.assertEqual(calls[0][1]['annotations'],'distance,duration')
        self.assertIn('-100,40;-99,40',calls[0][0])
    def test_misaligned_annotations_and_invalid_numbers_rejected(self):
        for change in ('array','nan','coordinate','total'):
            payload=deepcopy(PAYLOAD)
            if change=='array':payload['routes'][0]['legs'][0]['annotation']['duration']=[600]
            if change=='nan':payload['routes'][0]['legs'][0]['annotation']['duration']=[600,float('nan')]
            if change=='coordinate':payload['routes'][0]['geometry']['coordinates'][0]=[0,100]
            if change=='total':payload['routes'][0]['distance']=1
            with self.subTest(change=change),self.assertRaises(ProviderError) as caught:
                OSRMRoutingProvider(lambda *args:payload).routes(Coordinate(-100,40),Coordinate(-99,40))
            self.assertEqual(caught.exception.code,'provider_contract_invalid')
    def test_duplicate_routes_removed_and_three_distinct_preserved(self):
        payload=deepcopy(PAYLOAD)
        second=deepcopy(payload['routes'][0]);second['geometry']['coordinates'][1]=[-99.5,40.1]
        third=deepcopy(payload['routes'][0]);third['geometry']['coordinates'][1]=[-99.5,39.9]
        payload['routes']=[payload['routes'][0],deepcopy(payload['routes'][0]),second,third]
        routes=OSRMRoutingProvider(lambda *args:payload).routes(Coordinate(-100,40),Coordinate(-99,40))
        self.assertEqual(len(routes),3)
        self.assertEqual(len({r.route_id for r in routes}),3)
    def test_no_route_is_not_a_successful_empty_result(self):
        with self.assertRaises(ProviderError) as caught:
            OSRMRoutingProvider(lambda *args:{'code':'NoRoute','routes':[]}).routes(Coordinate(-100,40),Coordinate(-99,40))
        self.assertEqual(caught.exception.code,'no_route')
    def test_turn_costs_preserve_reported_duration_and_mark_eta_approximate(self):
        payload=deepcopy(PAYLOAD)
        payload['routes'][0]['duration']=1620
        payload['routes'][0]['legs'][0]['duration']=1620
        route=OSRMRoutingProvider(lambda *args:payload).routes(Coordinate(-100,40),Coordinate(-99,40))[0]
        self.assertAlmostEqual(sum(segment.duration_s for segment in route.segments),1620)
        self.assertAlmostEqual(route.segments[0].duration_s,648)
        self.assertTrue(route.eta_approximate)
