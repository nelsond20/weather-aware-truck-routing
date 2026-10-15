import { describe,it,expect } from 'vitest';
import { tripSchema,corridorSchema,tripInputSchema } from './schemas';
import fixture from '../test/trip.json';
import { sampleCorridor,sampleInput } from '../test/fixtures';
describe('strict transport contracts',()=>{
  it('accepts a real domain fixture and rejects extra fields',()=>{
    expect(tripSchema.safeParse(fixture).success).toBe(true);
    expect(tripSchema.safeParse({...fixture,extra:true}).success).toBe(false);
  });
  it('rejects invented risk and timestamps without offsets',()=>{
    const wrong=structuredClone(fixture);const route=wrong.routes[0];if(!route)throw Error('Fixture missing');const cp=route.checkpoints[0];if(!cp)throw Error('Checkpoint missing');cp.level='invented';expect(tripSchema.safeParse(wrong).success).toBe(false);
    expect(tripInputSchema.safeParse({...sampleInput,departure_at:'2026-10-13T12:00:00'}).success).toBe(false);
  });
  it('requires all 49 frames, matching locations and coverage',()=>{
    expect(corridorSchema.safeParse(sampleCorridor).success).toBe(true);
    expect(corridorSchema.safeParse({...sampleCorridor,frames:sampleCorridor.frames.slice(0,48)}).success).toBe(false);
    const wrong=structuredClone(sampleCorridor);const frame=wrong.frames[0];if(!frame)throw Error('Frame missing');frame.levels=[];expect(corridorSchema.safeParse(wrong).success).toBe(false);
  });
});
