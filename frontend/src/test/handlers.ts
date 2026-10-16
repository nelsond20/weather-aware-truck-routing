import { http, HttpResponse } from 'msw';
import fixture from './trip.json';
export const handlers = [http.post('http://localhost/api/trips/evaluate/',()=>HttpResponse.json(fixture))];
