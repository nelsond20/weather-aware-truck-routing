import unittest
import httpx
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from routing.domain.models import Coordinate,RawRoute,RouteSegment
from routing.domain.corridor import build_corridor
from routing.services.corridor import CorridorService
from routing.services.cache import RawDataCache,MemoryCache
from routing.domain.geometry import haversine_m,MILE_M
from routing.tests.test_trips import WeatherFake
A=Coordinate(-100,40);B=Coordinate(-99,40)
ROUTE=RawRoute('r1',(A,B),(RouteSegment(A,B,haversine_m(A,B),0),))
class CorridorTests(unittest.TestCase):
    def setUp(self):self.base=datetime(2026,10,13,12,tzinfo=timezone.utc)
    def test_bounded_grid_has_off_route_points(self):
        grid=build_corridor((ROUTE,))
        self.assertLessEqual(len(grid.locations),150);self.assertGreater(len(grid.locations),2)
        self.assertTrue(any(abs(p.latitude-40)>.05 for p in grid.locations))
        self.assertTrue(all(min(haversine_m(p,q) for q in ROUTE.geometry) <= 20*MILE_M+ROUTE.segments[0].distance_m/2+1 for p in grid.locations))
    def test_duplicates_and_dateline(self):
        grid=build_corridor((ROUTE,ROUTE));single=build_corridor((ROUTE,))
        self.assertEqual(grid.locations,single.locations)
        a,b=Coordinate(179.9,0),Coordinate(-179.9,0)
        route=RawRoute('date',(a,b),(RouteSegment(a,b,haversine_m(a,b),0),))
        grid=build_corridor((route,))
        self.assertTrue(all(abs(p.longitude)>179 for p in grid.locations));self.assertLessEqual(len(grid.locations),150)
    def test_diagonal_not_bounding_box(self):
        a,b=Coordinate(-120,30),Coordinate(-80,50)
        route=RawRoute('long',(a,b),(RouteSegment(a,b,haversine_m(a,b),0),))
        grid=build_corridor((route,));self.assertEqual(len(grid.locations),150)
        self.assertFalse(any(haversine_m(p,Coordinate(-120,50))<100000 for p in grid.locations))
    def test_49_frames_and_load_reuses_weather(self):
        class Full(WeatherFake):
            def forecast(self,points,start,end):
                self.calls+=1
                from routing.domain.models import HourlyForecast
                return {p:tuple(HourlyForecast(start+timedelta(hours=i),start+timedelta(hours=i-1),start+timedelta(hours=i),45,0,0) for i in range(52)) for p in points}
        weather=Full();service=CorridorService(weather,RawDataCache(MemoryCache()),'demo')
        light=service.forecast((ROUTE,),30000,self.base);heavy=service.forecast((ROUTE,),30001,self.base)
        self.assertEqual(len(light.frames),49);self.assertEqual(light.frames[-1].valid_at,self.base+timedelta(hours=48))
        self.assertTrue(all(len(f.risks)==len(light.grid.locations) for f in light.frames))
        self.assertEqual(weather.calls,1);self.assertNotEqual(light.frames[0].risks[0].level,heavy.frames[0].risks[0].level)
    def test_open_meteo_batches_full_window_then_reuses_series_for_all_frames(self):
        from routing.providers.open_meteo import OpenMeteoWeatherProvider
        from routing.domain.models import RiskLevel
        calls=[]
        def request(url,params):
            calls.append(params)
            self.assertEqual(url,'https://api.open-meteo.com/v1/forecast')
            self.assertEqual(params['hourly'],'wind_speed_10m,rain,snowfall')
            self.assertEqual(params['start_date'],'2026-10-13');self.assertEqual(params['end_date'],'2026-10-15')
            self.assertLess(len(str(httpx.Request('GET',url,params=params).url)),2000)
            values=[]
            for lat,lon in zip(params['latitude'].split(','),params['longitude'].split(',')):
                values.append({'latitude':float(lat),'longitude':float(lon),'utc_offset_seconds':0,
                    'hourly_units':{'time':'iso8601','wind_speed_10m':'mp/h','rain':'mm','snowfall':'cm'},
                    'hourly':{'time':[(self.base+timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M') for i in range(-1,50)],
                              'wind_speed_10m':[45]*51,'rain':[0]*51,'snowfall':[0]*51}})
            return values if len(values)>1 else values[0]
        service=CorridorService(OpenMeteoWeatherProvider(request),RawDataCache(MemoryCache()),'live')
        light=service.forecast((ROUTE,),30000,self.base)
        self.assertEqual(len(light.frames),49);self.assertEqual(light.frames[-1].valid_at,self.base+timedelta(hours=48))
        self.assertGreater(len(light.grid.locations),25);self.assertLessEqual(len(calls),6)
        self.assertTrue(all(1<=len(p['latitude'].split(','))<=25 for p in calls))
        self.assertTrue(all(risk.level==RiskLevel.SEVERE for frame in light.frames for risk in frame.risks))
        count=len(calls)
        heavy=service.forecast((ROUTE,),30001,self.base)
        self.assertEqual(len(calls),count)
        self.assertTrue(all(risk.level==RiskLevel.NO_TRAVEL for frame in heavy.frames for risk in frame.risks))
    def test_total_coverage_counts_all_frames(self):
        from routing.domain.models import CorridorGrid,HourlyForecast
        class Partial:
            def forecast(self,points,start,end):
                return {p:tuple(HourlyForecast(self_base+timedelta(hours=i),self_base+timedelta(hours=i-1),self_base+timedelta(hours=i),None if p==B and i==48 else 20,0,0) for i in range(49)) for p in points}
        self_base=self.base
        with patch('routing.services.corridor.build_corridor',return_value=CorridorGrid((A,B),20,1000)):
            result=CorridorService(Partial(),RawDataCache(MemoryCache()),'demo').forecast((ROUTE,),0,self.base)
        self.assertEqual(sum(r.level is not None for f in result.frames for r in f.risks),97)
    def test_empty_routes_and_naive_time_rejected(self):
        with self.assertRaises(ValueError):build_corridor(())
        with self.assertRaises(ValueError):CorridorService(WeatherFake(),RawDataCache(MemoryCache()),'demo').forecast((ROUTE,),0,self.base.replace(tzinfo=None))
