"""Compose the shared domain; never cache classifications."""
import logging
import math
from routing.domain.models import TripRequest, TripEvaluation
from routing.domain.checkpoints import sample_route, validate_route
from routing.domain.geometry import MILE_M
from routing.domain.forecast import select_weather
from routing.domain.recommendation import evaluate_route, recommend_routes
from routing.providers.base import RoutingProvider, WeatherProvider, ProviderError
from .cache import RawDataCache, CachedWeatherProvider, route_cache_key
from .budget import check_deadline

logger = logging.getLogger(__name__)

class TripService:
    def __init__(self, routing: RoutingProvider, weather: WeatherProvider, cache: RawDataCache, mode: str, routing_provider='osrm'):
        self.routing, self.weather, self.cache, self.mode = routing, CachedWeatherProvider(weather,cache,mode), cache, mode
        self.routing_provider = routing_provider

    def evaluate(self, request: TripRequest) -> TripEvaluation:
        check_deadline()
        routes = self.cache.get_or_load(route_cache_key(request.origin,request.destination,self.mode,self.routing_provider),
                  lambda:self.routing.routes(request.origin,request.destination),3600)
        if not routes:
            raise ProviderError('no_route','No driving route was found.')
        totals = [validate_route(route)[0] for route in routes]
        if len(routes)>3 or sum(len(r.geometry) for r in routes)>20000:
            raise ProviderError('provider_contract_invalid','Provider returned invalid data.')
        if sum(math.ceil(total/(request.spacing_miles*MILE_M))+1 for total in totals)>1000:
            raise ProviderError('sampling_limit_exceeded','Too many checkpoints. Choose 25 or 50 miles.')
        samples = [sample_route(route,request.departure_at,request.spacing_miles) for route in routes]
        points = tuple(dict.fromkeys(cp.coordinate for group in samples for cp in group))
        start, end = min(cp.eta for group in samples for cp in group), max(cp.eta for group in samples for cp in group)
        check_deadline()
        forecasts = self.weather.forecast(points,start,end)
        check_deadline()
        if not forecasts:
            raise ProviderError('weather_unavailable','Weather is unavailable.',True)
        evaluations = tuple(evaluate_route(route,cps,tuple(select_weather(forecasts.get(cp.coordinate,()),cp.eta) for cp in cps),request.load_lb) for route,cps in zip(routes,samples))
        warnings = []
        if len(routes)<3:warnings.append('fewer_than_three_routes')
        if any(r.eta_approximate for r in routes):warnings.append('eta_approximate')
        if any(not result.complete for result in evaluations):warnings.append('weather_coverage_incomplete')
        return TripEvaluation(evaluations,recommend_routes(evaluations),tuple(warnings))


def build_services(mode: str):
    from django.conf import settings
    from types import SimpleNamespace
    from django.core.cache import cache as django_cache
    from .corridor import CorridorService
    routing_provider = 'osrm'
    if mode == 'demo':
        from routing.providers.demo import DemoRoutingProvider,DemoWeatherProvider,DemoGeocodingProvider
        routing,weather,geocoding = DemoRoutingProvider(),DemoWeatherProvider(),DemoGeocodingProvider()
    elif mode == 'live':
        from routing.providers.osrm import OSRMRoutingProvider
        from routing.providers.valhalla import ValhallaRoutingProvider
        from routing.providers.photon import PhotonGeocodingProvider
        from routing.providers.open_meteo import OpenMeteoWeatherProvider
        from routing.providers.http import request_json
        routing_provider = settings.LIVE_ROUTING_PROVIDER
        routing = (ValhallaRoutingProvider if routing_provider == 'valhalla' else OSRMRoutingProvider)(request_json)
        weather,geocoding=OpenMeteoWeatherProvider(request_json),PhotonGeocodingProvider(request_json)
    else:
        raise ValueError('PROVIDER_MODE must be demo or live.')
    logger.info('provider_configuration mode=%s configured_routing_provider=%s active_routing_provider=%s weather_provider=%s geocoding_provider=%s',
                mode,settings.LIVE_ROUTING_PROVIDER,type(routing).__name__,type(weather).__name__,type(geocoding).__name__)
    cache = RawDataCache(django_cache)
    return SimpleNamespace(trip=TripService(routing,weather,cache,mode,routing_provider),corridor=CorridorService(weather,cache,mode),geocoding=geocoding,mode=mode)
