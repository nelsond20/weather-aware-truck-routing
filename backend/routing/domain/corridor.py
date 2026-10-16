"""Bounded transverse bands following geodesic road stations."""
import math
from .models import Coordinate,RawRoute,CorridorGrid
from .geometry import EARTH_RADIUS_M,MILE_M,interpolate_coordinate
from .checkpoints import validate_route

def bearing(a,b):
    lat1,lat2=math.radians(a.latitude),math.radians(b.latitude)
    delta=math.radians(b.longitude-a.longitude)
    return math.atan2(math.sin(delta)*math.cos(lat2),math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(delta))

def offset(point,distance,heading):
    lat,lon=math.radians(point.latitude),math.radians(point.longitude)
    angle=distance/EARTH_RADIUS_M
    target_lat=math.asin(max(-1,min(1,math.sin(lat)*math.cos(angle)+math.cos(lat)*math.sin(angle)*math.cos(heading))))
    target_lon=lon+math.atan2(math.sin(heading)*math.sin(angle)*math.cos(lat),math.cos(angle)-math.sin(lat)*math.sin(target_lat))
    return Coordinate((math.degrees(target_lon)+180)%360-180,math.degrees(target_lat))

def build_corridor(routes:tuple[RawRoute,...],width_miles:float=20,max_locations:int=150)->CorridorGrid:
    if not routes or len(routes)>3 or not math.isfinite(width_miles) or width_miles<=0 or max_locations<30:
        raise ValueError('Invalid corridor input')
    unique=tuple({r.geometry:r for r in routes}.values())
    station_count=max(2,max_locations//(len(unique)*5))
    points={};resolution=0
    for route in unique:
        total,_=validate_route(route)
        spacing=total/(station_count-1);resolution=max(resolution,spacing)
        segment_index=0;distance=0
        for i in range(station_count):
            target=i*spacing
            while segment_index<len(route.segments)-1 and (route.segments[segment_index].distance_m==0 or distance+route.segments[segment_index].distance_m<target):
                distance+=route.segments[segment_index].distance_m;segment_index+=1
            segment=route.segments[segment_index]
            fraction=min(1,max(0,(target-distance)/segment.distance_m)) if segment.distance_m else 0
            center=interpolate_coordinate(segment.start,segment.end,fraction)
            heading=bearing(segment.start,segment.end)
            for multiplier in (-1,-.5,0,.5,1):
                point=center if multiplier==0 else offset(center,abs(multiplier)*width_miles*MILE_M,heading+(math.pi/2 if multiplier>0 else -math.pi/2))
                points.setdefault(point,None)
    return CorridorGrid(tuple(points),width_miles,resolution)
