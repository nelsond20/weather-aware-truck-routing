import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from routing.domain.models import Coordinate
from routing.providers.base import ProviderError
from routing.providers import http
from routing.tests.test_osrm import PAYLOAD


class ValhallaTests(unittest.TestCase):
    def provider(self, request):
        from routing.providers.valhalla import ValhallaRoutingProvider
        return ValhallaRoutingProvider(request)

    def test_requests_two_alternates_and_aligned_full_shape_timing(self):
        calls = []
        def request(url, params):
            calls.append((url, params))
            return deepcopy(PAYLOAD)
        route = self.provider(request).routes(Coordinate(-100, 40), Coordinate(-99, 40))[0]
        self.assertEqual(route.segments[1].duration_s, 900)
        self.assertEqual(sum(s.distance_m for s in route.segments), 24140.16)
        self.assertEqual(calls[0][0], 'https://valhalla1.openstreetmap.de/route')
        options = json.loads(calls[0][1]['json'])
        self.assertNotIn(' ', calls[0][1]['json'])  # The endpoint rejects '+'-encoded spaces.
        self.assertEqual(options['alternates'], 2)
        self.assertEqual(options['locations'], [{'lon': -100, 'lat': 40}, {'lon': -99, 'lat': 40}])
        self.assertEqual(options['costing'], 'auto')
        self.assertEqual(options['format'], 'osrm')
        self.assertEqual(options['shape_format'], 'geojson')
        self.assertEqual(options['filters'], {'action': 'include', 'attributes': ['shape_attributes.time', 'shape_attributes.length']})
        self.assertNotIn('generalize', options)  # Default is the full, annotation-aligned shape.
        self.assertNotIn('date_time', options)  # Time-dependent routing disables alternates.

    def test_three_distinct_routes_preserved_without_fabricating_missing_routes(self):
        payload = deepcopy(PAYLOAD)
        second = deepcopy(payload['routes'][0])
        second['geometry']['coordinates'][1] = [-99.5, 40.1]
        third = deepcopy(payload['routes'][0])
        third['geometry']['coordinates'][1] = [-99.5, 39.9]
        for raw, count in (([payload['routes'][0]], 1), ([payload['routes'][0], second], 2), ([payload['routes'][0], second, third], 3)):
            with self.subTest(count=count):
                payload['routes'] = raw + [deepcopy(raw[0])]
                routes = self.provider(lambda *args: payload).routes(Coordinate(-100, 40), Coordinate(-99, 40))
                self.assertEqual(len(routes), count)
                self.assertEqual(len({r.route_id for r in routes}), count)

    def test_invalid_annotations_and_no_route_are_normalized(self):
        payload = deepcopy(PAYLOAD)
        payload['routes'][0]['legs'][0]['annotation']['duration'] = [600]
        for value, code in ((payload, 'provider_contract_invalid'), ({'code': 'NoRoute'}, 'no_route')):
            with self.subTest(code=code):
                with self.assertRaises(ProviderError) as caught:
                    self.provider(lambda *args: value).routes(Coordinate(-100, 40), Coordinate(-99, 40))
                self.assertEqual(caught.exception.code, code)

    def test_identifying_client_header_and_existing_public_rate_limit(self):
        from routing.tests.test_http import TransportTests
        http._last_public_request.clear()
        http._public_cooldown.clear()
        with patch('routing.providers.http.httpx.Client') as client, patch('routing.providers.http.time.monotonic', return_value=10), patch('routing.providers.http.time.sleep') as wait:
            TransportTests().response(client)
            for _ in range(2):
                self.assertEqual(http.request_json('https://valhalla1.openstreetmap.de/route', {}), {'ok': True})
            self.assertEqual(client.call_args.kwargs['headers']['X-Client-Id'], 'weather-aware-truck-routing-spotter-assessment')
            wait.assert_called_once_with(1)

    def test_routing_caches_do_not_mix_providers(self):
        from routing.services.cache import route_cache_key
        origin, destination = Coordinate(-100, 40), Coordinate(-99, 40)
        self.assertNotEqual(route_cache_key(origin, destination, provider='osrm'), route_cache_key(origin, destination, provider='valhalla'))

    def test_live_provider_selection_preserves_osrm_and_demo(self):
        from django.test import override_settings
        from routing.services.trips import build_services
        for name, expected in (('osrm', 'OSRMRoutingProvider'), ('valhalla', 'ValhallaRoutingProvider')):
            with self.subTest(provider=name), override_settings(LIVE_ROUTING_PROVIDER=name):
                with self.assertLogs('routing.services.trips',level='INFO') as logs:
                    self.assertEqual(type(build_services('live').trip.routing).__name__, expected)
                self.assertIn(f'mode=live configured_routing_provider={name} active_routing_provider={expected}',logs.output[0])
                self.assertEqual(type(build_services('demo').trip.routing).__name__, 'DemoRoutingProvider')

    def test_identifies_routing_limits_without_exposing_upstream_messages(self):
        for payload,expected in (
            ({'code':'DistanceExceeded','message':'private upstream details'},'route_distance_exceeded'),
            ({'error_code':154,'error':'private upstream details'},'route_distance_exceeded'),
            ({'error_code':170},'no_route'),
            ({'error_code':171},'route_location_unavailable'),
            ({'error_code':441},'no_route'),
            ({'error_code':442},'no_route'),
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ProviderError) as caught:
                    self.provider(lambda *args:payload).routes(Coordinate(-100,40),Coordinate(-99,40))
                self.assertEqual(caught.exception.code,expected)
                self.assertFalse(caught.exception.retryable)
                self.assertNotIn('private upstream details',caught.exception.message)

    def test_distance_exceeded_http_400_reaches_the_routing_adapter(self):
        import httpx
        real_client=httpx.Client
        transport=httpx.MockTransport(lambda request:httpx.Response(400,json={'code':'DistanceExceeded','message':'Path distance exceeds the max distance limit.'}))
        http._last_public_request.clear()
        with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=transport,**kwargs)):
            with self.assertRaises(ProviderError) as caught:
                self.provider(http.request_json).routes(Coordinate(-100,40),Coordinate(-99,40))
        self.assertEqual(caught.exception.code,'route_distance_exceeded')
