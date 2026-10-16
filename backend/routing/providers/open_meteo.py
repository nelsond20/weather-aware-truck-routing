"""Open-Meteo hourly contract; rain and snow are preceding-hour amounts."""
from datetime import datetime, timedelta, timezone
from routing.domain.forecast import aware_utc
from routing.domain.models import Coordinate, HourlyForecast
from routing.domain.geometry import haversine_m, validate_coordinate
from routing.domain.risk import usable
from .base import JsonTransport, ProviderError, mapping, sequence, invalid
from .osrm import coordinate


def fetch_dates(start: datetime, end: datetime) -> tuple[str, str]:
    start, end = aware_utc(start), aware_utc(end)
    if start > end:
        raise ValueError('Invalid forecast window')
    return ((start-timedelta(hours=1)).date().isoformat(), (end+timedelta(hours=1)).date().isoformat())


def parse_series(value: object, requested: Coordinate) -> tuple[HourlyForecast, ...]:
    data = mapping(value)
    grid = coordinate([data.get('longitude'), data.get('latitude')])
    # Grid snapping is allowed; a distant or reordered response is not.
    if haversine_m(grid, requested) > 10000 or data.get('utc_offset_seconds', 0) != 0:
        raise invalid()
    units, hourly = mapping(data.get('hourly_units')), mapping(data.get('hourly'))
    for field, unit in (('time','iso8601'),('wind_speed_10m','mp/h'),('rain','mm'),('snowfall','cm')):
        if units.get(field) != unit:
            raise invalid()
    times = sequence(hourly.get('time'))
    if len(times) > 1000:
        raise invalid()
    arrays = {}
    for field in ('wind_speed_10m','rain','snowfall'):
        arrays[field] = sequence(hourly[field]) if field in hourly else []
    result = []
    for index, value in enumerate(times):
        if not isinstance(value, str) or len(value) != 16:
            raise invalid()
        try:
            instant = datetime.strptime(value, '%Y-%m-%dT%H:%M').replace(tzinfo=timezone.utc)
        except ValueError:
            raise invalid() from None
        def amount(field, divisor):
            array = arrays[field]
            value = array[index] if index < len(array) else None
            return value/divisor if usable(value) else None
        result.append(HourlyForecast(instant,instant-timedelta(hours=1),instant,
                                    amount('wind_speed_10m',1),amount('rain',25.4),amount('snowfall',2.54)))
    return tuple(result)


class OpenMeteoWeatherProvider:
    def __init__(self, request_json: JsonTransport):
        self.request_json = request_json

    def forecast(self, locations: tuple[Coordinate, ...], start: datetime, end: datetime) -> dict[Coordinate, tuple[HourlyForecast, ...]]:
        start_date, end_date = fetch_dates(start, end)
        points = tuple(dict.fromkeys(locations))
        for point in points:
            validate_coordinate(point)
        result = {}
        first_error = None
        for offset in range(0,len(points),25):
            batch = points[offset:offset+25]
            params = {'latitude':','.join(str(p.latitude) for p in batch),
                      'longitude':','.join(str(p.longitude) for p in batch),
                      'hourly':'wind_speed_10m,rain,snowfall','wind_speed_unit':'mph',
                      'precipitation_unit':'mm','timezone':'UTC',
                      'start_date':start_date,'end_date':end_date}
            try:
                payload = self.request_json('https://api.open-meteo.com/v1/forecast',params)
                values = [payload] if isinstance(payload,dict) and len(batch)==1 else sequence(payload)
                if len(values) != len(batch):
                    raise invalid()
                parsed = {point:parse_series(value,point) for point,value in zip(batch,values)}
                result.update(parsed)
            except ProviderError as error:
                first_error = first_error or error
        if points and not result and first_error:
            raise first_error
        return result
