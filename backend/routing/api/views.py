from datetime import datetime,timezone
from functools import lru_cache
from uuid import uuid4
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from routing.domain.models import Coordinate,TripRequest
from routing.services.budget import admission
from .serializers import TripInputSerializer,GeocodeSerializer
from .limits import throttle
from .output import trip_json

def get_current_time():return datetime.now(timezone.utc)

@lru_cache(maxsize=1)
def get_services():
    from routing.services.trips import build_services
    return build_services(settings.PROVIDER_MODE)

class HealthView(APIView):
    def get(self,request):return Response({'status':'ok','mode':settings.PROVIDER_MODE})

class TripView(APIView):
    def post(self,request):
        serializer=TripInputSerializer(data=request.data,context={'now':get_current_time()})
        serializer.is_valid(raise_exception=True)
        limited=throttle(request,'evaluate')
        if limited is not None:return limited
        data=serializer.validated_data
        value=TripRequest(Coordinate(**data['origin']),Coordinate(**data['destination']),data['departure_at'],data['load_lb'],data['spacing_miles'])
        with admission():
            services=get_services()
            result=services.trip.evaluate(value)
            return Response(trip_json(result,value,services.mode,str(uuid4())))

class GeocodeView(APIView):
    def get(self,request):
        serializer=GeocodeSerializer(data=request.query_params.dict());serializer.is_valid(raise_exception=True)
        limited=throttle(request,'geocode')
        if limited is not None:return limited
        with admission():
            candidates=get_services().geocoding.search(serializer.validated_data['q'])
            return Response([{'candidate_id':c.candidate_id,'label':c.label,'coordinate':[c.coordinate.longitude,c.coordinate.latitude]} for c in candidates])

class CorridorView(APIView):
    def post(self,request):
        from .serializers import CorridorInputSerializer
        from .output import corridor_json
        from routing.domain.models import RawRoute,RouteSegment
        from routing.domain.geometry import haversine_m
        now=get_current_time()
        serializer=CorridorInputSerializer(data=request.data,context={'now':now});serializer.is_valid(raise_exception=True)
        limited=throttle(request,'corridor')
        if limited is not None:return limited
        data=serializer.validated_data
        routes=[]
        for i,value in enumerate(data['routes']):
            points=tuple(Coordinate(*pair) for pair in value['coordinates'])
            routes.append(RawRoute(str(i),points,tuple(RouteSegment(a,b,haversine_m(a,b),0) for a,b in zip(points,points[1:]))))
        base=data.get('base_time',now.replace(minute=0,second=0,microsecond=0))
        with admission():
            services=get_services()
            return Response(corridor_json(services.corridor.forecast(tuple(routes),data['load_lb'],base),services.mode))
