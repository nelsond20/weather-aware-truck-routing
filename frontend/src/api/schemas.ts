import { z } from 'zod';
// Keep validation compatible with production CSP without dynamic code generation.
z.config({jitless:true});
export const riskSchema=z.enum(['low','moderate','high','severe','no_travel']);
const amount=z.number().finite().nonnegative();
const id=z.string().min(1).max(64);
export const instantSchema=z.iso.datetime({offset:true}).max(64);
export const positionSchema=z.tuple([z.number().finite().min(-180).max(180),z.number().finite().min(-90).max(90)]);
export const lineSchema=z.strictObject({type:z.literal('LineString'),coordinates:z.array(positionSchema).min(2).max(20000)});
const coordinate=z.strictObject({longitude:z.number().finite().min(-180).max(180),latitude:z.number().finite().min(-90).max(90)});
export const tripInputSchema=z.strictObject({origin:coordinate,destination:coordinate,departure_at:instantSchema,load_lb:amount.max(1000000),spacing_miles:z.union([z.literal(10),z.literal(25),z.literal(50)])}).refine(v=>v.origin.longitude!==v.destination.longitude||v.origin.latitude!==v.destination.latitude,{message:'Choose distinct locations.'});
export const geocodeSchema=z.array(z.strictObject({candidate_id:z.string().min(1).max(256),label:z.string().min(1).max(500),coordinate:positionSchema})).max(5);
const messages=z.array(z.string().max(200)).max(20);
const checkpoint=z.strictObject({coordinate:positionSchema,distance_miles:amount,eta:instantSchema,level:riskSchema.nullable(),known_max:riskSchema.nullable(),wind_level:riskSchema.nullable(),rain_level:riskSchema.nullable(),snow_level:riskSchema.nullable(),wind_mph:amount.nullable(),rain_in_hr:amount.nullable(),snow_in_hr:amount.nullable(),wind_valid_at:instantSchema.nullable(),accumulation_start:instantSchema.nullable(),accumulation_end:instantSchema.nullable(),missing_fields:z.array(z.enum(['wind','rain','snow'])).max(3),reasons:messages});
const interval=z.strictObject({start_index:z.number().int().nonnegative(),end_index:z.number().int().positive(),distance_miles:amount,level:riskSchema.nullable(),geometry:lineSchema});
export const routeSchema=z.strictObject({route_id:id,geometry:lineSchema,distance_miles:amount,duration_seconds:amount,arrival_at:instantSchema,eta_approximate:z.boolean(),blocked:z.boolean(),complete:z.boolean(),miles_by_level:z.strictObject({low:amount,moderate:amount,high:amount,severe:amount,no_travel:amount}),unknown_miles:amount,average_risk:z.number().finite().min(0).max(4).nullable(),checkpoints:z.array(checkpoint).min(2).max(1000),intervals:z.array(interval).min(1).max(999)}).superRefine((route,ctx)=>{
  const total=Object.values(route.miles_by_level).reduce((a,b)=>a+b,0)+route.unknown_miles;
  if(Math.abs(total-route.distance_miles)>Math.max(.00001,route.distance_miles*.000001))ctx.addIssue({code:'custom',message:'Distance totals differ.'});
  if(route.intervals.length!==route.checkpoints.length-1||route.intervals.some((iv,i)=>iv.start_index!==i||iv.end_index!==i+1))ctx.addIssue({code:'custom',message:'Intervals do not align.'});
  if(route.complete!==route.checkpoints.every(cp=>cp.level!==null)||route.blocked!==route.checkpoints.some(cp=>cp.known_max==='no_travel'))ctx.addIssue({code:'custom',message:'Coverage or blocking is inconsistent.'});
});
export const tripSchema=z.strictObject({mode:z.enum(['demo','live']),request_id:id,departure_at:instantSchema,load_lb:amount,spacing_miles:z.union([z.literal(10),z.literal(25),z.literal(50)]),warnings:messages,recommendation:z.strictObject({route_id:id.nullable(),status:z.enum(['recommended','all_blocked','insufficient_data','no_routes']),ranked_route_ids:z.array(id).max(3),deciding_criterion:z.string().max(64).nullable(),comparison_criteria:z.record(id,z.string().max(64))}),routes:z.array(routeSchema).max(3)}).superRefine((value,ctx)=>{
  const ids=value.routes.map(r=>r.route_id);
  const selected=value.routes.find(r=>r.route_id===value.recommendation.route_id);
  if(new Set(ids).size!==ids.length||value.routes.reduce((n,r)=>n+r.checkpoints.length,0)>1000||value.routes.reduce((n,r)=>n+r.geometry.coordinates.length,0)>20000)ctx.addIssue({code:'custom',message:'Route limits exceeded.'});
  if((value.recommendation.status==='recommended')!==(value.recommendation.route_id!==null)||selected?.blocked||selected?.complete===false||(value.recommendation.route_id!==null&&!selected)||value.recommendation.ranked_route_ids.some(id=>!ids.includes(id)))ctx.addIssue({code:'custom',message:'Invalid recommendation.'});
});
export const coverageSchema=z.strictObject({known_samples:z.number().int().nonnegative(),total_samples:z.number().int().nonnegative()}).refine(v=>v.known_samples<=v.total_samples);
export const corridorInputSchema=z.strictObject({routes:z.array(lineSchema).min(1).max(3),load_lb:amount.max(1000000),base_time:instantSchema.optional()}).refine(v=>v.routes.reduce((n,r)=>n+r.coordinates.length,0)<=20000);
const frame=z.strictObject({valid_at:instantSchema,levels:z.array(riskSchema.nullable()).max(150),known_max:z.array(riskSchema.nullable()).max(150),coverage:coverageSchema});
export const corridorSchema=z.strictObject({base_time:instantSchema,width_miles:z.literal(20),resolution_m:amount,locations:z.array(positionSchema).min(1).max(150),frames:z.array(frame).length(49),coverage:coverageSchema,mode:z.enum(['demo','live'])}).superRefine((value,ctx)=>{
  const length=value.locations.length;
  if(value.frames.some((f,i)=>f.levels.length!==length||f.known_max.length!==length||f.coverage.total_samples!==length||f.coverage.known_samples!==f.levels.filter(v=>v!==null).length||Date.parse(f.valid_at)!==Date.parse(value.base_time)+i*3600000)||value.coverage.total_samples!==length*49||value.coverage.known_samples!==value.frames.reduce((n,f)=>n+f.coverage.known_samples,0))ctx.addIssue({code:'custom',message:'Invalid frame coverage or timestamps.'});
});
export const apiErrorSchema=z.strictObject({code:z.string().max(64),message:z.string().max(200),retryable:z.boolean()});
export const envSchema=z.strictObject({VITE_MAP_STYLE_URL:z.string().regex(/^\/map-styles\/[a-zA-Z0-9_-]+\.json$/).optional()});
