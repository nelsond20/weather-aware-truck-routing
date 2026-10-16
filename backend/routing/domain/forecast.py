"""Select accumulation intervals and nearest covered wind; never extrapolate."""
from dataclasses import replace
from datetime import datetime,timezone
from .models import HourlyForecast,WeatherObservation
from .risk import usable


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timezone required.")
    return value.astimezone(timezone.utc)


def select_weather(series: tuple[HourlyForecast,...], eta: datetime) -> WeatherObservation:
    eta=aware_utc(eta)
    grouped: dict[datetime,list[HourlyForecast]]={}
    for entry in series:
        entry=replace(entry,valid_at=aware_utc(entry.valid_at),
                      accumulation_start=aware_utc(entry.accumulation_start),
                      accumulation_end=aware_utc(entry.accumulation_end))
        if entry.accumulation_start>=entry.accumulation_end:
            raise ValueError("Invalid accumulation interval.")
        grouped.setdefault(entry.valid_at,[]).append(entry)
    normalized=sorted((entries[0] for entries in grouped.values()
                       if all(entry==entries[0] for entry in entries)),key=lambda entry:entry.valid_at)
    accumulation=next((entry for entry in normalized
                       if entry.accumulation_start<eta<=entry.accumulation_end),None)
    wind=None
    if normalized and normalized[0].valid_at<=eta<=normalized[-1].valid_at:
        nearest=min(normalized,key=lambda entry:(abs((entry.valid_at-eta).total_seconds()),entry.valid_at))
        if abs((nearest.valid_at-eta).total_seconds())<=1800 and usable(nearest.wind_mph):
            wind=nearest
    return WeatherObservation(wind.wind_mph if wind else None,
        accumulation.rain_in_hr if accumulation and usable(accumulation.rain_in_hr) else None,
        accumulation.snow_in_hr if accumulation and usable(accumulation.snow_in_hr) else None,
        wind.valid_at if wind else None,
        accumulation.accumulation_start if accumulation else None,
        accumulation.accumulation_end if accumulation else None)
