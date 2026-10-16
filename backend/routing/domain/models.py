"""Immutable public domain contracts; units are metres, seconds and UTC."""
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

@dataclass(frozen=True)
class Coordinate:
    longitude: float
    latitude: float

@dataclass(frozen=True)
class RouteSegment:
    start: Coordinate
    end: Coordinate
    distance_m: float
    duration_s: float

@dataclass(frozen=True)
class RawRoute:
    route_id: str
    geometry: tuple[Coordinate, ...]
    segments: tuple[RouteSegment, ...]
    eta_approximate: bool = False

@dataclass(frozen=True)
class Checkpoint:
    coordinate: Coordinate
    distance_m: float
    eta: datetime

@dataclass(frozen=True)
class HourlyForecast:
    valid_at: datetime
    accumulation_start: datetime
    accumulation_end: datetime
    wind_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None

@dataclass(frozen=True)
class WeatherObservation:
    wind_mph: float | None
    rain_in_hr: float | None
    snow_in_hr: float | None
    wind_valid_at: datetime | None
    accumulation_start: datetime | None
    accumulation_end: datetime | None

@dataclass(frozen=True)
class CheckpointRisk:
    level: RiskLevel | None
    known_max: RiskLevel | None
    wind_level: RiskLevel | None
    rain_level: RiskLevel | None
    snow_level: RiskLevel | None
    missing_fields: tuple[str, ...]
    reasons: tuple[str, ...]

@dataclass(frozen=True)
class RouteInterval:
    start: Checkpoint
    end: Checkpoint
    level: RiskLevel | None

@dataclass(frozen=True)
class RouteEvaluation:
    route: RawRoute
    checkpoints: tuple[Checkpoint, ...]
    observations: tuple[WeatherObservation, ...]
    risks: tuple[CheckpointRisk, ...]
    intervals: tuple[RouteInterval, ...]
    miles_by_level: dict[RiskLevel, float]
    unknown_miles: float
    average_risk: float | None
    blocked: bool
    complete: bool

@dataclass(frozen=True)
class Recommendation:
    route_id: str | None
    status: str  # recommended | all_blocked | insufficient_data | no_routes
    ranked_route_ids: tuple[str, ...]
    deciding_criterion: str | None
    comparison_criteria: dict[str, str]

@dataclass(frozen=True)
class TripRequest:
    origin: Coordinate
    destination: Coordinate
    departure_at: datetime
    load_lb: float
    spacing_miles: int

@dataclass(frozen=True)
class TripEvaluation:
    routes: tuple[RouteEvaluation, ...]
    recommendation: Recommendation
    warnings: tuple[str, ...]

@dataclass(frozen=True)
class GeocodeCandidate:
    candidate_id: str
    label: str
    coordinate: Coordinate

@dataclass(frozen=True)
class CorridorGrid:
    locations: tuple[Coordinate,...]
    width_miles: float
    resolution_m: float

@dataclass(frozen=True)
class CorridorFrame:
    valid_at: datetime
    risks: tuple[CheckpointRisk,...]

@dataclass(frozen=True)
class CorridorForecast:
    base_time: datetime
    grid: CorridorGrid
    frames: tuple[CorridorFrame,...]
