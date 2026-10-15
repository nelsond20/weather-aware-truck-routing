import type { FeatureCollection,LineString,MultiLineString,Point } from 'geojson';
import type { Position,RouteResult } from '../../api/types';
export function splitDateline(coordinates:Position[]):LineString|MultiLineString{
  if(coordinates.length<2)throw Error('Line needs two points');
  const first=coordinates[0];if(!first)throw Error('Missing point');
  const parts:Position[][]=[[first]];
  for(let i=1;i<coordinates.length;i++){
    const a=coordinates[i-1],b=coordinates[i];const part=parts.at(-1);if(!a||!b||!part)throw Error('Invalid line');
    if(Math.abs(b[0]-a[0])<=180){part.push(b);continue;}
    const unwrapped=b[0]+(b[0]<a[0]?360:-360);const edge=unwrapped>a[0]?180:-180;
    const fraction=(edge-a[0])/(unwrapped-a[0]);const latitude=a[1]+fraction*(b[1]-a[1]);
    part.push([edge,latitude]);parts.push([[-edge,latitude],b]);
  }
  const only=parts[0];if(!only)throw Error('Missing part');
  return parts.length===1?{type:'LineString',coordinates:only}:{type:'MultiLineString',coordinates:parts};
}
export function routeFeatures(routes:RouteResult[]):FeatureCollection<LineString|MultiLineString>{
  return {type:'FeatureCollection',features:routes.flatMap(route=>route.intervals.map(interval=>({type:'Feature' as const,id:route.route_id+':'+interval.start_index,geometry:splitDateline(interval.geometry.coordinates),properties:{route_id:route.route_id,level:interval.level,distance_miles:interval.distance_miles,blocked:route.blocked}})))};
}
export function contextFeatures(routes:RouteResult[]):FeatureCollection<LineString|MultiLineString>{
  return {type:'FeatureCollection',features:routes.map(route=>({type:'Feature',id:route.route_id,geometry:splitDateline(route.geometry.coordinates),properties:{route_id:route.route_id,blocked:route.blocked}}))};
}
export function checkpointFeatures(routes:RouteResult[]):FeatureCollection<Point>{
  return {type:'FeatureCollection',features:routes.flatMap(route=>route.checkpoints.map((cp,index)=>({type:'Feature' as const,id:route.route_id+':'+index,geometry:{type:'Point' as const,coordinates:cp.coordinate},properties:{route_id:route.route_id,checkpoint_index:index,level:cp.level,known_max:cp.known_max,eta:cp.eta,reasons:cp.reasons.join(' ')}})))};
}
export function routeBounds(routes:RouteResult[]):[Position,Position]{
  const points=routes.flatMap(r=>r.geometry.coordinates);const first=points[0];if(!first)return [[-100,39],[-98,41]];
  const unwrapped=points.map(p=>[first[0]+(((p[0]-first[0]+180)%360+360)%360)-180,p[1]] as Position);
  return [[Math.min(...unwrapped.map(p=>p[0])),Math.min(...unwrapped.map(p=>p[1]))],[Math.max(...unwrapped.map(p=>p[0])),Math.max(...unwrapped.map(p=>p[1]))]];
}
