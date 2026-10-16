import type { TripResponse } from '../../api/types';
import styles from './RouteList.module.css';
type Props={trip:TripResponse;selectedRouteId:string|null;onSelectRoute:(id:string)=>void;stale?:boolean};
const criteria:Record<string,string>={severe_miles:'Fewer severe-risk miles',high_miles:'Fewer high-risk miles',average_risk:'Lower average weather risk',duration_seconds:'Shorter travel time',only_eligible_route:'Only complete, unblocked route',stable_tie:'Equivalent exposure and time',blocked:'Known No Travel condition',incomplete:'Weather data incomplete'};
export function RouteList({trip,selectedRouteId,onSelectRoute,stale=false}:Props){
  return <section className={styles.list} aria-label="Route comparison"><h2>Compare routes</h2>
    <p>{trip.mode==='demo'?'Demo · Synthetic routes and weather':'Live forecast'}{stale?' · Inputs changed — evaluate again':''}</p>
    {trip.recommendation.status==='all_blocked'&&<p role="status">All routes have No Travel conditions. Change the departure or load and evaluate again.</p>}
    {trip.recommendation.status==='insufficient_data'&&<p role="status">Weather coverage is incomplete. No route can be recommended.</p>}
    {trip.warnings.map(w=><p key={w} className={styles.hint}>{w==='fewer_than_three_routes'?'Fewer than three alternatives available.':w==='weather_coverage_incomplete'?'Some weather samples are unknown.':w==='eta_approximate'?'Arrival times are approximate.':w}</p>)}
    {trip.routes.map((route,index)=><article key={route.route_id} aria-label={'Route '+(index+1)} className={styles.route} data-selected={route.route_id===selectedRouteId} data-blocked={route.blocked}>
      <div className={styles.heading}><h3>Route {index+1}</h3>{!stale&&route.route_id===trip.recommendation.route_id&&<strong className={styles.badge}>Recommended</strong>}</div>
      <p>{route.distance_miles.toFixed(1)} mi · {(route.duration_seconds/3600).toFixed(1)} h · Arrival {new Date(route.arrival_at).toISOString().replace('T',' ').replace('.000Z',' UTC')}</p>
      <p><strong>{route.blocked?'No Travel':!route.complete?'Incomplete weather':'Eligible'}</strong> · Average risk {route.average_risk===null?'Unknown':route.average_risk.toFixed(2)}</p>
      <p>Severe {route.miles_by_level.severe.toFixed(1)} mi · High {route.miles_by_level.high.toFixed(1)} mi · Unknown {route.unknown_miles.toFixed(1)} mi</p>
      <p>{criteria[route.route_id===trip.recommendation.route_id?trip.recommendation.deciding_criterion??'':trip.recommendation.comparison_criteria[route.route_id]??'']??'Inspect arrival weather and exposure.'}</p>
      {route.blocked&&<p>{[...new Set(route.checkpoints.flatMap(cp=>cp.known_max==='no_travel'?cp.reasons:[]))].join(' ')}</p>}
      <button type="button" aria-pressed={route.route_id===selectedRouteId} onClick={()=>onSelectRoute(route.route_id)}>Inspect route {index+1}{route.blocked?' · No Travel':''}</button>
    </article>)}
  </section>;
}
