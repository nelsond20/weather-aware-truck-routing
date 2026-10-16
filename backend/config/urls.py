from django.urls import include,path
from .frontend import index, asset
urlpatterns = [path('api/',include('routing.api.urls')), path('', index), path('assets/<str:filename>', asset)]
