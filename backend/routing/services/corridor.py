from datetime import timedelta
from routing.domain.corridor import build_corridor
from routing.domain.forecast import aware_utc,select_weather
from routing.domain.risk import assess_weather
from routing.domain.models import CorridorForecast,CorridorFrame
from routing.providers.base import ProviderError
from .cache import CachedWeatherProvider
from .budget import check_deadline
class CorridorService:
    def __init__(self,weather,cache,mode):self.weather=CachedWeatherProvider(weather,cache,mode)
    def forecast(self,routes,load_lb,base_time):
        base_time=aware_utc(base_time)
        grid=build_corridor(routes)
        check_deadline()
        series=self.weather.forecast(grid.locations,base_time-timedelta(hours=1),base_time+timedelta(hours=49))
        check_deadline()
        if not series:raise ProviderError('weather_unavailable','Weather is unavailable.',True)
        frames=tuple(CorridorFrame(base_time+timedelta(hours=i),tuple(assess_weather(select_weather(series.get(p,()),base_time+timedelta(hours=i)),load_lb) for p in grid.locations)) for i in range(49))
        return CorridorForecast(base_time,grid,frames)
