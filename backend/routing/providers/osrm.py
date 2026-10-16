"""OSRM public demo routing, normalized to the existing road-segment contract."""
import hashlib
import json
import math
from routing.domain.geometry import validate_coordinate
from routing.domain.checkpoints import validate_route
from routing.domain.models import Coordinate, RawRoute, RouteSegment
from .base import JsonTransport, ProviderError, mapping, sequence, invalid

HOST = 'https://router.project-osrm.org'


def number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise invalid()
    return float(value)


def coordinate(value: object) -> Coordinate:
    pair = sequence(value)
    if len(pair) != 2:
        raise invalid()
    point = Coordinate(pair[0], pair[1])
    try:
        validate_coordinate(point)
    except (ValueError, TypeError):
        raise invalid() from None
    return point


def parse_route(value: object) -> RawRoute:
    data = mapping(value)
    geometry = mapping(data.get('geometry'))
    if geometry.get('type') != 'LineString':
        raise invalid()
    points = tuple(coordinate(p) for p in sequence(geometry.get('coordinates')))
    if not 2 <= len(points) <= 20000:
        raise invalid()
    distances, durations = [], []
    approximate = False
    for leg in sequence(data.get('legs')):
        leg = mapping(leg)
        annotation = mapping(leg.get('annotation'))
        distances.extend(number(x) for x in sequence(annotation.get('distance')))
        annotated = [number(x) for x in sequence(annotation.get('duration'))]
        total = sum(annotated)
        reported = number(leg.get('duration'))
        if total == 0 and reported != 0:
            raise invalid()
        # OSRM annotations exclude turns. Spread their time proportionally within
        # each leg so cumulative ETAs retain the reported total travel time.
        approximate = approximate or not math.isclose(total, reported, abs_tol=1e-6)
        durations.extend(value * reported / total if total else 0 for value in annotated)
    if len(distances) != len(points)-1 or len(durations) != len(distances):
        raise invalid()
    for values, field, tolerance in ((distances, 'distance', 5), (durations, 'duration', 1)):
        total = number(data.get(field))
        if abs(sum(values)-total) > max(tolerance, total*.005):
            raise invalid()
    digest = hashlib.sha256(json.dumps([[p.longitude, p.latitude] for p in points], separators=(',', ':')).encode()).hexdigest()[:24]
    route = RawRoute(digest, points, tuple(RouteSegment(a,b,d,t) for a,b,d,t in zip(points, points[1:], distances, durations)), approximate)
    try:
        validate_route(route)
    except ValueError:
        raise invalid() from None
    return route


class OSRMRoutingProvider:
    def __init__(self, request_json: JsonTransport):
        self.request_json = request_json

    def routes(self, origin: Coordinate, destination: Coordinate) -> tuple[RawRoute, ...]:
        validate_coordinate(origin)
        validate_coordinate(destination)
        path = f'{origin.longitude},{origin.latitude};{destination.longitude},{destination.latitude}'
        payload = mapping(self.request_json(f'{HOST}/route/v1/driving/{path}', {
            'alternatives': '2', 'overview': 'full',
            'geometries': 'geojson', 'annotations': 'distance,duration'}))
        if payload.get('code') in ('NoRoute', 'NoSegment'):
            raise ProviderError('no_route', 'No driving route was found.')
        if payload.get('code') != 'Ok':
            raise invalid()
        results = {}
        raw = sequence(payload.get('routes'))
        if not raw or len(raw) > 10:
            raise invalid()
        if sum(len(sequence(mapping(mapping(r).get('geometry')).get('coordinates'))) for r in raw) > 20000:
            raise invalid()
        for value in raw:
            route = parse_route(value)
            results.setdefault(route.route_id, route)
        return tuple(results.values())[:3]


