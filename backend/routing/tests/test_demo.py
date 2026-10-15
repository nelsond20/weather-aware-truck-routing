import unittest
from dataclasses import replace
from datetime import datetime,timezone
from routing.domain.models import TripRequest,Coordinate
from routing.providers.demo import DemoRoutingProvider,DemoWeatherProvider,DemoGeocodingProvider
from routing.services.trips import TripService
from routing.services.cache import RawDataCache,MemoryCache
class DemoTests(unittest.TestCase):
    def request(self,load):return TripRequest(Coordinate(-100,40),Coordinate(-98,40),datetime(2026,10,13,12,tzinfo=timezone.utc),load,10)
    def service(self,routes=3,weather=None):return TripService(DemoRoutingProvider(routes),weather or DemoWeatherProvider(),RawDataCache(MemoryCache()),'demo')
    def test_uniform_no_travel_average_never_exceeds_the_score_contract(self):
        trip=self.service(weather=DemoWeatherProvider(wind_override=55)).evaluate(replace(self.request(0),spacing_miles=25))
        for route in trip.routes:
            with self.subTest(route=route.route.route_id):
                self.assertLessEqual(route.average_risk,4)
                self.assertEqual(route.average_risk,4)

    def test_uniform_weather_keeps_its_exact_average_at_every_spacing(self):
        for wind,score in ((0,0),(25,1),(35,2),(45,3),(55,4)):
            for spacing in (10,25,50):
                trip=self.service(weather=DemoWeatherProvider(wind_override=wind)).evaluate(replace(self.request(0),spacing_miles=spacing))
                for route in trip.routes:
                    with self.subTest(wind=wind,spacing=spacing,route=route.route.route_id):
                        self.assertEqual(route.average_risk,score)

    def test_weight_recalculates_real_rules(self):
        service=self.service();light=service.evaluate(self.request(30000));heavy=service.evaluate(self.request(30001))
        self.assertFalse(light.routes[0].blocked);self.assertTrue(heavy.routes[0].blocked)
        self.assertEqual(light.routes[0].route.geometry,heavy.routes[0].route.geometry)
        self.assertEqual(len(light.routes),3)
    def test_all_blocked_one_route_and_incomplete(self):
        blocked=self.service(weather=DemoWeatherProvider(wind_override=55)).evaluate(self.request(0))
        self.assertEqual(blocked.recommendation.status,'all_blocked')
        single=self.service(routes=1).evaluate(self.request(0));self.assertEqual(len(single.routes),1)
        incomplete=self.service(weather=DemoWeatherProvider(missing_snow=True)).evaluate(self.request(0))
        self.assertEqual(incomplete.recommendation.status,'insufficient_data')
    def test_geocode_only_documented_scenario(self):
        provider=DemoGeocodingProvider()
        self.assertEqual(provider.search('West')[0].coordinate,Coordinate(-100,40))
        self.assertEqual(provider.search('Atlantis'),())
