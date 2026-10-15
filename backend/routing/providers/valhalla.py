"""FOSSGIS Valhalla, using its annotation-aligned OSRM response format."""
import json

from routing.domain.geometry import validate_coordinate
from routing.domain.models import Coordinate, RawRoute
from .base import JsonTransport, ProviderError, invalid, mapping, sequence
from .osrm import parse_route

HOST = 'https://valhalla1.openstreetmap.de'


class ValhallaRoutingProvider:
    def __init__(self, request_json: JsonTransport):
        self.request_json = request_json

    def routes(self, origin: Coordinate, destination: Coordinate) -> tuple[RawRoute, ...]:
        validate_coordinate(origin)
        validate_coordinate(destination)
        options = {
            'locations': [{'lon': p.longitude, 'lat': p.latitude} for p in (origin, destination)],
            'costing': 'auto', 'alternates': 2, 'units': 'kilometers',
            'format': 'osrm', 'shape_format': 'geojson',
            'filters': {'action': 'include', 'attributes': ['shape_attributes.time', 'shape_attributes.length']},
        }
        # Compact JSON also avoids '+'-encoded spaces rejected by this endpoint.
        payload = mapping(self.request_json(f'{HOST}/route', {'json': json.dumps(options, separators=(',', ':'))}))
        if payload.get('code') in ('NoRoute', 'NoSegment'):
            raise ProviderError('no_route', 'No driving route was found.')
        if payload.get('code') != 'Ok':
            raise invalid()
        raw = sequence(payload.get('routes'))
        if not raw or len(raw) > 10:
            raise invalid()
        if sum(len(sequence(mapping(mapping(r).get('geometry')).get('coordinates'))) for r in raw) > 20000:
            raise invalid()
        results = {}
        for value in raw:
            # Includes leg-time reconciliation, validation and stable geometry IDs.
            route = parse_route(value)
            results.setdefault(route.route_id, route)
        return tuple(results.values())[:3]
