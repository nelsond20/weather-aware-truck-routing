import unittest
from unittest.mock import patch
from datetime import datetime, timezone
import httpx
from routing.providers import http
from routing.providers.http import request_json, USER_AGENT
from routing.providers.base import ProviderError
class TransportTests(unittest.TestCase):
    def setUp(self):
        http._last_public_request.clear();http._public_cooldown.clear()

    def response(self, client, status=200, headers=None):
        response=httpx.Response(status,json={'ok':True},headers=headers)
        client.return_value.__enter__.return_value.stream.return_value.__enter__.return_value=response

    def test_unapproved_url_rejected_before_transport(self):
        with patch('routing.providers.http.httpx.Client') as client:
            for url in ('http://router.project-osrm.org/route/v1/driving/0,0;1,1','https://localhost/a','https://photon.komoot.io:444/api/','https://photon.komoot.io@evil.com/api/','https://router.project-osrm.org/unknown','https://api.mapbox.com/directions/v5/mapbox/driving/0,0;1,1'):
                with self.subTest(url=url),self.assertRaises(ProviderError):request_json(url,{})
            client.assert_not_called()

    def test_public_hosts_and_identifying_user_agent(self):
        with patch('routing.providers.http.httpx.Client') as client:
            self.response(client)
            for url in ('https://photon.komoot.io/api/','https://router.project-osrm.org/route/v1/driving/0,0;1,1','https://api.open-meteo.com/v1/forecast'):
                self.assertEqual(request_json(url,{}),{'ok':True})
            self.assertEqual(client.call_args.kwargs['headers'],{'User-Agent':USER_AGENT})
            self.assertFalse(client.call_args.kwargs['follow_redirects'])

    def test_public_requests_spaced_per_host(self):
        with patch('routing.providers.http.httpx.Client') as client, patch('routing.providers.http.time.monotonic',return_value=10), patch('routing.providers.http.time.sleep') as sleep:
            self.response(client)
            request_json('https://photon.komoot.io/api/',{})
            request_json('https://photon.komoot.io/api/',{})
            sleep.assert_called_once_with(1)

    def test_retry_after_prevents_further_requests(self):
        with patch('routing.providers.http.httpx.Client') as client, patch('routing.providers.http.time.monotonic',return_value=10):
            self.response(client,429,{'Retry-After':'120'})
            for _ in range(2):
                with self.assertRaises(ProviderError) as caught:request_json('https://photon.komoot.io/api/',{})
                self.assertEqual(caught.exception.code,'provider_rate_limited')
            self.assertEqual(client.call_count,1)
            self.assertEqual(http._public_cooldown['photon.komoot.io'],130)

    def test_weather_transient_responses_recover_with_exponential_backoff(self):
        real_client=httpx.Client
        for status in (429,502,503,504):
            with self.subTest(status=status):
                requests=[];responses=[];delays=[]
                def handle(request):
                    requests.append(request)
                    response=httpx.Response(status if len(requests)<3 else 200,json={'ok':True})
                    responses.append(response)
                    return response
                def wait(delay):
                    self.assertTrue(responses[-1].is_closed)
                    delays.append(delay)
                transport=httpx.MockTransport(handle)
                with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=transport,**kwargs)),patch('routing.providers.http.time.sleep',side_effect=wait):
                    try:value=request_json('https://api.open-meteo.com/v1/forecast',{'latitude':'52,53','longitude':'13,14'})
                    except ProviderError as error:self.fail(f'Transient weather response was not recovered: {error.code}')
                self.assertEqual(value,{'ok':True})
                self.assertEqual(delays,[1,2])
                self.assertEqual(len(requests),3)
                self.assertTrue(all(r.url.params['latitude']=='52,53' for r in requests))

    def test_weather_retry_after_is_respected_for_seconds_and_http_dates(self):
        real_client=httpx.Client
        for header,expected in (('4',4),('Tue, 13 Oct 2026 12:00:04 GMT',4),('invalid',1)):
            with self.subTest(header=header):
                requests=[];delays=[]
                def handle(request):
                    requests.append(request)
                    return httpx.Response(429 if len(requests)==1 else 200,json={'ok':True},headers={'Retry-After':header})
                with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=httpx.MockTransport(handle),**kwargs)),patch('routing.providers.http.time.sleep',side_effect=delays.append),patch('routing.providers.http.datetime') as clock:
                    clock.now.return_value=datetime(2026,10,13,12,tzinfo=timezone.utc)
                    try:value=request_json('https://api.open-meteo.com/v1/forecast',{})
                    except ProviderError as error:self.fail(f'Weather did not recover after Retry-After: {error.code}')
                    self.assertEqual(value,{'ok':True})
                self.assertEqual(delays,[expected]);self.assertEqual(len(requests),2)

    def test_weather_retry_limit_and_other_providers_are_preserved(self):
        real_client=httpx.Client
        for url,status,count,code in (
            ('https://api.open-meteo.com/v1/forecast',503,3,'provider_unavailable'),
            ('https://api.open-meteo.com/v1/forecast',429,3,'provider_rate_limited'),
            ('https://api.open-meteo.com/v1/forecast',400,1,'provider_unavailable'),
            ('https://router.project-osrm.org/route/v1/driving/0,0;1,1',503,1,'provider_unavailable'),
        ):
            with self.subTest(url=url,status=status):
                requests=[]
                def handle(request):requests.append(request);return httpx.Response(status,json={'error':True})
                with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=httpx.MockTransport(handle),**kwargs)),patch('routing.providers.http.time.sleep'):
                    with self.assertRaises(ProviderError) as caught:request_json(url,{})
                self.assertEqual(caught.exception.code,code);self.assertEqual(len(requests),count)

    def test_weather_backoff_cannot_exceed_the_operation_deadline(self):
        real_client=httpx.Client
        for status,headers,remaining,code in (
            (503,{},.5,'provider_timeout'),
            (429,{'Retry-After':'120'},2,'provider_rate_limited'),
        ):
            with self.subTest(status=status):
                requests=[]
                def handle(request):requests.append(request);return httpx.Response(status,json={'error':True},headers=headers)
                with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=httpx.MockTransport(handle),**kwargs)),patch('routing.providers.http.time.sleep') as wait,patch('routing.providers.http.remaining_seconds',return_value=remaining):
                    with self.assertRaises(ProviderError) as caught:request_json('https://api.open-meteo.com/v1/forecast',{})
                self.assertEqual(caught.exception.code,code);self.assertEqual(len(requests),1);wait.assert_not_called()

    def test_upstream_429_and_local_cooldown_are_distinguishable_in_logs(self):
        with patch('routing.providers.http.httpx.Client') as client, patch('routing.providers.http.time.monotonic',return_value=10):
            self.response(client,429,{'Retry-After':'120'})
            with self.assertLogs('routing.providers.http',level='INFO') as logs:
                for _ in range(2):
                    with self.assertRaises(ProviderError) as caught:
                        request_json('https://photon.komoot.io/api/',{'q':'private search'})
                    self.assertEqual(caught.exception.code,'provider_rate_limited')
                    self.assertTrue(caught.exception.retryable)
            output='\n'.join(logs.output)
            self.assertIn('provider=photon host=photon.komoot.io',output)
            self.assertIn('source=upstream status=429 attempt=1 max_attempts=1',output)
            self.assertIn('source=upstream_cooldown status=none attempt=0',output)
            self.assertNotIn('private search',output)
            self.assertEqual(client.call_count,1)

    def test_weather_logs_each_retry_without_logging_query_parameters(self):
        real_client=httpx.Client
        transport=httpx.MockTransport(lambda request:httpx.Response(429,json={'error':'private upstream body'}))
        with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=transport,**kwargs)),patch('routing.providers.http.time.sleep'),self.assertLogs('routing.providers.http',level='INFO') as logs:
            with self.assertRaises(ProviderError) as caught:
                request_json('https://api.open-meteo.com/v1/forecast',{'apikey':'private key'})
        self.assertEqual(caught.exception.code,'provider_rate_limited')
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(len(logs.output),3)
        for attempt,entry in enumerate(logs.output,1):
            self.assertIn('provider=open-meteo host=api.open-meteo.com',entry)
            self.assertIn(f'source=upstream status=429 attempt={attempt} max_attempts=3',entry)
            self.assertNotIn('private',entry)

    def test_retry_budget_logs_the_upstream_status_that_caused_it(self):
        real_client=httpx.Client
        transport=httpx.MockTransport(lambda request:httpx.Response(429,json={},headers={'Retry-After':'120'}))
        with patch('routing.providers.http.httpx.Client',side_effect=lambda **kwargs:real_client(transport=transport,**kwargs)),patch('routing.providers.http.remaining_seconds',return_value=2),patch('routing.providers.http.time.sleep') as wait,self.assertLogs('routing.providers.http',level='INFO') as logs:
            with self.assertRaises(ProviderError) as caught:
                request_json('https://api.open-meteo.com/v1/forecast',{})
        self.assertEqual(caught.exception.code,'provider_rate_limited')
        self.assertIn('source=retry_budget status=429 attempt=1',logs.output[-1])
        wait.assert_not_called()
