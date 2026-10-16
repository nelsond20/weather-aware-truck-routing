"""Geodesic operations preserve the short arc across the antimeridian."""
from math import acos, asin, atan2, cos, degrees, isfinite, radians, sin, sqrt
from .models import Coordinate

EARTH_RADIUS_M = 6371008.8
MILE_M = 1609.344


def validate_coordinate(point: Coordinate) -> None:
    for value, maximum in ((point.longitude,180),(point.latitude,90)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or abs(value)>maximum:
            raise ValueError("Invalid coordinate.")


def haversine_m(start: Coordinate, end: Coordinate) -> float:
    validate_coordinate(start)
    validate_coordinate(end)
    lat1,lat2=radians(start.latitude),radians(end.latitude)
    dlat=lat2-lat1
    dlon=radians(end.longitude-start.longitude)
    value=sin(dlat/2)**2+cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 2*EARTH_RADIUS_M*asin(sqrt(min(1,max(0,value))))


def interpolate_coordinate(start: Coordinate, end: Coordinate, fraction: float) -> Coordinate:
    validate_coordinate(start)
    validate_coordinate(end)
    if not isfinite(fraction) or not 0<=fraction<=1:
        raise ValueError("Fraction outside segment.")
    if fraction==0:return start
    if fraction==1:return end
    def vector(point: Coordinate) -> tuple[float,float,float]:
        lat,lon=radians(point.latitude),radians(point.longitude)
        return cos(lat)*cos(lon),cos(lat)*sin(lon),sin(lat)
    a,b=vector(start),vector(end)
    angle=acos(max(-1,min(1,sum(x*y for x,y in zip(a,b)))))
    if angle<1e-10:return start
    if abs(sin(angle))<1e-10:
        raise ValueError("Antipodal segment has no unique short arc.")
    left,right=sin((1-fraction)*angle)/sin(angle),sin(fraction*angle)/sin(angle)
    x,y,z=(left*u+right*v for u,v in zip(a,b))
    return Coordinate((degrees(atan2(y,x))+180)%360-180,degrees(atan2(z,sqrt(x*x+y*y))))
