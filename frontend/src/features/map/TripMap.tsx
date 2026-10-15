import { useEffect,useId,useRef,useState } from 'react';
import { Map as MapLibreMap,Popup,setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import type { FeatureCollection,Point } from 'geojson';
import { z } from 'zod';
import type { RouteResult,CheckpointResult } from '../../api/types';
import { envSchema } from '../../api/schemas';
import { createLayerMapPort } from './mapAdapter';
import { installTripLayers,updateTripLayers,installHeatmap,updateHeatmap,readPalette } from './layers';
import { routeBounds } from './geojson';
import styles from './TripMap.module.css';
import 'maplibre-gl/dist/maplibre-gl.css';
type Props={routes:RouteResult[];selectedRouteId:string|null;onSelectRoute:(id:string)=>void;heatmapFrame:FeatureCollection<Point>|null;mode?:'demo'|'live'};
setWorkerUrl(workerUrl);
const env=envSchema.parse({VITE_MAP_STYLE_URL:import.meta.env.VITE_MAP_STYLE_URL});
function description(cp:CheckpointResult){return `Arrival ${cp.eta}. ${cp.level?.replace('_',' ')??'Incomplete weather'}${cp.known_max==='no_travel'?' · Known No Travel':''}. Wind ${cp.wind_mph??'Unknown'} mph. Rain ${cp.rain_in_hr??'Unknown'} in/hr. Snow ${cp.snow_in_hr??'Unknown'} in/hr. ${cp.reasons.join(' ')}`;}
export function TripMap({routes,selectedRouteId,onSelectRoute,heatmapFrame,mode='demo'}:Props){
  const id=useId();const container=useRef<HTMLDivElement>(null);const mapRef=useRef<MapLibreMap|null>(null);const popup=useRef<Popup|null>(null);
  const latest=useRef({routes,onSelectRoute});const [ready,setReady]=useState(false);const [mapError,setMapError]=useState(false);
  const [inspected,setInspected]=useState<{routeId:string;index:number}|null>(null);
  useEffect(()=>{latest.current={routes,onSelectRoute};},[routes,onSelectRoute]);
  useEffect(()=>{
    if(!container.current)return;
    let cancelled=false;
    let map:MapLibreMap;
    try {map=new MapLibreMap({container:container.current,
      style:env.VITE_MAP_STYLE_URL??{version:8,
        sources:mode==='live'?{osm:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,maxzoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}}:{},
        layers:mode==='live'?[{id:'osm-basemap',type:'raster',source:'osm'}]:[{id:'background',type:'background',paint:{'background-color':getComputedStyle(document.documentElement).getPropertyValue('--color-page').trim()}}]},
      center:[-99,40],zoom:6,bounds:latest.current.routes.length?routeBounds(latest.current.routes):undefined,fitBoundsOptions:{padding:45},
      attributionControl:mode==='live'?{compact:false}:false});}
    catch {queueMicrotask(()=>{if(!cancelled)setMapError(true);});return()=>{cancelled=true;};}
    mapRef.current=map;map.getCanvas().setAttribute('aria-label','Route and corridor weather map');
    function handleLoad(){const port=createLayerMapPort(map);const palette=readPalette();installHeatmap(port,palette);installTripLayers(port,palette);setReady(true);}
    function handleClick(event:Parameters<MapLibreMap['queryRenderedFeatures']>[0]){
      const features=map.queryRenderedFeatures(event,{layers:['trip-intervals','trip-checkpoints','trip-checkpoints-unknown']});
      const feature=features[0];const routeId=z.string().max(64).safeParse(feature?.properties?.route_id);
      if(!routeId.success)return;latest.current.onSelectRoute(routeId.data);
      const index=z.number().int().nonnegative().safeParse(feature?.properties?.checkpoint_index);
      const cp=index.success?latest.current.routes.find(r=>r.route_id===routeId.data)?.checkpoints[index.data]:undefined;
      if(cp&&index.success){setInspected({routeId:routeId.data,index:index.data});popup.current?.remove();const node=document.createElement('p');node.textContent=description(cp);popup.current=new Popup().setLngLat(cp.coordinate).setDOMContent(node).addTo(map);}
    }
    const onClick=(event:{point:{x:number;y:number}})=>{if(map.isStyleLoaded())handleClick([event.point.x,event.point.y]);};
    const onError=()=>setMapError(true);
    map.on('load',handleLoad);map.on('click',onClick);map.on('error',onError);
    const observer=new ResizeObserver(()=>map.resize());observer.observe(container.current);
    return()=>{cancelled=true;observer.disconnect();popup.current?.remove();map.off('load',handleLoad);map.off('click',onClick);map.off('error',onError);map.remove();mapRef.current=null;};
  },[mode]);
  useEffect(()=>{const map=mapRef.current;if(ready&&map)updateTripLayers(createLayerMapPort(map),routes,selectedRouteId);},[ready,routes,selectedRouteId]);
  useEffect(()=>{const map=mapRef.current;if(ready&&map&&routes.length)map.fitBounds(routeBounds(routes),{padding:45,duration:0});},[ready,routes]);
  useEffect(()=>{const map=mapRef.current;if(ready&&map)updateHeatmap(createLayerMapPort(map),heatmapFrame);},[ready,heatmapFrame]);
  const route=routes.find(r=>r.route_id===selectedRouteId);const cp=inspected?routes.find(r=>r.route_id===inspected.routeId)?.checkpoints[inspected.index]:undefined;
  return <section className={styles.panel} aria-label="Trip map and checkpoints"><h2>Route exposure</h2>
    <div ref={container} className={styles.canvas} aria-label="Interactive route map"/>
    {mapError&&<p role="status">Map unavailable. Inspect the same routes and checkpoints below.</p>}
    <p className={styles.hint}>Solid routes show arrival-based exposure; dashed samples have incomplete weather. Select any route for inspection.</p>
    <ul className={styles.legend} aria-label="Weather risk legend">{(['low','moderate','high','severe','no_travel','unknown'] as const).map(level=><li key={level} data-risk={level}>{level.replace('_',' ')}</li>)}</ul>
    <p>Smoothed weather risk intensity blends sample weight and density. Exact categories belong to the sampled points.</p>
    {route&&<><h3>Arrival checkpoints · {route.checkpoints.length} samples</h3><ul className={styles.checkpoints} aria-label="Arrival checkpoints">{route.checkpoints.map((point,index)=><li key={route.route_id+':'+index}><button type="button" aria-describedby={id+'detail'} onClick={()=>setInspected({routeId:route.route_id,index})}>Checkpoint {index+1} · {point.distance_miles.toFixed(1)} mi · {point.level?.replace('_',' ')??'Incomplete'}{point.known_max==='no_travel'?' · Known No Travel':''}</button></li>)}</ul></>}
    <p id={id+'detail'} role="status" aria-live="polite">{cp?description(cp):'Choose a checkpoint to inspect its arrival weather.'}</p>
  </section>;
}
