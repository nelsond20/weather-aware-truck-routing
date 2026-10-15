"""Fixed provider ports: untrusted responses cross strict parsers."""
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol
from routing.domain.models import Coordinate, RawRoute, GeocodeCandidate, HourlyForecast

JsonTransport = Callable[[str, Mapping[str, str]], object]

class ProviderError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code, self.message, self.retryable = code, message, retryable

class RoutingProvider(Protocol):
    def routes(self, origin: Coordinate, destination: Coordinate) -> tuple[RawRoute, ...]: ...

class GeocodingProvider(Protocol):
    def search(self, query: str) -> tuple[GeocodeCandidate, ...]: ...

class WeatherProvider(Protocol):
    def forecast(self, locations: tuple[Coordinate, ...], start: datetime, end: datetime) -> dict[Coordinate, tuple[HourlyForecast, ...]]: ...


def invalid() -> ProviderError:
    return ProviderError('provider_contract_invalid', 'Provider returned invalid data.')


def mapping(value: object) -> dict:
    if not isinstance(value, dict):
        raise invalid()
    return value


def sequence(value: object) -> list:
    if not isinstance(value, list):
        raise invalid()
    return value
