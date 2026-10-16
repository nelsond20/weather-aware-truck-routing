import { it,expect } from 'vitest';
import { http,HttpResponse } from 'msw';
import { server } from '../test/setup';
import { evaluateTrip } from './client';
import { sampleInput } from '../test/fixtures';
it('parses a valid response before exposing it',async()=>{
  expect((await evaluateTrip(sampleInput,new AbortController().signal)).mode).toBe('demo');
});
it('turns invalid successful JSON into a controlled contract error',async()=>{
  server.use(http.post('http://localhost/api/trips/evaluate/',()=>HttpResponse.json({routes:[]})));
  await expect(evaluateTrip(sampleInput,new AbortController().signal)).rejects.toMatchObject({code:'api_contract_invalid'});
});
it('rejects non-JSON without exposing server contents',async()=>{
  server.use(http.post('http://localhost/api/trips/evaluate/',()=>new HttpResponse('<secret>',{status:502})));
  await expect(evaluateTrip(sampleInput,new AbortController().signal)).rejects.toMatchObject({code:'api_contract_invalid'});
});
