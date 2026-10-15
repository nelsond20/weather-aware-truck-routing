"""Raw data only: load never participates in cache keys."""
import hashlib
import json
import time
from collections.abc import Callable
from datetime import datetime
from typing import TypeVar, Protocol
from routing.domain.models import Coordinate, HourlyForecast
from routing.providers.open_meteo import fetch_dates
from routing.providers.base import WeatherProvider

T = TypeVar('T')
_MISSING = object()

class CacheBackend(Protocol):
    def get(self, key: str, default: object = None) -> object: ...
    def set(self, key: str, value: object, timeout: int) -> None: ...

class MemoryCache:
    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock, self.entries = clock, {}

    def get(self, key: str, default: object = None) -> object:
        entry = self.entries.get(key)
        if entry is None or entry[0] <= self.clock():
            self.entries.pop(key,None)
            return default
        return entry[1]

    def set(self, key: str, value: object, timeout: int) -> None:
        self.entries[key] = (self.clock()+timeout,value)

class RawDataCache:
    def __init__(self, backend: CacheBackend):
        self.backend = backend

    def get_or_load(self, key: str, loader: Callable[[], T], ttl_s: int) -> T:
        cached = self.backend.get(key,_MISSING)
        if cached is not _MISSING:
            return cached
        value = loader()
        self.backend.set(key,value,ttl_s)
        return value


def digest(kind, value):
    return kind+':'+hashlib.sha256(json.dumps(value,separators=(',',':')).encode()).hexdigest()


def forecast_cache_key(coordinate: Coordinate, start: datetime, end: datetime, mode='live') -> str:
    return digest('weather-v1',(mode,'open-meteo','wind_speed_10m,rain,snowfall','mph,mm,cm',coordinate.longitude,coordinate.latitude,*fetch_dates(start,end)))


def route_cache_key(origin: Coordinate, destination: Coordinate, mode='live', provider='osrm') -> str:
    return digest('route-v1',(mode,provider+'-v1-driving',origin.longitude,origin.latitude,destination.longitude,destination.latitude))


def geocode_cache_key(query: str, mode='live') -> str:
    return digest('geocode-v1',(mode,'photon',query.strip()))


class CachedWeatherProvider:
    def __init__(self, provider: WeatherProvider, cache: RawDataCache, mode: str):
        self.provider, self.cache, self.mode = provider, cache, mode

    def forecast(self, locations: tuple[Coordinate,...], start: datetime, end: datetime) -> dict[Coordinate,tuple[HourlyForecast,...]]:
        result, missing = {}, []
        for point in dict.fromkeys(locations):
            value = self.cache.backend.get(forecast_cache_key(point,start,end,self.mode),_MISSING)
            if value is _MISSING:
                missing.append(point)
            else:
                result[point] = value
        if missing:
            fresh = self.provider.forecast(tuple(missing),start,end)
            for point, series in fresh.items():
                if point not in missing:
                    raise ValueError('Unexpected forecast location')
                self.cache.backend.set(forecast_cache_key(point,start,end,self.mode),series,900)
            result.update(fresh)
        return result
