import type { ExpressionSpecification } from 'maplibre-gl';
import type { FeatureCollection } from 'geojson';
import type { RiskLevel,RouteResult } from '../../api/types';
import type { LayerMapPort } from './mapAdapter';
import { routeFeatures,checkpointFeatures,contextFeatures } from './geojson';
export type RiskPalette=Record<RiskLevel|'unknown',string>;
export const empty:FeatureCollection={type:'FeatureCollection',features:[]};
function color(p:RiskPalette):ExpressionSpecification{return ['match',['get','level'],'low',p.low,'moderate',p.moderate,'high',p.high,'severe',p.severe,'no_travel',p.no_travel,p.unknown];}
export function installTripLayers(map:LayerMapPort,p:RiskPalette){
  if(map.getSource('trip-intervals'))return;
  map.addSource('trip-context',{type:'geojson',data:empty});map.addSource('trip-intervals',{type:'geojson',data:empty});map.addSource('trip-checkpoints',{type:'geojson',data:empty});
  map.addLayer({id:'trip-context',type:'line',source:'trip-context',paint:{'line-color':p.unknown,'line-width':8,'line-opacity':.3,'line-dasharray':[3,1]}});
  map.addLayer({id:'trip-selected',type:'line',source:'trip-context',filter:['==',['get','route_id'],''],paint:{'line-color':p.low,'line-width':14,'line-opacity':.3}});
  map.addLayer({id:'trip-intervals',type:'line',source:'trip-intervals',paint:{'line-color':color(p),'line-width':5,'line-dasharray':['case',['==',['get','level'],null],['literal',[1,2]],['literal',[4,0]]]}});
  map.addLayer({id:'trip-checkpoints',type:'circle',source:'trip-checkpoints',filter:['!=',['get','level'],null],paint:{'circle-radius':5,'circle-color':color(p),'circle-stroke-color':p.unknown,'circle-stroke-width':1}});
  map.addLayer({id:'trip-checkpoints-unknown',type:'circle',source:'trip-checkpoints',filter:['==',['get','level'],null],paint:{'circle-radius':7,'circle-color':p.unknown,'circle-stroke-color':['case',['==',['get','known_max'],'no_travel'],p.no_travel,p.unknown],'circle-stroke-width':3}});
}
export function updateTripLayers(map:LayerMapPort,routes:RouteResult[],selectedRouteId:string|null){
  map.getSource('trip-context')?.setData(contextFeatures(routes));map.getSource('trip-intervals')?.setData(routeFeatures(routes));map.getSource('trip-checkpoints')?.setData(checkpointFeatures(routes));
  map.setFilter('trip-selected',['==',['get','route_id'],selectedRouteId??'']);
}
export function installHeatmap(map:LayerMapPort,p:RiskPalette){
  if(map.getSource('weather'))return;
  map.addSource('weather',{type:'geojson',data:empty});
  map.addLayer({id:'weather-heat',type:'heatmap',source:'weather',filter:['!=',['get','level'],null],paint:{'heatmap-weight':['get','weight'],'heatmap-radius':['interpolate',['linear'],['zoom'],3,15,10,35],'heatmap-opacity':.45,'heatmap-color':['interpolate',['linear'],['heatmap-density'],0,'rgba(0,0,0,0)',.2,p.low,.4,p.moderate,.6,p.high,.8,p.severe,1,p.no_travel]}});
  map.addLayer({id:'weather-exact',type:'circle',source:'weather',filter:['!=',['get','level'],null],paint:{'circle-color':color(p),'circle-radius':4,'circle-opacity':.8}});
  map.addLayer({id:'weather-unknown',type:'circle',source:'weather',filter:['==',['get','level'],null],paint:{'circle-color':p.unknown,'circle-radius':5,'circle-stroke-width':2,'circle-stroke-color':['case',['==',['get','known_max'],'no_travel'],p.no_travel,p.unknown]}});
}
export function updateHeatmap(map:LayerMapPort,features:FeatureCollection|null){map.getSource('weather')?.setData(features??empty);}
export function readPalette():RiskPalette{
  const css=getComputedStyle(document.documentElement);
  return {low:css.getPropertyValue('--color-risk-low').trim(),moderate:css.getPropertyValue('--color-risk-moderate').trim(),high:css.getPropertyValue('--color-risk-high').trim(),severe:css.getPropertyValue('--color-risk-severe').trim(),no_travel:css.getPropertyValue('--color-risk-no-travel').trim(),unknown:css.getPropertyValue('--color-risk-unknown').trim()};
}
