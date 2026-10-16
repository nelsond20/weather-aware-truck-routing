"""Synthetic coordinates and weather; classification always uses the domain."""
from datetime import datetime,timedelta,timezone
from routing.domain.models import Coordinate,RawRoute,RouteSegment,GeocodeCandidate,HourlyForecast
from routing.domain.geometry import haversine_m
from .open_meteo import fetch_dates

ORIGIN=Coordinate(-100,40)
DESTINATION=Coordinate(-98,40)
DEMO_WIND_BY_ROUTE={'demo-north':45.0,'demo-central':35.0,'demo-south':20.0}
DEMO_DURATION_SECONDS={'demo-north':10800,'demo-central':12600,'demo-south':14400}

class DemoRoutingProvider:
    def __init__(self,alternatives=3):self.alternatives=alternatives
    def routes(self,origin,destination):
        if origin!=ORIGIN or destination!=DESTINATION:
            from .base import ProviderError
            raise ProviderError('no_route','Demo supports West Depot to East Depot.')
        result=[]
        for identifier,latitude in (('demo-north',40.4),('demo-central',40.05),('demo-south',39.6)):
            points=(origin,Coordinate(-99.8,latitude),Coordinate(-99,latitude),Coordinate(-98.2,latitude),destination)
            lengths=[haversine_m(a,b) for a,b in zip(points,points[1:])];total=sum(lengths)
            segments=tuple(RouteSegment(a,b,d,DEMO_DURATION_SECONDS[identifier]*d/total) for a,b,d in zip(points,points[1:],lengths))
            result.append(RawRoute(identifier,points,segments))
        return tuple(result[:self.alternatives])

class DemoGeocodingProvider:
    cache_allowed=True
    def search(self,query):
        values=(GeocodeCandidate('demo-west','West Depot · Synthetic origin',ORIGIN),GeocodeCandidate('demo-east','East Depot · Synthetic destination',DESTINATION))
        return tuple(c for c in values if query.strip().casefold() in c.label.casefold())

class DemoWeatherProvider:
    def __init__(self,wind_override=None,missing_snow=False):self.wind_override,self.missing_snow=wind_override,missing_snow
    def forecast(self,locations,start,end):
        first,last=fetch_dates(start,end)
        base=datetime.fromisoformat(first).replace(tzinfo=timezone.utc)
        final=datetime.fromisoformat(last).replace(tzinfo=timezone.utc)+timedelta(days=1)
        count=int((final-base).total_seconds()/3600)
        result={}
        for point in locations:
            wind=self.wind_override if self.wind_override is not None else 45 if point.latitude>=40.15 else 35 if point.latitude>=39.95 else 20
            result[point]=tuple(HourlyForecast(base+timedelta(hours=i),base+timedelta(hours=i-1),base+timedelta(hours=i),wind+(i%6 if self.wind_override is None else 0),0,None if self.missing_snow else 0) for i in range(count))
        return result
