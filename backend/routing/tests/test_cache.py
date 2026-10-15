import unittest
from datetime import datetime, timezone, timedelta
from routing.domain.models import Coordinate
from routing.services.cache import RawDataCache, MemoryCache, forecast_cache_key, route_cache_key, geocode_cache_key
class CacheTests(unittest.TestCase):
    def test_loader_and_real_expiration(self):
        now=[0];backend=MemoryCache(lambda:now[0]);cache=RawDataCache(backend);calls=[]
        def load():calls.append(1);return (0,None)
        self.assertEqual(cache.get_or_load('a',load,10),(0,None));cache.get_or_load('a',load,10)
        self.assertEqual(len(calls),1);now[0]=11;cache.get_or_load('a',load,10);self.assertEqual(len(calls),2)
    def test_keys_canonicalize_window_but_preserve_locations(self):
        point=Coordinate(-100,40);start=datetime(2026,10,13,12,tzinfo=timezone.utc);end=start+timedelta(hours=2)
        key=forecast_cache_key(point,start,end)
        self.assertEqual(key,forecast_cache_key(point,start+timedelta(minutes=5),end+timedelta(minutes=5)))
        self.assertNotEqual(key,forecast_cache_key(Coordinate(-100.000001,40),start,end))
        self.assertNotEqual(key,forecast_cache_key(point,start,end+timedelta(days=1)))
        self.assertEqual(geocode_cache_key(' Town '),geocode_cache_key('Town'))
        self.assertNotEqual(route_cache_key(point,Coordinate(-99,40)),route_cache_key(point,Coordinate(-98,40)))
    def test_errors_not_cached(self):
        calls=[];cache=RawDataCache(MemoryCache())
        def load():calls.append(1);raise ValueError('failure')
        for _ in range(2):
            with self.assertRaises(ValueError):cache.get_or_load('a',load,10)
        self.assertEqual(len(calls),2)
