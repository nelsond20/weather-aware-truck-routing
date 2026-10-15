import { useEffect,useId,useRef,useState } from 'react';
import { z } from 'zod';
import { tripInputSchema,instantSchema } from '../../api/schemas';
import type { GeocodeCandidate,TripInput } from '../../api/types';
import styles from './TripForm.module.css';
type Props={onSubmit:(input:TripInput)=>Promise<void>|void;searchPlaces:(query:string,signal:AbortSignal)=>Promise<GeocodeCandidate[]>;pending:boolean;onEdit?:()=>void};
type PlaceState={text:string;selected:GeocodeCandidate|null;options:GeocodeCandidate[];error:string|null};
const empty:PlaceState={text:'',selected:null,options:[],error:null};
export function TripForm({onSubmit,searchPlaces,pending,onEdit}:Props){
  const id=useId();const form=useRef<HTMLFormElement>(null);
  const [origin,setOrigin]=useState<PlaceState>(empty);const [destination,setDestination]=useState<PlaceState>(empty);
  const [departure,setDeparture]=useState(()=>new Date(Math.ceil((Date.now()+3600000)/3600000)*3600000).toISOString());
  const [error,setError]=useState<{message:string;field:string}|null>(null);
  useEffect(()=>{
    if(origin.selected||origin.text.trim().length<2)return;
    const controller=new AbortController();
    const timer=setTimeout(()=>{void searchPlaces(origin.text,controller.signal).then(options=>{if(!controller.signal.aborted)setOrigin(s=>({...s,options,error:null}));}).catch(()=>{if(!controller.signal.aborted)setOrigin(s=>({...s,error:'Could not search. Try again.'}));});},300);
    return()=>{clearTimeout(timer);controller.abort();};
  },[origin.text,origin.selected,searchPlaces]);
  useEffect(()=>{
    if(destination.selected||destination.text.trim().length<2)return;
    const controller=new AbortController();
    const timer=setTimeout(()=>{void searchPlaces(destination.text,controller.signal).then(options=>{if(!controller.signal.aborted)setDestination(s=>({...s,options,error:null}));}).catch(()=>{if(!controller.signal.aborted)setDestination(s=>({...s,error:'Could not search. Try again.'}));});},300);
    return()=>{clearTimeout(timer);controller.abort();};
  },[destination.text,destination.selected,searchPlaces]);
  function fail(field:string,message:string){setError({field,message});const element=form.current?.elements.namedItem(field);if(element instanceof HTMLElement)element.focus();}
  async function handleSubmit(event:React.FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget);
    if(!instantSchema.safeParse(departure).success){fail('departure','Include a UTC offset, for example 2026-11-01T01:30:00-05:00.');return;}
    if(!origin.selected){fail('origin','Choose an origin from the search results.');return;}
    if(!destination.selected){fail('destination','Choose a destination from the search results.');return;}
    const numeric=z.string().trim().min(1).transform(Number).pipe(z.number().finite().nonnegative());
    const load=numeric.safeParse(data.get('load'));const spacing=numeric.safeParse(data.get('spacing'));
    if(!load.success||!spacing.success){fail('load','Enter a non-negative load in pounds.');return;}
    const result=tripInputSchema.safeParse({origin:{longitude:origin.selected.coordinate[0],latitude:origin.selected.coordinate[1]},destination:{longitude:destination.selected.coordinate[0],latitude:destination.selected.coordinate[1]},departure_at:departure,load_lb:load.data,spacing_miles:spacing.data});
    if(!result.success){fail('load','Check the load and choose distinct locations.');return;}
    setError(null);await onSubmit(result.data);
  }
  const utc=instantSchema.safeParse(departure).success?new Date(departure).toISOString().replace('.000Z',' UTC'):null;
  return <form ref={form} className={styles.form} onSubmit={event=>{void handleSubmit(event);}} noValidate onChange={()=>{onEdit?.();}}>
    <h2>Plan your trip</h2><p className={styles.hint}>Search and select both locations to compare available routes.</p>
    <label htmlFor={id+'origin'}>Origin</label><input id={id+'origin'} name="origin" value={origin.text} autoComplete="off" aria-invalid={error?.field==='origin'} aria-describedby={error?.field==='origin'?id+'error':undefined} onChange={event=>setOrigin({...empty,text:event.target.value})}/>
    {origin.error&&<p role="status">{origin.error}</p>}{origin.options.length>0&&<ul aria-label="Origin search results" className={styles.options}>{origin.options.map(place=><li key={place.candidate_id}><button type="button" onClick={()=>{setOrigin({text:place.label,selected:place,options:[],error:null});onEdit?.();}}>{place.label}</button></li>)}</ul>}
    <label htmlFor={id+'destination'}>Destination</label><input id={id+'destination'} name="destination" value={destination.text} autoComplete="off" aria-invalid={error?.field==='destination'} aria-describedby={error?.field==='destination'?id+'error':undefined} onChange={event=>setDestination({...empty,text:event.target.value})}/>
    {destination.error&&<p role="status">{destination.error}</p>}{destination.options.length>0&&<ul aria-label="Destination search results" className={styles.options}>{destination.options.map(place=><li key={place.candidate_id}><button type="button" onClick={()=>{setDestination({text:place.label,selected:place,options:[],error:null});onEdit?.();}}>{place.label}</button></li>)}</ul>}
    <label htmlFor={id+'load'}>Truck load (lb)</label><input id={id+'load'} name="load" type="number" min="0" defaultValue="30000" aria-invalid={error?.field==='load'} aria-describedby={error?.field==='load'?id+'error':undefined}/>
    <label htmlFor={id+'departure'}>Departure time (include UTC offset)</label><input id={id+'departure'} name="departure" value={departure} aria-invalid={error?.field==='departure'} aria-describedby={id+'timehint'+(error?.field==='departure'?' '+id+'error':'')} onChange={event=>setDeparture(event.target.value)}/>
    <p id={id+'timehint'} className={styles.hint}>{utc??'Example: 2026-11-01T01:30:00-05:00'}</p>
    <label htmlFor={id+'spacing'}>Checkpoint spacing</label><select id={id+'spacing'} name="spacing" defaultValue="25"><option value="10">Every 10 miles</option><option value="25">Every 25 miles</option><option value="50">Every 50 miles</option></select>
    <div aria-live="polite">{error&&<p id={id+'error'} role="alert" className={styles.errorMessage}>{error.message}</p>}</div>
    <button type="submit" disabled={pending}>{pending?'Evaluating routes…':'Evaluate routes'}</button>
  </form>;
}
