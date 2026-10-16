import { useEffect,useRef,useState } from 'react';
import * as client from '../../api/client';
import { apiErrorSchema } from '../../api/schemas';
import type { TripInput,TripResponse,CorridorInput,CorridorResponse,ApiError } from '../../api/types';
export interface TripApi { evaluateTrip(input:TripInput,signal:AbortSignal):Promise<TripResponse>;fetchCorridor(input:CorridorInput,signal:AbortSignal):Promise<CorridorResponse> }
type Status='idle'|'loading'|'ready'|'error';
type State={status:Status;trip:TripResponse|null;corridor:CorridorResponse|null;selectedRouteId:string|null;selectedFrame:number;error:ApiError|null;corridorStatus:Status;corridorError:ApiError|null};
const initial:State={status:'idle',trip:null,corridor:null,selectedRouteId:null,selectedFrame:0,error:null,corridorStatus:'idle',corridorError:null};
function errorValue(error:unknown):ApiError { const result=apiErrorSchema.safeParse(error);return result.success?result.data:{code:'network_unavailable',message:'The request failed. Try again.',retryable:true}; }
export function useTrip(api:TripApi=client){
  const [state,setState]=useState<State>(initial);
  const generation=useRef(0);const controller=useRef<AbortController|null>(null);
  const previous=useRef<{input:TripInput;corridor:CorridorResponse|null}|null>(null);
  useEffect(()=>()=>{generation.current++;controller.current?.abort();},[]);
  async function submit(input:TripInput){
    const prev=previous.current;
    const same=prev!==null&&JSON.stringify({...prev.input,load_lb:0})===JSON.stringify({...input,load_lb:0});
    const base=same?prev.corridor?.base_time:undefined;
    controller.current?.abort();const current=new AbortController();controller.current=current;
    const ticket=++generation.current;
    setState({...initial,status:'loading'});
    let trip:TripResponse;
    try {trip=await api.evaluateTrip(input,current.signal);}catch(error){if(ticket===generation.current&&!current.signal.aborted)setState({...initial,status:'error',error:errorValue(error)});return;}
    if(ticket!==generation.current||current.signal.aborted)return;
    previous.current={input,corridor:null};
    setState({...initial,status:'ready',trip,selectedRouteId:trip.recommendation.route_id??trip.routes[0]?.route_id??null,corridorStatus:trip.routes.length?'loading':'idle'});
    if(!trip.routes.length)return;
    try {
      const corridor=await api.fetchCorridor({routes:trip.routes.map(r=>r.geometry),load_lb:input.load_lb,...(base?{base_time:base}:{})},current.signal);
      if(ticket!==generation.current||current.signal.aborted)return;
      previous.current={input,corridor};setState(s=>({...s,corridor,corridorStatus:'ready'}));
    }catch(error){if(ticket===generation.current&&!current.signal.aborted)setState(s=>({...s,corridorStatus:'error',corridorError:errorValue(error)}));}
  }
  function selectRoute(routeId:string){setState(s=>s.trip?.routes.some(r=>r.route_id===routeId)?{...s,selectedRouteId:routeId}:s);}
  function selectFrame(frameIndex:number){if(Number.isInteger(frameIndex)&&frameIndex>=0&&frameIndex<=48)setState(s=>({...s,selectedFrame:frameIndex}));}
  return {state,submit,selectRoute,selectFrame};
}
