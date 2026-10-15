import { tripSchema } from '../api/schemas';
import type { TripInput,CorridorResponse } from '../api/types';
import fixture from './trip.json' with {type:'json'};
export const sampleTrip=tripSchema.parse(fixture);
export const sampleInput:TripInput={origin:{longitude:-100,latitude:40},destination:{longitude:-98,latitude:40},departure_at:'2026-10-13T12:00:00Z',load_lb:30000,spacing_miles:25};
export const sampleCorridor:CorridorResponse={base_time:'2026-10-13T12:00:00Z',width_miles:20,resolution_m:16093.44,locations:[[-100,40],[-98,40]],mode:'demo',frames:Array.from({length:49},(_,hour)=>({valid_at:new Date(Date.parse('2026-10-13T12:00:00Z')+hour*3600000).toISOString(),levels:['low','low'],known_max:['low','low'],coverage:{known_samples:2,total_samples:2}})),coverage:{known_samples:98,total_samples:98}};
