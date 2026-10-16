import { it,expect } from 'vitest';
import { splitDateline,routeFeatures,checkpointFeatures,routeBounds } from './geojson';
import { sampleTrip } from '../../test/fixtures';
it('preserves intermediate road vertices in exposure',()=>{
  const route=structuredClone(sampleTrip.routes[0]);if(!route)throw Error('Missing route');const interval=route.intervals[0];if(!interval)throw Error('Missing interval');
  interval.geometry.coordinates=[[-100,40],[-99.8,40.2],[-99,40]];
  expect(routeFeatures([route]).features[0]?.geometry.coordinates).toEqual(interval.geometry.coordinates);
});
it('splits dateline without traversing Greenwich',()=>{
  expect(splitDateline([[179.9,40],[-179.9,40]])).toEqual({type:'MultiLineString',coordinates:[[[179.9,40],[180,40]],[[-180,40],[-179.9,40]]]});
  const route=structuredClone(sampleTrip.routes[0]);if(!route)throw Error('Missing route');route.geometry.coordinates=[[179.9,40],[-179.9,40]];
  const bounds=routeBounds([route]);expect(bounds[1][0]-bounds[0][0]).toBeCloseTo(.2);
});
it('uses stable IDs and keeps known blocking separate from unknown',()=>{
  const route=structuredClone(sampleTrip.routes[0]);if(!route)throw Error('Missing route');const cp=route.checkpoints[0];if(!cp)throw Error('Missing sample');cp.level=null;cp.known_max='no_travel';
  const data=checkpointFeatures([route]);expect(data.features[0]?.id).toBe(route.route_id+':0');expect(data.features[0]?.properties?.known_max).toBe('no_travel');
});
