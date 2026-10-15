"""Conservative mileage exposure and lexicographic, explainable route ranking."""
from math import isclose,isfinite
from .checkpoints import validate_route
from .geometry import MILE_M
from .models import Checkpoint,RawRoute,Recommendation,RiskLevel,RouteEvaluation,RouteInterval,WeatherObservation
from .risk import assess_weather


def evaluate_route(route: RawRoute, checkpoints: tuple[Checkpoint,...], observations: tuple[WeatherObservation,...], load_lb: float) -> RouteEvaluation:
    total,_=validate_route(route)
    if len(checkpoints)<2 or len(checkpoints)!=len(observations):
        raise ValueError("Checkpoint/observation counts must match.")
    if not isclose(checkpoints[0].distance_m,0,abs_tol=1e-6) or not isclose(checkpoints[-1].distance_m,total,rel_tol=0,abs_tol=1e-6):
        raise ValueError("Checkpoints must cover the full route.")
    for left,right in zip(checkpoints,checkpoints[1:]):
        if not isfinite(right.distance_m) or right.distance_m<=left.distance_m:
            raise ValueError("Checkpoint distances must increase.")
    risks=tuple(assess_weather(observation,load_lb) for observation in observations)
    mileage={level:0.0 for level in RiskLevel}
    unknown=0.0
    intervals=[]
    for index,(left,right) in enumerate(zip(checkpoints,checkpoints[1:])):
        first,last=risks[index].level,risks[index+1].level
        level=max(first,last) if first is not None and last is not None else None
        miles=(right.distance_m-left.distance_m)/MILE_M
        if level is None:unknown+=miles
        else:
            mileage[level]+=miles
        intervals.append(RouteInterval(left,right,level))
    complete=all(risk.level is not None for risk in risks)
    blocked=any(risk.known_max==RiskLevel.NO_TRAVEL for risk in risks)
    known_miles=sum(mileage.values())
    # Normalize the same exposure buckets used by the numerator. This preserves
    # uniform scores exactly and avoids out-of-range drift from a second total.
    average=sum(int(level)*(miles/known_miles) for level,miles in mileage.items()) if complete else None
    return RouteEvaluation(route,checkpoints,observations,risks,tuple(intervals),mileage,unknown,
                           average,blocked,complete)


def _metrics(route: RouteEvaluation) -> tuple[float,float,float,float]:
    if route.average_risk is None:
        raise ValueError("Incomplete route is not rankable.")
    return (route.miles_by_level[RiskLevel.SEVERE],route.miles_by_level[RiskLevel.HIGH],
            route.average_risk,sum(segment.duration_s for segment in route.route.segments))


def _criterion(winner: RouteEvaluation, other: RouteEvaluation) -> str:
    for name,first,last in zip(('severe_miles','high_miles','average_risk','duration_seconds'),_metrics(winner),_metrics(other)):
        if first!=last:return name
    return 'stable_tie'


def recommend_routes(routes: tuple[RouteEvaluation,...]) -> Recommendation:
    if len({route.route.route_id for route in routes})!=len(routes):
        raise ValueError("Route IDs must be unique.")
    ranked=sorted((route for route in routes if route.complete and not route.blocked),
                  key=lambda route:(*_metrics(route),route.route.route_id))
    if not ranked:
        status='no_routes' if not routes else ('all_blocked' if all(route.blocked for route in routes) else 'insufficient_data')
        return Recommendation(None,status,(),None,{})
    winner=ranked[0]
    deciding=_criterion(winner,ranked[1]) if len(ranked)>1 else 'only_eligible_route'
    comparisons={route.route.route_id:('blocked' if route.blocked else 'incomplete' if not route.complete else _criterion(winner,route))
                 for route in routes if route.route.route_id!=winner.route.route_id}
    return Recommendation(winner.route.route_id,'recommended',tuple(route.route.route_id for route in ranked),deciding,comparisons)
