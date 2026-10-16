import unittest
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from routing.domain.models import Coordinate
from routing.providers.base import ProviderError
from routing.providers.open_meteo import OpenMeteoWeatherProvider
PAYLOAD={'latitude':40,'longitude':-100,'utc_offset_seconds':0,'hourly_units':{'time':'iso8601','wind_speed_10m':'mp/h','rain':'mm','snowfall':'cm'},'hourly':{'time':['2026-10-13T14:00','2026-10-13T15:00','2026-10-13T16:00'],'wind_speed_10m':[20,35,55],'rain':[0,6.35,None],'snowfall':[0,2.54,0]}}
class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.point=Coordinate(-100,40);self.start=datetime(2026,10,13,14,tzinfo=timezone.utc);self.end=self.start+timedelta(hours=2)
    def test_conversion_and_ending_hour(self):
        calls=[]
        def request(url,params):calls.append(params);return deepcopy(PAYLOAD)
        series=OpenMeteoWeatherProvider(request).forecast((self.point,),self.start,self.end)[self.point]
        self.assertAlmostEqual(series[1].rain_in_hr,.25);self.assertAlmostEqual(series[1].snow_in_hr,1)
        self.assertEqual(series[1].accumulation_end,series[1].valid_at)
        self.assertEqual(series[1].accumulation_start,series[1].valid_at-timedelta(hours=1))
        self.assertEqual(calls[0]['wind_speed_unit'],'mph')
    def test_truncated_or_missing_field_is_unknown(self):
        payload=deepcopy(PAYLOAD);payload['hourly']['wind_speed_10m']=[20];payload['hourly'].pop('rain')
        series=OpenMeteoWeatherProvider(lambda *args:payload).forecast((self.point,),self.start,self.end)[self.point]
        self.assertIsNone(series[1].wind_mph);self.assertIsNone(series[0].rain_in_hr)
    def test_unknown_units_and_missing_time_rejected(self):
        for field in ('unit','time','coordinate','offset'):
            payload=deepcopy(PAYLOAD)
            if field=='unit':payload['hourly_units']['snowfall']='mystery'
            if field=='time':payload['hourly'].pop('time')
            if field=='coordinate':payload['longitude']=20
            if field=='offset':payload['utc_offset_seconds']=3600
            with self.subTest(field=field),self.assertRaises(ProviderError):OpenMeteoWeatherProvider(lambda *args:payload).forecast((self.point,),self.start,self.end)
    def test_multi_point_order_and_batches(self):
        points=tuple(Coordinate(-100+i*.01,40) for i in range(26));calls=[]
        def request(url,params):
            calls.append(params);values=[]
            for lon in params['longitude'].split(','):
                value=deepcopy(PAYLOAD);value['longitude']=float(lon);values.append(value)
            return values if len(values)>1 else values[0]
        result=OpenMeteoWeatherProvider(request).forecast(points,self.start,self.end)
        self.assertEqual(len(result),26);self.assertEqual(len(calls),2)
    def test_partial_batch_failure_preserves_other_locations(self):
        points=tuple(Coordinate(-100+i*.01,40) for i in range(26))
        def request(url,params):
            if len(params['longitude'].split(','))==1:raise ProviderError('provider_timeout','Weather provider timed out.',True)
            return [dict(deepcopy(PAYLOAD),longitude=float(lon)) for lon in params['longitude'].split(',')]
        result=OpenMeteoWeatherProvider(request).forecast(points,self.start,self.end)
        self.assertEqual(len(result),25);self.assertNotIn(points[-1],result)
