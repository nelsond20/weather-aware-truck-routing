import { test,expect } from '@playwright/test';
import { sampleTrip,sampleCorridor } from '../src/test/fixtures';
import { fillTrip } from './helpers';
import blockedTrip from './fixtures/all-blocked.json' with {type:'json'};
import incompleteTrip from './fixtures/incomplete.json' with {type:'json'};
import { tripSchema } from '../src/api/schemas';
import AxeBuilder from '@axe-core/playwright';

// These journeys verify browser recovery. Only external API responses are replaced;
// trip-planning.spec.ts keeps the successful journey against the real Django app.
test.beforeEach(async({page})=>{
  await page.route('**/api/geocode/**',route=>{
    const west=new URL(route.request().url()).searchParams.get('q')?.startsWith('West');
    return route.fulfill({json:[{candidate_id:west?'demo-west':'demo-east',label:west?'West Depot · Synthetic origin':'East Depot · Synthetic destination',coordinate:west?[-100,40]:[-98,40]}]});
  });
});

test('requires explicit location selection and focuses the invalid field',async({page})=>{
  let evaluations=0;
  await page.route('**/api/trips/evaluate/',route=>{evaluations++;return route.fulfill({status:503,json:{code:'unexpected_request',message:'Unexpected evaluation.',retryable:false}});});
  await page.goto('/');
  const origin=page.getByRole('textbox',{name:'Origin'});
  await origin.fill('West');
  await expect(page.getByRole('button',{name:'West Depot · Synthetic origin'})).toBeVisible();
  await page.getByRole('button',{name:'Evaluate routes'}).click();
  await expect(page.getByRole('alert')).toHaveText('Choose an origin from the search results.');
  await expect(origin).toBeFocused();
  expect(evaluations).toBe(0);
});

test('recovers from an evaluation failure and hides stale recommendations after edits',async({page})=>{
  let evaluations=0;
  await page.route('**/api/trips/evaluate/',route=>{
    evaluations++;
    return evaluations===1
      ?route.fulfill({status:503,json:{code:'provider_unavailable',message:'Routing is temporarily unavailable.',retryable:true}})
      :route.fulfill({json:sampleTrip});
  });
  await page.route('**/api/weather/corridor/',route=>route.fulfill({json:sampleCorridor}));
  await page.goto('/');await fillTrip(page,30000);
  const evaluate=page.getByRole('button',{name:'Evaluate routes'});
  await evaluate.click();
  const notice=page.getByRole('dialog',{name:'Public service unavailable'});
  await expect(notice).toContainText('Routing is temporarily unavailable.');
  await notice.getByRole('button',{name:'Close'}).click();
  await expect(page.getByRole('alert')).toHaveText('Routing is temporarily unavailable.');
  await expect(evaluate).toBeEnabled();
  await expect(page.getByRole('article',{name:'Route 1',exact:true})).toHaveCount(0);
  await evaluate.click();
  await expect(page.getByText('Recommended',{exact:true})).toHaveCount(1);
  await expect(page.getByRole('slider',{name:'Forecast hour'})).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.getByRole('spinbutton',{name:'Truck load (lb)'}).fill('40001');
  await expect(page.getByText('Recommended',{exact:true})).toHaveCount(0);
  await expect(page.getByText('Inputs changed; evaluate again.',{exact:true})).toBeVisible();
});

test('rejects malformed successful responses without crashing the page',async({page})=>{
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/api/trips/evaluate/',route=>route.fulfill({json:{...sampleTrip,unexpected:true}}));
  await page.goto('/');await fillTrip(page);
  await page.getByRole('button',{name:'Evaluate routes'}).click();
  await page.getByRole('dialog').getByRole('button',{name:'Close'}).click();
  await expect(page.getByRole('alert')).toHaveText('The service returned an unexpected response. Try again.');
  await expect(page.getByRole('button',{name:'Evaluate routes'})).toBeEnabled();
  await expect(page.getByText('Recommended',{exact:true})).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('recovers a failed place search when the user searches again',async({page})=>{
  await page.unroute('**/api/geocode/**');
  let searches=0;
  await page.route('**/api/geocode/**',route=>{
    searches++;
    return searches===1
      ?route.fulfill({status:503,json:{code:'provider_unavailable',message:'Search unavailable.',retryable:true}})
      :route.fulfill({json:[{candidate_id:'demo-west',label:'West Depot · Synthetic origin',coordinate:[-100,40]}]});
  });
  await page.goto('/');
  const origin=page.getByRole('textbox',{name:'Origin'});
  await origin.fill('West');
  await expect(page.getByRole('status')).toHaveText('Could not search. Try again.');
  await origin.fill('West Depot');
  await page.getByRole('button',{name:'West Depot · Synthetic origin'}).click();
  await expect(origin).toHaveValue('West Depot · Synthetic origin');
  await expect(page.getByText('Could not search. Try again.',{exact:true})).toHaveCount(0);
});

test('explains routing distance limits in a keyboard-accessible modal and permits correction',async({page})=>{
  let evaluations=0;
  await page.route('**/api/trips/evaluate/',route=>{
    evaluations++;
    return evaluations===1
      ?route.fulfill({status:400,json:{code:'route_distance_exceeded',message:'This trip exceeds the public routing service distance limit. Choose closer locations.',retryable:false}})
      :route.fulfill({json:sampleTrip});
  });
  await page.route('**/api/weather/corridor/',route=>route.fulfill({json:sampleCorridor}));
  await page.goto('/');await fillTrip(page,30000);
  const evaluate=page.getByRole('button',{name:'Evaluate routes'});
  await evaluate.click();
  const dialog=page.getByRole('dialog',{name:'Trip exceeds the routing limit'});
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText('Choose closer locations.');
  const close=dialog.getByRole('button',{name:'Close'});
  await expect(close).toBeFocused();
  await close.press('Tab');
  await expect.poll(()=>page.evaluate(()=>document.activeElement===document.body||document.activeElement?.closest('dialog')!==null)).toBe(true);
  await page.keyboard.press('Shift+Tab');await expect(close).toBeFocused();
  const accessibility=await new AxeBuilder({page}).analyze();
  expect(accessibility.violations.filter(v=>v.impact==='serious'||v.impact==='critical')).toEqual([]);
  await close.press('Escape');await expect(dialog).not.toBeVisible();
  await expect(evaluate).toBeFocused();
  await evaluate.click();
  await expect(page.getByText('Recommended',{exact:true})).toHaveCount(1);
  await expect(page.getByRole('slider',{name:'Forecast hour'})).toBeVisible();
  await expect(page.getByRole('dialog')).not.toBeVisible();
});

test('keeps the recommendation and restores checkpoint focus after a corridor error',async({page})=>{
  let release:()=>void=()=>{};
  const pending=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/trips/evaluate/',route=>route.fulfill({json:sampleTrip}));
  await page.route('**/api/weather/corridor/',async route=>{await pending;await route.fulfill({status:503,json:{code:'provider_timeout',message:'Weather service timed out.',retryable:true}});});
  await page.goto('/');await fillTrip(page,30000);
  await page.getByRole('button',{name:'Evaluate routes'}).click();
  await expect(page.getByText('Recommended',{exact:true})).toHaveCount(1);
  const checkpoint=page.getByRole('button',{name:/Checkpoint 1 ·/});
  await checkpoint.focus();await expect(checkpoint).toBeFocused();
  release();
  const notice=page.getByRole('dialog',{name:'Service timed out'});
  await expect(notice).toContainText('CORRIDOR FORECAST');
  await expect(notice).toContainText('Weather service timed out.');
  const closed=notice.evaluate(node=>new Promise<void>(resolve=>{node.addEventListener('close',()=>requestAnimationFrame(()=>resolve()),{once:true});}));
  await notice.getByRole('button',{name:'Close'}).click();
  await closed;
  await expect(checkpoint).toBeFocused();
  await expect(page.getByText('Recommended',{exact:true})).toHaveCount(1);
});

for(const notice of [
  {code:'no_route',title:'No driving route found',message:'No driving route connects the selected locations. Choose locations connected by road.',status:400},
  {code:'route_location_unavailable',title:'Location is not accessible by road',message:'A selected location could not be matched to a drivable road. Choose a nearby town or road.',status:400},
  {code:'provider_rate_limited',title:'Public service request limit reached',message:'Provider quota is unavailable.',status:503},
  {code:'__proto__',title:'Request could not be completed',message:'The service could not complete the request.',status:503},
]){
  test('shows an actionable modal for '+notice.code,async({page})=>{
    await page.route('**/api/trips/evaluate/',route=>route.fulfill({status:notice.status,json:{code:notice.code,message:notice.message,retryable:notice.code==='provider_rate_limited'}}));
    await page.goto('/');await fillTrip(page,30000);
    await page.getByRole('button',{name:'Evaluate routes'}).click();
    const dialog=page.getByRole('dialog',{name:notice.title});
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(notice.message);
    await dialog.getByRole('button',{name:'Close'}).click();
    await expect(dialog).not.toBeVisible();
    await expect(page.getByRole('textbox',{name:'Origin'})).toHaveValue('West Depot · Synthetic origin');
  });
}

for(const scenario of [
  {name:'never recommends when all routes have No Travel conditions',trip:blockedTrip,message:'All routes have No Travel conditions. Change the departure or load and evaluate again.',state:'No Travel'},
  {name:'never recommends when weather is incomplete',trip:incompleteTrip,message:'Weather coverage is incomplete. No route can be recommended.',state:'Incomplete weather'},
]){
  test(scenario.name,async({page})=>{
    await page.route('**/api/trips/evaluate/',route=>route.fulfill({json:tripSchema.parse(scenario.trip)}));
    await page.route('**/api/weather/corridor/',route=>route.fulfill({status:503,json:{code:'provider_timeout',message:'Corridor unavailable.',retryable:true}}));
    await page.goto('/');await fillTrip(page,30000);
    await page.getByRole('button',{name:'Evaluate routes'}).click();
    await page.getByRole('dialog',{name:'Service timed out'}).getByRole('button',{name:'Close'}).click();
    await expect(page.getByText(scenario.message,{exact:true})).toBeVisible();
    await expect(page.getByText('Recommended',{exact:true})).toHaveCount(0);
    const first=page.getByRole('article',{name:'Route 1',exact:true});
    await expect(first).toContainText(scenario.state);
    await first.getByRole('button',{name:/Inspect route 1/}).click();
    await page.getByRole('button',{name:/Checkpoint 1 ·/}).click();
    await expect(page.getByRole('status').filter({hasText:'Wind'})).toBeVisible();
  });
}
