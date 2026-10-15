import { lazy,Suspense,useEffect,useId,useRef,useState } from 'react';
import { TripForm } from './features/trip/TripForm';
import { RouteList } from './features/trip/RouteList';
import { ForecastSlider } from './features/weather/ForecastSlider';
import { frameFeatures } from './features/weather/heatmap';
import { useTrip } from './features/trip/useTrip';
import { searchPlaces } from './api/client';
import type { ApiError } from './api/types';
import styles from './App.module.css';
const TripMap=lazy(()=>import('./features/map/TripMap').then(module=>({default:module.TripMap})));
const errorTitles=new Map([
  ['route_distance_exceeded','Trip exceeds the routing limit'],
  ['route_location_unavailable','Location is not accessible by road'],
  ['no_route','No driving route found'],
  ['provider_rate_limited','Public service request limit reached'],
  ['rate_limited','Too many requests'],
  ['provider_timeout','Service timed out'],
  ['provider_unavailable','Public service unavailable'],
  ['network_unavailable','Connection unavailable'],
]);
export function App(){
  const {state,submit,selectRoute,selectFrame}=useTrip();const [stale,setStale]=useState(false);const [showWeather,setShowWeather]=useState(true);
  const dialog=useRef<HTMLDialogElement>(null);const returnFocus=useRef<HTMLElement|null>(null);const noticeId=useId();
  const [dismissedError,setDismissedError]=useState<ApiError|null>(null);
  const error=state.error??state.corridorError;const notice=error!==dismissedError?error:null;
  useEffect(()=>{
    const element=dialog.current;
    if(notice&&element&&!element.open){
      const active=document.activeElement;
      if(active instanceof HTMLElement&&active!==document.body)returnFocus.current=active;
      element.showModal();
    }
    else if(!notice&&element?.open)element.close();
  },[notice]);
  const frame=state.corridor?.frames[state.selectedFrame];
  return <main className={styles.app}><header className={styles.header}><div><p className={styles.eyebrow}>DISPATCH / WEATHER & ROAD</p><h1>Weather-aware truck routing</h1><p>Compare arrival weather. Inspect the next 48 hours.</p></div><span className={styles.demo}>Arrival weather · 48-hour corridor forecast</span></header>
    <div className={styles.layout}><aside className={styles.sidebar}><TripForm onSubmit={async input=>{returnFocus.current=document.activeElement instanceof HTMLElement?document.activeElement:null;setStale(false);await submit(input);}} searchPlaces={searchPlaces} pending={state.status==='loading'} onEdit={()=>setStale(true)}/>
      <div aria-live="polite">{state.status==='loading'&&<p>Evaluating arrival weather…</p>}{state.error&&<p role="alert">{state.error.message}</p>}{state.trip&&<p>{stale?'Inputs changed; evaluate again.':state.trip.recommendation.route_id?'Recommendation ready.':'No eligible recommendation.'}</p>}</div>
      {state.trip&&<RouteList trip={state.trip} selectedRouteId={state.selectedRouteId} onSelectRoute={selectRoute} stale={stale}/>}</aside>
      <div className={styles.workspace}>{state.trip?<><Suspense fallback={<p role="status">Loading route map…</p>}><TripMap key={state.trip.mode} mode={state.trip.mode} routes={state.trip.routes} selectedRouteId={state.selectedRouteId} onSelectRoute={selectRoute} heatmapFrame={state.corridor&&showWeather?frameFeatures(state.corridor,state.selectedFrame):null}/></Suspense>
        {state.corridorStatus==='loading'&&<p role="status">Loading corridor forecast…</p>}{state.corridorError&&<p role="alert">Corridor: {state.corridorError.message}{state.corridorError.code==='invalid_base_time'?' Change departure or checkpoint spacing and evaluate to renew the window.':''}</p>}
        {state.corridor&&frame&&<><label><input type="checkbox" checked={showWeather} onChange={event=>setShowWeather(event.target.checked)}/> Show corridor weather</label><ForecastSlider frames={state.corridor.frames} selectedFrame={state.selectedFrame} onSelectFrame={selectFrame} coverage={frame.coverage} baseTime={state.corridor.base_time}/><p>Adaptive grid spacing: {(state.corridor.resolution_m/1609.344).toFixed(1)} mi · 20-mile corridor on each side.</p></>}
      </>:<section className={styles.empty}><p className={styles.eyebrow}>READY FOR YOUR NEXT ROUTE</p><h2>A clearer view of the road ahead.</h2><p>Choose the origin and destination from the search results, add your load, and evaluate the weather at each arrival checkpoint.</p><p>Compare available routes and explore the corridor forecast for the next 48 hours.</p></section>}</div></div>
    <dialog ref={dialog} className={styles.notice} aria-labelledby={noticeId+'title'} aria-describedby={noticeId+'message'} onClose={()=>{setDismissedError(error);if(returnFocus.current?.isConnected)returnFocus.current.focus();}}>
      <p className={styles.eyebrow}>{state.error?'TRIP REQUEST':'CORRIDOR FORECAST'}</p>
      <h2 id={noticeId+'title'}>{errorTitles.get(notice?.code??'')??'Request could not be completed'}</h2>
      <p id={noticeId+'message'}>{notice?.message}</p>
      {notice?.retryable&&<p>Please wait a moment, then try again.</p>}
      <div className={styles.noticeActions}><button type="button" onClick={()=>dialog.current?.close()}>Close</button></div>
    </dialog>
    <footer><small>Map data © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · Routing engines: <a href="https://valhalla.openstreetmap.de/">Valhalla</a> / <a href="https://project-osrm.org/">OSRM</a> · Search: <a href="https://photon.komoot.io/">Photon</a> · <a href="https://www.openstreetmap.org/fixthemap">Fix the map</a> · Weather: <a href="https://open-meteo.com/">Open-Meteo</a></small></footer>
  </main>;
}
