import unittest
from datetime import datetime,timezone,timedelta
from routing.domain.models import Coordinate,RawRoute,RouteSegment,TripRequest,HourlyForecast
from routing.services.trips import TripService
from routing.services.cache import RawDataCache,MemoryCache
from routing.providers.base import ProviderError
A=Coordinate(-100,40);B=Coordinate(-99,40)
class RoutingFake:
    calls=0
    def routes(self,a,b):
        self.calls+=1;return (RawRoute('r1',(A,B),(RouteSegment(A,B,24140.16,1500),)),)
class WeatherFake:
    calls=0
    def forecast(self,locations,start,end):
        self.calls+=1;base=start.replace(minute=0,second=0,microsecond=0)-timedelta(hours=1)
        return {p:tuple(HourlyForecast(base+timedelta(hours=i),base+timedelta(hours=i-1),base+timedelta(hours=i),45,0,0) for i in range(5)) for p in locations}
class TripTests(unittest.TestCase):
    def setUp(self):
        self.routing=RoutingFake();self.weather=WeatherFake();self.service=TripService(self.routing,self.weather,RawDataCache(MemoryCache()),'demo')
        self.request=TripRequest(A,B,datetime(2026,10,13,12,tzinfo=timezone.utc),30000,10)
    def test_repeated_load_reuses_originals_but_reclassifies(self):
        light=self.service.evaluate(self.request)
        heavy=self.service.evaluate(TripRequest(A,B,self.request.departure_at,30001,10))
        self.assertFalse(light.routes[0].blocked);self.assertTrue(heavy.routes[0].blocked)
        self.assertEqual(self.routing.calls,1);self.assertEqual(self.weather.calls,1)
        self.assertIn('fewer_than_three_routes',light.warnings)
    def test_sampling_limit_before_weather(self):
        class HugeRoute:
            def routes(self,*args):return (RawRoute('huge',(A,B),(RouteSegment(A,B,20000000,1500),)),)
        service=TripService(HugeRoute(),self.weather,RawDataCache(MemoryCache()),'demo')
        with self.assertRaises(ProviderError) as caught:service.evaluate(self.request)
        self.assertEqual(caught.exception.code,'sampling_limit_exceeded');self.assertEqual(self.weather.calls,0)
    def test_missing_location_retained_as_unknown(self):
        class Partial(WeatherFake):
            def forecast(self,locations,start,end):return super().forecast(locations[:1],start,end)
        result=TripService(self.routing,Partial(),RawDataCache(MemoryCache()),'demo').evaluate(self.request)
        self.assertFalse(result.routes[0].complete);self.assertIsNone(result.recommendation.route_id)
        self.assertIn('weather_coverage_incomplete',result.warnings)
    def test_total_weather_failure_is_not_success(self):
        class Failed:
            def forecast(self,*args):raise ProviderError('provider_timeout','Weather provider timed out.',True)
        with self.assertRaises(ProviderError):TripService(self.routing,Failed(),RawDataCache(MemoryCache()),'demo').evaluate(self.request)
