import math
import re
from datetime import datetime,timezone,timedelta
from rest_framework import serializers

class StrictSerializer(serializers.Serializer):
    def to_internal_value(self,data):
        if not isinstance(data,dict) or set(data)-set(self.fields):
            raise serializers.ValidationError({'non_field_errors':['Unexpected input fields.']})
        return super().to_internal_value(data)

class StrictFloat(serializers.FloatField):
    def to_internal_value(self,data):
        if isinstance(data,bool) or not isinstance(data,(int,float)) or not math.isfinite(data):
            self.fail('invalid')
        return super().to_internal_value(data)

class StrictChoice(serializers.ChoiceField):
    def to_internal_value(self,data):
        if isinstance(data,bool) or not isinstance(data,int):self.fail('invalid_choice',input=data)
        return super().to_internal_value(data)

class CoordinateSerializer(StrictSerializer):
    longitude = StrictFloat(min_value=-180,max_value=180)
    latitude = StrictFloat(min_value=-90,max_value=90)

ISO = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$')

def parse_instant(value):
    if not isinstance(value,str) or len(value)>64 or not ISO.fullmatch(value):
        raise serializers.ValidationError('Use ISO 8601 with an explicit UTC offset.')
    try:
        return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
    except ValueError:
        raise serializers.ValidationError('Invalid timestamp.') from None

class TripInputSerializer(StrictSerializer):
    origin = CoordinateSerializer()
    destination = CoordinateSerializer()
    departure_at = serializers.CharField(max_length=64,trim_whitespace=False)
    load_lb = StrictFloat(min_value=0,max_value=1000000)
    spacing_miles = StrictChoice(choices=(10,25,50))
    def validate_departure_at(self,value):
        instant = parse_instant(value)
        if instant < self.context['now']:
            raise serializers.ValidationError('Departure is in the past.',code='departure_in_past')
        return instant
    def validate(self,data):
        if data['origin']==data['destination']:raise serializers.ValidationError('Choose distinct locations.')
        return data

class GeocodeSerializer(StrictSerializer):
    q = serializers.CharField(min_length=2,max_length=200)
    def validate_q(self,value):
        if ';' in value or len(value.split())>20:raise serializers.ValidationError('Invalid search.')
        return value

class GeometrySerializer(StrictSerializer):
    type = serializers.ChoiceField(choices=('LineString',))
    coordinates = serializers.ListField(min_length=2,max_length=20000)
    def validate_coordinates(self,values):
        result=[]
        for pair in values:
            if not isinstance(pair,list) or len(pair)!=2:raise serializers.ValidationError('Invalid coordinates.')
            serializer=CoordinateSerializer(data={'longitude':pair[0],'latitude':pair[1]})
            serializer.is_valid(raise_exception=True)
            result.append(pair)
        return result

class CorridorInputSerializer(StrictSerializer):
    routes = GeometrySerializer(many=True,allow_empty=False,max_length=3)
    load_lb = StrictFloat(min_value=0,max_value=1000000)
    base_time = serializers.CharField(max_length=64,required=False)
    def to_internal_value(self,data):
        # Bound aggregate work before nested serializers validate every coordinate.
        routes=data.get('routes') if isinstance(data,dict) else None
        if isinstance(routes,list) and len(routes)<=3:
            count=sum(len(route['coordinates']) for route in routes
                      if isinstance(route,dict) and isinstance(route.get('coordinates'),list))
            if count>20000:
                raise serializers.ValidationError({'routes':{'non_field_errors':['Too many route vertices.']}},code='max_length')
        return super().to_internal_value(data)
    def validate_routes(self,values):
        if len(values)>3 or sum(len(v['coordinates']) for v in values)>20000:raise serializers.ValidationError('Too many route vertices.')
        if any(len({tuple(p) for p in v['coordinates']})<2 for v in values):raise serializers.ValidationError('Route must have positive distance.')
        return values
    def validate_base_time(self,value):
        instant=parse_instant(value)
        if not value.endswith('Z') and not value.endswith('+00:00'):raise serializers.ValidationError('Use UTC.',code='invalid_base_time')
        if instant.minute or instant.second or instant.microsecond or abs((instant-self.context['now']).total_seconds())>3600:
            raise serializers.ValidationError('Renew the corridor window.',code='invalid_base_time')
        return instant
