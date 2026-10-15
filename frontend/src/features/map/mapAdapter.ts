import { GeoJSONSource } from 'maplibre-gl';
import type { Map as MapLibreMap,LayerSpecification,FilterSpecification } from 'maplibre-gl';
import type { FeatureCollection } from 'geojson';
export interface GeoJsonSourcePort {setData(data:FeatureCollection):void}
export interface LayerMapPort {
  getSource(id:string):GeoJsonSourcePort|undefined;
  addSource(id:string,source:{type:'geojson';data:FeatureCollection}):void;
  addLayer(layer:LayerSpecification):void;
  setFilter(id:string,filter:FilterSpecification):void;
  setPaintProperty(id:string,name:string,value:unknown):void;
}
export function createLayerMapPort(map:MapLibreMap):LayerMapPort{
  return {getSource(id){const source=map.getSource(id);return source instanceof GeoJSONSource?{setData(data){source.setData(data);}}:undefined;},addSource(id,source){map.addSource(id,source);},addLayer(layer){map.addLayer(layer);},setFilter(id,filter){map.setFilter(id,filter);},setPaintProperty(id,name,value){const allowed=['line-color','line-width','line-opacity','circle-color','circle-radius','circle-stroke-color','circle-stroke-width','heatmap-color','heatmap-radius','heatmap-opacity'] as const;const key=allowed.find(property=>property===name);if(!key)throw Error('Unsupported paint property');if(typeof value!=='string'&&typeof value!=='number')throw Error('Unsupported paint value');map.setPaintProperty(id,key,value);}};
}
