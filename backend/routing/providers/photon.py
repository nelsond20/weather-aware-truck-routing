"""Photon public geocoding, retaining the app's explicit candidate contract."""
from routing.domain.models import GeocodeCandidate
from .base import JsonTransport, mapping, sequence, invalid
from .osrm import coordinate


class PhotonGeocodingProvider:
    cache_allowed = False

    def __init__(self, request_json: JsonTransport):
        self.request_json = request_json

    def search(self, query: str) -> tuple[GeocodeCandidate, ...]:
        query = query.strip()
        if not 2 <= len(query) <= 200 or ';' in query or len(query.split()) > 20:
            raise ValueError('Invalid geocoding query')
        payload = mapping(self.request_json('https://photon.komoot.io/api/', {
            'q': query, 'limit': '5', 'lang': 'en'}))
        if payload.get('type') != 'FeatureCollection':
            raise invalid()
        features = sequence(payload.get('features'))
        if len(features) > 5:
            raise invalid()
        candidates = {}
        for value in features:
            feature = mapping(value)
            props, geometry = mapping(feature.get('properties')), mapping(feature.get('geometry'))
            osm_type, osm_id = props.get('osm_type'), props.get('osm_id')
            if (feature.get('type') != 'Feature' or geometry.get('type') != 'Point'
                    or osm_type not in ('N', 'W', 'R') or isinstance(osm_id, bool)
                    or not isinstance(osm_id, int) or not 0 < osm_id < 10**20):
                raise invalid()
            address = {}
            for field in ('name', 'housenumber', 'street', 'city', 'district', 'state', 'country'):
                text = props.get(field, '')
                if not isinstance(text, str) or len(text) > 500:
                    raise invalid()
                address[field] = text.strip()
            street = ' '.join(filter(None, (address['housenumber'], address['street'])))
            parts = (address['name'], street, address['city'], address['district'], address['state'], address['country'])
            label = ', '.join(dict.fromkeys(part for part in parts if part))[:500]
            if not label:
                raise invalid()
            identifier = f'photon:{osm_type}:{osm_id}'
            candidates.setdefault(identifier, GeocodeCandidate(identifier, label, coordinate(geometry.get('coordinates'))))
        return tuple(candidates.values())
