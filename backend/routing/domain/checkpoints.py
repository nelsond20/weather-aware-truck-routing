"""Sample annotated road distances and retain cumulative segment travel times."""
from datetime import datetime, timedelta, timezone
from math import ceil, isfinite
from .geometry import MILE_M, interpolate_coordinate, validate_coordinate
from .models import Checkpoint, Coordinate, RawRoute


def validate_route(route: RawRoute) -> tuple[float,float]:
    if len(route.geometry)<2 or len(route.segments)!=len(route.geometry)-1:
        raise ValueError("Geometry and segments must align.")
    for point in route.geometry:validate_coordinate(point)
    for index,segment in enumerate(route.segments):
        if segment.start!=route.geometry[index] or segment.end!=route.geometry[index+1]:
            raise ValueError("Segment endpoints must match geometry.")
        for value in (segment.distance_m,segment.duration_s):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<0:
                raise ValueError("Invalid route measurement.")
        if segment.distance_m==0 and segment.start!=segment.end:
            raise ValueError("Zero-distance segment cannot change location.")
    distance=sum(segment.distance_m for segment in route.segments)
    duration=sum(segment.duration_s for segment in route.segments)
    if not isfinite(distance) or not isfinite(duration) or distance<=0:
        raise ValueError("Route must have finite positive distance.")
    return distance,duration


def sample_route(route: RawRoute, departure_at: datetime, spacing_miles: int) -> tuple[Checkpoint,...]:
    total,duration=validate_route(route)
    if departure_at.tzinfo is None or departure_at.utcoffset() is None:
        raise ValueError("Departure requires an explicit timezone.")
    if isinstance(spacing_miles,bool) or spacing_miles not in (10,25,50):
        raise ValueError("Spacing must be 10, 25 or 50 miles.")
    departure_at=departure_at.astimezone(timezone.utc)
    spacing=spacing_miles*MILE_M
    count=ceil(total/spacing)
    if count+1>1000:
        raise ValueError("Sampling limit exceeded.")
    targets=[i*spacing for i in range(1,count) if i*spacing<total-1e-6]
    points=[Checkpoint(route.geometry[0],0,departure_at)]
    index=0
    distance=seconds=0.0
    for target in targets:
        while index<len(route.segments):
            segment=route.segments[index]
            if segment.distance_m>0 and distance+segment.distance_m>=target:
                break
            distance+=segment.distance_m
            seconds+=segment.duration_s
            index+=1
        segment=route.segments[index]
        fraction=(target-distance)/segment.distance_m
        points.append(Checkpoint(interpolate_coordinate(segment.start,segment.end,fraction),target,
                                 departure_at+timedelta(seconds=seconds+fraction*segment.duration_s)))
    points.append(Checkpoint(route.geometry[-1],total,departure_at+timedelta(seconds=duration)))
    return tuple(points)


def clip_route_geometry(route: RawRoute, start_m: float, end_m: float) -> tuple[Coordinate,...]:
    total,_=validate_route(route)
    if not isfinite(start_m) or not isfinite(end_m) or not 0<=start_m<end_m<=total:
        raise ValueError("Invalid clipping interval.")
    def locate(target: float) -> Coordinate:
        if target==0:return route.geometry[0]
        if target==total:return route.geometry[-1]
        distance=0.0
        for segment in route.segments:
            if segment.distance_m>0 and distance+segment.distance_m>=target:
                return interpolate_coordinate(segment.start,segment.end,(target-distance)/segment.distance_m)
            distance+=segment.distance_m
        raise ValueError("Distance outside route.")
    points=[locate(start_m)]
    distance=0.0
    for segment in route.segments:
        distance+=segment.distance_m
        if start_m<distance<end_m and segment.end!=points[-1]:points.append(segment.end)
    points.append(locate(end_m))
    return tuple(points)
