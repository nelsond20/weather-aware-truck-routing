import type { FeatureCollection,Point } from 'geojson';
import type { CorridorResponse,RiskLevel } from '../../api/types';
const weight:Record<RiskLevel,number>={low:.2,moderate:.4,high:.6,severe:.8,no_travel:1};
export function frameFeatures(corridor:CorridorResponse,frameIndex:number):FeatureCollection<Point>{
  const frame=corridor.frames[frameIndex];
  if(!frame||frame.levels.length!==corridor.locations.length||frame.known_max.length!==corridor.locations.length)throw Error('Invalid corridor frame');
  return {type:'FeatureCollection',features:corridor.locations.map((coordinate,index)=>{const level=frame.levels[index]??null;return {type:'Feature',id:'weather:'+index,geometry:{type:'Point',coordinates:coordinate},properties:{level,known_max:frame.known_max[index]??null,weight:level===null?0:weight[level]}};})};
}
