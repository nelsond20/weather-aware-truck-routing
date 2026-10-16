from django.urls import path
from .views import HealthView,TripView,GeocodeView,CorridorView
urlpatterns=[path('weather/corridor/',CorridorView.as_view()),path('health/',HealthView.as_view()),path('geocode/',GeocodeView.as_view()),path('trips/evaluate/',TripView.as_view())]
