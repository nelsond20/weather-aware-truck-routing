import unittest
from math import inf, nan
from routing.domain.models import RiskLevel, WeatherObservation
from routing.domain.risk import assess_weather, classify_rain, classify_snow, classify_wind

class RiskTests(unittest.TestCase):
    def test_increasing_weather_never_reduces_risk_across_dense_ranges(self):
        # Independent safety property: a stronger hazard cannot produce a safer level.
        for load in (0,30000,30000.01,40000,40000.01,1000000):
            levels=[classify_wind(step/10,load) for step in range(701)]
            self.assertEqual(levels,sorted(levels))
        for classify,maximum in ((classify_rain,1200),(classify_snow,3500)):
            levels=[classify(step/1000) for step in range(maximum+1)]
            self.assertEqual(levels,sorted(levels))

    def test_heavier_load_never_reduces_wind_risk(self):
        for step in range(701):
            levels=[classify_wind(step/10,load) for load in (0,30000,30000.01,40000,40000.01,1000000)]
            self.assertEqual(levels,sorted(levels))

    def test_wind_boundaries_without_rounding(self):
        for value, expected in ((0,0),(24.999,0),(25,1),(34.999,1),(35,2),(44.999,2),(45,3),(54.999,3),(55,4),(55.001,4)):
            with self.subTest(value=value):
                self.assertEqual(classify_wind(value,0), RiskLevel(expected))

    def test_precipitation_boundaries(self):
        for value, expected in ((0,0),(.09999,0),(.1,1),(.24999,1),(.25,2),(.49999,2),(.5,3),(1,3),(1.00001,4)):
            with self.subTest(rain=value):
                self.assertEqual(classify_rain(value),RiskLevel(expected))
        for value, expected in ((0,0),(.49999,0),(.5,1),(.99999,1),(1,2),(1.99999,2),(2,3),(3,3),(3.00001,4)):
            with self.subTest(snow=value):
                self.assertEqual(classify_snow(value),RiskLevel(expected))

    def test_weight_boundaries_are_strict(self):
        for wind, load, expected in ((45,30000,3),(45,30000.01,4),(35,40000,2),(35,40000.01,3),(34.99,50000,1),(44.99,40001,3),(55,0,4)):
            with self.subTest(wind=wind,load=load):
                self.assertEqual(classify_wind(wind,load),RiskLevel(expected))

    def test_invalid_weather_is_unknown(self):
        for value in (None,-1,nan,inf,-inf,True):
            with self.subTest(value=value):
                self.assertIsNone(classify_wind(value,0))
                self.assertIsNone(classify_rain(value))
                self.assertIsNone(classify_snow(value))

    def test_invalid_load_is_rejected_even_with_missing_wind(self):
        for value in (-1,nan,inf,True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                classify_wind(None,value)

    def test_missing_rain_preserves_known_no_travel(self):
        result=assess_weather(WeatherObservation(55,None,0,None,None,None),0)
        self.assertIsNone(result.level)
        self.assertEqual(result.known_max,RiskLevel.NO_TRAVEL)
        self.assertEqual(result.missing_fields,('rain',))
        self.assertTrue(result.reasons)

    def test_maximum_danger_and_individual_causes_are_preserved(self):
        result=assess_weather(WeatherObservation(20,.3,2.1,None,None,None),0)
        self.assertEqual(result.level,RiskLevel.SEVERE)
        self.assertEqual(result.wind_level,RiskLevel.LOW)
        self.assertEqual(result.rain_level,RiskLevel.HIGH)
        self.assertEqual(result.snow_level,RiskLevel.SEVERE)
        self.assertEqual(result.missing_fields,())

    def test_low_zero_is_not_treated_as_missing(self):
        result=assess_weather(WeatherObservation(0,0,0,None,None,None),0)
        self.assertEqual(result.level,RiskLevel.LOW)
        self.assertEqual(result.known_max,RiskLevel.LOW)
