import { it,expect } from 'vitest';
import { frameFeatures } from './heatmap';
import { sampleCorridor } from '../../test/fixtures';
it('keeps unknown distinct from low and preserves known blocking',()=>{
  const corridor=structuredClone(sampleCorridor);const frame=corridor.frames[0];if(!frame)throw Error('Frame missing');frame.levels=['low',null];frame.known_max=['low','no_travel'];
  const points=frameFeatures(corridor,0).features;expect(points[0]?.properties?.level).toBe('low');expect(points[1]?.properties?.level).toBe(null);expect(points[1]?.properties?.known_max).toBe('no_travel');
});
it('uses local frame 48 and rejects an absent frame',()=>{
  expect(frameFeatures(sampleCorridor,48).features).toHaveLength(2);expect(()=>frameFeatures(sampleCorridor,49)).toThrow();
});
