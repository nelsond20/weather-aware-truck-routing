"""Fixed hosts/paths, no redirects/proxies, bounded decoded responses."""
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from urllib.parse import urlsplit
import httpx
from .base import ProviderError
from routing.services.budget import check_deadline,remaining_seconds

USER_AGENT = 'WeatherAwareTruckRouting/0.1 (Spotter assessment/demo)'
PUBLIC_HOSTS = ('router.project-osrm.org', 'photon.komoot.io', 'valhalla1.openstreetmap.de')
_public_lock = Lock()
_last_public_request = {}
_public_cooldown = {}


def request_json(url,params):
    parsed=urlsplit(url)
    allowed=(parsed.hostname=='router.project-osrm.org' and parsed.path.startswith('/route/v1/driving/')) or (parsed.hostname=='photon.komoot.io' and parsed.path=='/api/') or (parsed.hostname=='api.open-meteo.com' and parsed.path=='/v1/forecast') or (parsed.hostname=='valhalla1.openstreetmap.de' and parsed.path=='/route')
    if parsed.scheme!='https' or parsed.port not in (None,443) or parsed.username or parsed.password or parsed.query or parsed.fragment or not allowed:
        raise ProviderError('provider_contract_invalid','Provider destination is not allowed.')
    check_deadline()
    if parsed.hostname in PUBLIC_HOSTS:
        # One worker, at most one request/second per public service, across users.
        with _public_lock:
            now = time.monotonic()
            if now < _public_cooldown.get(parsed.hostname, 0):
                raise ProviderError('provider_rate_limited','Provider quota is unavailable.',True)
            delay = max(0, _last_public_request.get(parsed.hostname, -1) + 1 - now)
            if delay >= remaining_seconds():
                raise ProviderError('provider_timeout','Provider timed out.',True)
            if delay:
                time.sleep(delay)
            check_deadline()
            _last_public_request[parsed.hostname] = time.monotonic()
    try:
        headers = {'User-Agent': USER_AGENT}
        if parsed.hostname == 'valhalla1.openstreetmap.de':
            headers['X-Client-Id'] = 'weather-aware-truck-routing-spotter-assessment'
        with httpx.Client(follow_redirects=False,trust_env=False,timeout=min(15,remaining_seconds()),headers=headers) as client:
            weather = parsed.hostname == 'api.open-meteo.com'
            for attempt in range(3 if weather else 1):
                check_deadline()
                if weather:
                    # Recompute after every backoff so retries share the operation budget.
                    available = remaining_seconds()
                    client.timeout = httpx.Timeout(min(20,available),connect=min(5,available))
                with client.stream('GET',url,params=params) as response:
                    if weather and response.status_code in (429,502,503,504) and attempt < 2:
                        delay = 2 ** attempt
                        retry = response.headers.get('Retry-After', '')
                        try:
                            retry_delay = int(retry)
                        except ValueError:
                            try:
                                retry_delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                            except (ValueError,TypeError,OverflowError):
                                retry_delay = 0
                        delay = max(delay,retry_delay)
                        if delay >= remaining_seconds():
                            if response.status_code == 429:
                                raise ProviderError('provider_rate_limited','Provider quota is unavailable.',True)
                            raise ProviderError('provider_timeout','Provider retry exceeds its time limit.',True)
                    else:
                        if response.status_code==429:
                            if parsed.hostname in PUBLIC_HOSTS:
                                retry = response.headers.get('Retry-After', '60')
                                try:
                                    delay = int(retry)
                                except ValueError:
                                    try:
                                        delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                                    except (ValueError, TypeError, OverflowError):
                                        delay = 60
                                with _public_lock:
                                    _public_cooldown[parsed.hostname] = time.monotonic() + max(1, delay)
                            raise ProviderError('provider_rate_limited','Provider quota is unavailable.',True)
                        # Valhalla returns structured route-limit errors with HTTP 400.
                        routing_error = parsed.hostname=='valhalla1.openstreetmap.de' and response.status_code==400
                        if response.status_code!=200 and not routing_error:
                            raise ProviderError('provider_unavailable','Provider is unavailable.',True)
                        content=bytearray()
                        for chunk in response.iter_bytes():
                            check_deadline()
                            if len(content)+len(chunk)>8*1024*1024:
                                raise ProviderError('provider_contract_invalid','Provider response exceeds size limit.')
                            content.extend(chunk)
                        return json.loads(content,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
                # Release the failed response/connection before waiting to retry.
                time.sleep(delay)
    except httpx.TimeoutException:
        raise ProviderError('provider_timeout','Provider timed out.',True) from None
    except httpx.HTTPError:
        raise ProviderError('provider_unavailable','Provider is unavailable.',True) from None
    except (ValueError,UnicodeError):
        raise ProviderError('provider_contract_invalid','Provider returned invalid JSON.') from None
