import unittest
from datetime import datetime,timedelta,timezone
from routing.domain.forecast import select_weather
from routing.domain.models import HourlyForecast
H=datetime(2026,10,13,15,tzinfo=timezone.utc)
def row(hour,wind,rain,snow):
    return HourlyForecast(hour,hour-timedelta(hours=1),hour,wind,rain,snow)
SERIES=(row(H,20,.3,0),row(H+timedelta(hours=1),30,0,1))
class ForecastTests(unittest.TestCase):
    def test_accumulation_uses_ending_timestamp_and_exact_boundary(self):
        for eta in (H-timedelta(minutes=10),H):
            result=select_weather(SERIES,eta)
            self.assertEqual(result.rain_in_hr,.3)
            self.assertEqual(result.accumulation_end,H)
    def test_wind_tie_uses_earlier_sample(self):
        result=select_weather(SERIES,H+timedelta(minutes=30))
        self.assertEqual(result.wind_mph,20)
        self.assertEqual(result.rain_in_hr,0)
        self.assertEqual(result.snow_in_hr,1)
    def test_outside_wind_coverage_does_not_extrapolate(self):
        result=select_weather(SERIES,H-timedelta(minutes=10))
        self.assertIsNone(result.wind_mph)
        self.assertEqual(result.rain_in_hr,.3)
        result=select_weather(SERIES,H+timedelta(hours=2))
        self.assertIsNone(result.wind_mph)
        self.assertIsNone(result.rain_in_hr)
    def test_empty_series_returns_unknown(self):
        result=select_weather((),H)
        self.assertIsNone(result.wind_mph)
        self.assertIsNone(result.accumulation_end)
    def test_unordered_identical_duplicates_and_offset(self):
        eta=H.astimezone(timezone(timedelta(hours=-5)))
        result=select_weather((SERIES[1],SERIES[0],SERIES[0]),eta)
        self.assertEqual(result.wind_mph,20)
        self.assertEqual(result.rain_in_hr,.3)
        self.assertEqual(result.wind_valid_at,H)
    def test_conflicting_duplicates_invalidate_that_hour(self):
        result=select_weather((row(H,20,.3,0),row(H,55,0,0),SERIES[1]),H)
        self.assertIsNone(result.wind_mph)
        self.assertIsNone(result.rain_in_hr)
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):select_weather(SERIES,H.replace(tzinfo=None))
        with self.assertRaises(ValueError):select_weather((row(H.replace(tzinfo=None),20,0,0),),H)
    def test_missing_wind_sample_not_replaced_by_another_hour(self):
        result=select_weather((row(H,None,0,0),SERIES[1]),H)
        self.assertIsNone(result.wind_mph)
        self.assertEqual(result.rain_in_hr,0)
