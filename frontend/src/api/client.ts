import { z } from 'zod';
import { apiErrorSchema,corridorInputSchema,corridorSchema,geocodeSchema,tripInputSchema,tripSchema } from './schemas';
import type { TripInput,CorridorInput,ApiError } from './types';
const invalid=():ApiError=>({code:'api_contract_invalid',message:'The service returned an unexpected response. Try again.',retryable:true});
async function request<T>(path:string,schema:z.ZodType<T>,signal:AbortSignal,input?:unknown):Promise<T>{
  let response:Response;
  try { response=await fetch(new URL(path,globalThis.location?.origin??'http://localhost'),{method:input===undefined?'GET':'POST',headers:input===undefined?undefined:{'Content-Type':'application/json'},body:input===undefined?undefined:JSON.stringify(input),signal}); }
  catch(error){if(error instanceof DOMException&&error.name==='AbortError')throw error;throw {code:'network_unavailable',message:'Could not reach the service. Try again.',retryable:true} satisfies ApiError;}
  let payload:unknown;
  try { payload=await response.json(); } catch { throw invalid(); }
  if(!response.ok){const parsed=apiErrorSchema.safeParse(payload);throw parsed.success?parsed.data:invalid();}
  const parsed=schema.safeParse(payload);
  if(!parsed.success)throw invalid();
  return parsed.data;
}
export function searchPlaces(query:string,signal:AbortSignal){
  const parsed=z.string().trim().min(2).max(200).parse(query);
  return request('/api/geocode/?q='+encodeURIComponent(parsed),geocodeSchema,signal);
}
export function evaluateTrip(input:TripInput,signal:AbortSignal){return request('/api/trips/evaluate/',tripSchema,signal,tripInputSchema.parse(input));}
export function fetchCorridor(input:CorridorInput,signal:AbortSignal){return request('/api/weather/corridor/',corridorSchema,signal,corridorInputSchema.parse(input));}
