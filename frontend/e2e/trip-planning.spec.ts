import { test,expect } from '@playwright/test';
import { tripSchema,corridorSchema } from '../src/api/schemas';
import { fillTrip } from './helpers';
test('evaluates real demo backend, inspects blocked route and changes frames without network',async({page},info)=>{
  let corridors=0;let evaluations=0;const errors:string[]=[];
  page.on('request',request=>{if(request.url().includes('/api/weather/corridor/'))corridors++;if(request.url().includes('/api/trips/evaluate/'))evaluations++;});
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('link',{name:'OpenStreetMap contributors'})).toHaveAttribute('href','https://www.openstreetmap.org/copyright');
  await fillTrip(page);
  const response=page.waitForResponse(r=>r.url().includes('/api/trips/evaluate/')&&r.status()===200);
  const forecastResponse=page.waitForResponse(r=>r.url().includes('/api/weather/corridor/')&&r.status()===200);
  await page.getByRole('button',{name:'Evaluate routes'}).click();
  const raw:unknown=await(await response).json();const trip=tripSchema.parse(raw);
  const rawForecast:unknown=await(await forecastResponse).json();const forecast=corridorSchema.parse(rawForecast);
  expect(forecast.frames).toHaveLength(49);expect(forecast.locations.length).toBeLessThanOrEqual(150);
  expect(trip.request_id).toBeTruthy();expect(trip.routes[0]?.blocked).toBe(true);expect(trip.recommendation.route_id).not.toBe(trip.routes[0]?.route_id);
  const north=page.getByRole('article',{name:'Route 1',exact:true});
  await expect(north).toContainText('No Travel');await expect(north).not.toContainText('Recommended');
  await page.getByRole('button',{name:'Inspect route 1 · No Travel'}).click();
  await page.getByRole('button',{name:/Checkpoint 1 ·/}).click();await expect(page.getByRole('status').filter({hasText:'Wind'})).toBeVisible();
  const slider=page.getByRole('slider',{name:'Forecast hour'});await expect(slider).toBeVisible();
  await slider.focus();await slider.press('End');await expect(slider).toHaveValue('48');
  await slider.press('Home');await expect(slider).toHaveValue('0');
  await slider.press('ArrowRight');await expect(slider).toHaveValue('1');
  expect(corridors).toBe(1);expect(evaluations).toBe(1);await expect(page.getByText('Recommended',{exact:true})).toHaveCount(1);
  await expect(page.getByRole('region',{name:'Trip map and checkpoints'})).not.toContainText('Map unavailable');
  expect(errors).toEqual([]);
  const durations:number[]=[];
  for(let i=0;i<20;i++){
    await slider.evaluate(node=>{
      node.removeAttribute('data-frame-latency');
      node.addEventListener('input',()=>{
        const started=performance.now();
        requestAnimationFrame(()=>requestAnimationFrame(()=>node.setAttribute('data-frame-latency',String(performance.now()-started))));
      },{once:true});
    });
    await slider.press('ArrowRight');
    await expect(slider).toHaveAttribute('data-frame-latency',/^[0-9.]+$/);
    durations.push(Number(await slider.getAttribute('data-frame-latency')));
  }
  durations.sort((a,b)=>a-b);const p95=durations[18]??Infinity;
  await info.attach('frame-performance',{body:JSON.stringify({samples:forecast.locations.length,moves:20,p95_ms:p95,metric:'browser input to paint; excludes transport and asynchronous GPU completion',browser:'Chromium',viewport:info.project.name}),contentType:'application/json'});
  expect(p95).toBeLessThan(100);expect(corridors).toBe(1);
  await page.getByRole('heading',{name:'Route exposure'}).scrollIntoViewIfNeeded();
  await page.screenshot({path:'/tmp/weather-'+info.project.name+'.png'});
});
test('keeps recommendation if only corridor forecast fails',async({page})=>{
  await page.route('**/api/weather/corridor/',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({code:'provider_timeout',message:'Weather provider timed out.',retryable:true})}));
  await page.goto('/');await fillTrip(page,30000);await page.getByRole('button',{name:'Evaluate routes'}).click();
  const notice=page.getByRole('dialog',{name:'Service timed out'});
  await expect(notice).toContainText('Weather provider timed out.');
  await notice.getByRole('button',{name:'Close'}).click();
  await expect(page.getByText('Recommended',{exact:true})).toBeVisible();await expect(page.getByRole('alert')).toHaveText(/Corridor: Weather provider timed out/);
});
