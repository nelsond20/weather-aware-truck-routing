import { act,renderHook,waitFor } from '@testing-library/react';
import { it,expect,vi } from 'vitest';
import { useTrip } from './useTrip';
import { sampleInput,sampleTrip,sampleCorridor } from '../../test/fixtures';
it('ignores old results even when a cancelled transport resolves',async()=>{
  let resolveOlder!:(value:typeof sampleTrip)=>void;
  const old=new Promise<typeof sampleTrip>(resolve=>{resolveOlder=resolve;});
  const api={evaluateTrip:vi.fn().mockReturnValueOnce(old).mockResolvedValueOnce({...sampleTrip,request_id:'newer'}),fetchCorridor:vi.fn().mockResolvedValue(sampleCorridor)};
  const {result}=renderHook(()=>useTrip(api));
  act(()=>{void result.current.submit(sampleInput);});
  act(()=>{void result.current.submit({...sampleInput,load_lb:40001});});
  await waitFor(()=>expect(result.current.state.trip?.request_id).toBe('newer'));
  await act(async()=>{resolveOlder({...sampleTrip,request_id:'older'});await old;});
  expect(result.current.state.trip?.request_id).toBe('newer');expect(api.fetchCorridor).toHaveBeenCalledTimes(1);
});
it('keeps valid trip when corridor fails',async()=>{
  const api={evaluateTrip:vi.fn().mockResolvedValue(sampleTrip),fetchCorridor:vi.fn().mockRejectedValue({code:'provider_timeout',message:'Weather unavailable.',retryable:true})};
  const {result}=renderHook(()=>useTrip(api));await act(()=>result.current.submit(sampleInput));
  expect(result.current.state.trip).toEqual(sampleTrip);expect(result.current.state.status).toBe('ready');expect(result.current.state.corridorStatus).toBe('error');
});
it('does not replace the current corridor when cancelled older weather arrives late',async()=>{
  let resolveOlder!:(value:typeof sampleCorridor)=>void;
  const older=new Promise<typeof sampleCorridor>(resolve=>{resolveOlder=resolve;});
  const newer={...sampleCorridor,resolution_m:9999};
  const api={evaluateTrip:vi.fn().mockResolvedValue(sampleTrip),fetchCorridor:vi.fn().mockReturnValueOnce(older).mockResolvedValueOnce(newer)};
  const {result}=renderHook(()=>useTrip(api));
  let first:Promise<void>;
  act(()=>{first=result.current.submit(sampleInput);});
  await waitFor(()=>expect(result.current.state.corridorStatus).toBe('loading'));
  await act(()=>result.current.submit({...sampleInput,load_lb:40001}));
  expect(result.current.state.corridor?.resolution_m).toBe(9999);
  await act(async()=>{resolveOlder(sampleCorridor);await first;});
  expect(result.current.state.corridor?.resolution_m).toBe(9999);
  expect(result.current.state.corridorStatus).toBe('ready');
});
it('changes frames locally and keeps base time for a load change',async()=>{
  const api={evaluateTrip:vi.fn().mockResolvedValue(sampleTrip),fetchCorridor:vi.fn().mockResolvedValue(sampleCorridor)};
  const {result}=renderHook(()=>useTrip(api));await act(()=>result.current.submit(sampleInput));
  const recommendation=result.current.state.trip?.recommendation;
  act(()=>{result.current.selectFrame(48);result.current.selectFrame(12);});
  expect(api.fetchCorridor).toHaveBeenCalledTimes(1);expect(result.current.state.trip?.recommendation).toBe(recommendation);
  await act(()=>result.current.submit({...sampleInput,load_lb:40001}));
  expect(api.fetchCorridor).toHaveBeenLastCalledWith(expect.objectContaining({base_time:sampleCorridor.base_time}),expect.any(AbortSignal));
});
it('aborts transport on unmount',()=>{
  let signal:AbortSignal|undefined;
  const api={evaluateTrip:vi.fn((_input:typeof sampleInput,value:AbortSignal)=>{signal=value;return new Promise<typeof sampleTrip>(()=>{});}),fetchCorridor:vi.fn().mockResolvedValue(sampleCorridor)};
  const {result,unmount}=renderHook(()=>useTrip(api));act(()=>{void result.current.submit(sampleInput);});unmount();expect(signal?.aborted).toBe(true);
});
