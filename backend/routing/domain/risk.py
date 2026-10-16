"""Weather/load classification in mph, inches per hour and pounds."""
from math import isfinite
from .models import CheckpointRisk, RiskLevel, WeatherObservation


def usable(value: float | None) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0


def classify_wind(value: float | None, load_lb: float) -> RiskLevel | None:
    if not usable(load_lb):
        raise ValueError("Load must be finite and nonnegative.")
    if not usable(value):
        return None
    if value >= 55:
        return RiskLevel.NO_TRAVEL
    if value >= 45:
        return RiskLevel.NO_TRAVEL if load_lb > 30000 else RiskLevel.SEVERE
    if value >= 35:
        return RiskLevel.SEVERE if load_lb > 40000 else RiskLevel.HIGH
    return RiskLevel.MODERATE if value >= 25 else RiskLevel.LOW


def classify_rain(value: float | None) -> RiskLevel | None:
    if not usable(value):
        return None
    if value > 1:
        return RiskLevel.NO_TRAVEL
    if value >= .5:
        return RiskLevel.SEVERE
    if value >= .25:
        return RiskLevel.HIGH
    return RiskLevel.MODERATE if value >= .1 else RiskLevel.LOW


def classify_snow(value: float | None) -> RiskLevel | None:
    if not usable(value):
        return None
    if value > 3:
        return RiskLevel.NO_TRAVEL
    if value >= 2:
        return RiskLevel.SEVERE
    if value >= 1:
        return RiskLevel.HIGH
    return RiskLevel.MODERATE if value >= .5 else RiskLevel.LOW


def assess_weather(observation: WeatherObservation, load_lb: float) -> CheckpointRisk:
    levels = (classify_wind(observation.wind_mph, load_lb),
              classify_rain(observation.rain_in_hr), classify_snow(observation.snow_in_hr))
    names = ("wind", "rain", "snow")
    known = [level for level in levels if level is not None]
    missing = tuple(name for name, level in zip(names, levels) if level is None)
    known_max = max(known) if known else None
    reasons = tuple(f"{name}: {level.name.lower().replace('_', ' ')}"
                    for name, level in zip(names, levels)
                    if level is not None and level > RiskLevel.LOW)
    if levels[0] is not None and usable(observation.wind_mph):
        wind = observation.wind_mph
        if 45 <= wind < 55 and load_lb > 30000:
            reasons += ("Wind at least 45 mph with load above 30,000 lb: no travel.",)
        elif 35 <= wind < 45 and load_lb > 40000:
            reasons += ("Wind at least 35 mph with load above 40,000 lb: severe.",)
    return CheckpointRisk(None if missing else known_max, known_max, *levels, missing, reasons)
