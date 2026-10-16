# Spotter verification evidence

Verified on 2026-10-14 (America/Bogota); final runs crossed into 2026-10-15 UTC. Sources: the original two-page [PDF](docs/fs-assessment-spotter.pdf), its [Markdown extraction](docs/fs-assessment-spotter.md), both page images, and the approved design and implementation plan under `docs/superpowers/`.

The deterministic flows pass the automated checks below. The later Open-Meteo reliability follow-up also passed a complete real trip, as recorded below. This is bounded evidence, not proof that all possible inputs, browsers, or external-service failures are covered. Three real public-OSRM routes have not been demonstrated, and the GitHub, hosted URL, and Loom deliverables remain pending.

## Commands and results

Run from the repository root with the existing virtual environment, npm dependencies, and Playwright Chromium installed. No dependencies or test infrastructure were added for this verification.

| Check | Command | Result |
| --- | --- | --- |
| TypeScript | `npm --prefix frontend run typecheck` | Passed |
| Lint | `npm --prefix frontend run lint` | Passed |
| Django/domain/providers/integration | `backend/.venv/bin/python backend/manage.py test routing.tests` | 86 passed |
| Full frontend, including existing stories | `PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test` | 37 passed in 11 files |
| Production artifacts | `npm --prefix frontend run build` | Passed; existing MapLibre chunk-size warning remains |
| Full browser suite | `PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test:e2e` | 18 passed; Chromium desktop 1440×900 and mobile 390×844 |

Repeatability commands, each with a fresh backend owned by Playwright:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test:e2e -- trip-planning.spec.ts -g 'evaluates real demo backend' --repeat-each=2
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test:e2e -- --shard=1/2
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test:e2e -- --shard=2/2
```

The isolated main journey passed twice per viewport (4 executions). Both shards passed (9 tests each). The final full suite passed all 18 with no retries or skips. Keep Vitest browser stories and Playwright runs serial; do not disable application rate limits to repeat tests. Repeating the entire suite twice against one worker can legitimately exceed the five-corridor-requests-per-minute limit.

Earlier runs did expose intermittent timeouts. Concurrent Vitest/Playwright browser work exceeded the total E2E budget. Later sharded runs also timed out during mobile slider actions and during Axe's initial, pre-evaluation scan; CPU pressure was observed during that period. The failed traces were inspected and retained temporarily. A clean rerun passing does not establish that this resource-sensitive flakiness can never recur. No global E2E timeout, retry setting, risk validation, or p95 threshold was relaxed.

The E2E slider check retains 20 measured moves and a p95 budget below 100 ms, checks both bounds (0 and 48), single-step keyboard changes, and absence of extra corridor requests. The prior unmeasured 12-key sequence was reduced to one step to remove redundant driver actions. Measurements use the actual returned 147 grid locations, not an assumed 150; they measure browser input through two animation frames, excluding Playwright transport and asynchronous GPU completion.

The final full run measured p95 **24.8 ms desktop / 29.0 ms mobile**. The final isolated repetitions measured **30.6 / 32.3 ms desktop** and **29.6 / 29.2 ms mobile**. These figures describe this Chromium environment, not a physical-device or GPU performance guarantee.

## Bugs reproduced before fixes

1. Invalid asset filenames containing a NUL or exceeding the filesystem filename limit produced HTTP 500. The regression failed with `500 != 404` before the fix. The asset view now rejects those names with 404 before filesystem access.
2. A uniform No Travel route could produce `average_risk: 4.000000000000001`, violating the frontend's 0–4 contract and preventing display of a valid all-blocked result. Uniform Moderate/High/Severe cases also drifted from their exact scores, which could affect average-risk ties. Failing regressions covered all five levels and all three checkpoint spacings. The numerator and normalization now use the same exposure buckets; uniform scores are exact, with the existing recommendation order preserved.

Test compatibility fixes were limited to JSON import attributes required by Node 24 and a 15-second allowance for the existing cold Stylelint-rule-loading test (previously timed out at 5 seconds). Linter configuration, dependencies, and application runtime limits were unchanged.

## Requirement coverage

| Requirement | Evidence |
| --- | --- |
| Origin/destination, departure with timezone, load | Actual Django demo E2E; explicit candidate selection and validation/focus journeys |
| Three distinct alternatives | Demo API returns three; OSRM adapter preserves three distinct returned routes and removes duplicates; live public-server limit below |
| 10/25/50-mile checkpoints and arrival ETAs | Geometry/time-annotation unit tests, partial final intervals, zero-distance timing, timezone normalization, API load/spacing matrix |
| Weather thresholds and load rules | Exact boundary tests plus dense monotonicity checks for hazards and loads; >30,000 and >40,000 lb boundaries exercised through the API |
| Recommendation priority | Severe miles, High miles, weighted average, duration, stable ties; blocked/incomplete exclusion; mileage conservation |
| Map and inspectable checkpoints | Desktop/mobile E2E with real MapLibre; visible routes, risk legend, route selection, checkpoint weather and ETA |
| Heatmap and 0–48-hour slider | 49 returned frames, bounded corridor grid, local frame changes, no new corridor request; browser timing check |
| Missing data and failures | All-blocked/incomplete response fixtures generated from actual domain services, malformed response rejection, search/evaluation recovery, independent corridor failure |
| Stale asynchronous responses | Hook tests resolve cancelled old trip/corridor requests after newer results and verify the newer state is retained |
| Accessibility | Existing Axe E2E has no serious/critical violations before/after evaluation at both viewports; keyboard inspection and slider interaction |
| Production delivery | Compiled frontend build, asset delivery tests, local same-origin check described below; public hosting remains pending |

The primary successful E2E uses real Django and deterministic demo providers. Recovery journeys stub selected API responses to trigger exceptional states. Provider integration tests use controlled HTTP payloads; real public-service checks are separate. Screenshots were inspected visually; this does not constitute testing on physical phones, Firefox, or Safari.

## Public OSRM alternatives investigation

Requests used `alternatives=2`, `geometries=geojson`, `overview=full`, and `annotations=distance,duration`, with the identifying User-Agent and conservative request spacing. A bounded set of public-location queries was used, not a load test.

| Origin → destination on router.project-osrm.org | Total distinct routes observed |
| --- | --- |
| London → Oxford | 2 |
| Amsterdam → Rotterdam | 2 |
| Boston → Worcester | 1 |
| Paris → Orleans | 1 |
| Berlin → Hamburg | 1 |
| San Francisco → San Jose | 2 |
| Munich → Augsburg | 2 |
| Madrid → Toledo | 1 |
| Central Berlin pair | 1 |
| Cologne → Dusseldorf | 1 |
| Los Angeles → Long Beach | 2 |
| Portland → Salem | 1 |

Raw response counts agreed with normalized counts. A comparison against `routing.openstreetmap.de/routed-car` returned two routes for Berlin → Potsdam and London → Oxford; this did not change the application's configured provider. No real three-route result was found. The application retains available distinct routes and displays its existing warning; it does not fabricate a third route.

The [OSRM route-service contract](https://project-osrm.org/docs/v5.24.0/api/#route-service) describes `alternatives=n` as requesting up to n alternatives and does not guarantee their availability. The upstream [CH implementation](https://github.com/Project-OSRM/osrm-backend/blob/master/src/engine/routing_algorithms/alternative_path_ch.cpp) ignores the requested alternative count and computes a primary/secondary pair; the [MLD implementation](https://github.com/Project-OSRM/osrm-backend/blob/master/src/engine/routing_algorithms/alternative_path_mld.cpp) handles multiple alternatives. The observed public-server results are consistent with that CH limitation, but the deployed server configuration was not independently established.

If the original assessment's three-API-route requirement is mandatory, it remains an acceptance gap despite the later approved behavior of returning fewer available routes. Resolving it requires a routing service/deployment supporting multiple alternatives and a suitable trip, then a real three-route verification. Even such a service cannot guarantee three distinct viable paths for every origin/destination. Public Photon/OSRM remain suitable for light assessment/demo use, without a production SLA.

## Earlier live build check, before the Open-Meteo retry fix

Django served the compiled frontend and API on `127.0.0.1:8000` with `DJANGO_DEBUG=0` and `PROVIDER_MODE=live`. This was a local delivery smoke check using `runserver`, not deployment to a production WSGI host. No third-party credentials were configured and no responses were stubbed.

Photon successfully resolved Berlin and Potsdam. OSRM returned two distinct routes, approximately 21.99 and 22.69 miles. Both had complete arrival-checkpoint weather from Open-Meteo and an eligible recommendation. The existing fewer-than-three and approximate-ETA warnings appeared correctly.

The live corridor failed on both attempts. The second response was HTTP 503 with `{code: "provider_timeout", message: "Evaluation exceeded its time limit.", retryable: true}`. An isolated request for the first 25 grid locations also timed out after approximately 15.9 seconds in the existing HTTP client. Two further bounded diagnostic requests, for just one and ten locations, each received **HTTP 503 directly from Open-Meteo** in approximately 0.85 seconds. Smaller batches therefore did not resolve the observed unavailability; the upstream cause was not established. The corridor makes up to six sequential 25-location batches under the existing 45-second operation budget. Neither that budget nor the 15-second HTTP timeout was increased, no automatic retries were added, and the weather provider was not refactored speculatively.

The real UI retained the recommendation and displayed the corridor error at desktop and mobile widths. Those screenshots were inspected; the check recorded no page JavaScript errors or CSP violations. **That pre-fix live heatmap/49-frame run did not pass.** Its failure is retained as historical evidence; the subsequent reliability result appears below.

Temporary evidence remains under `/tmp/spotter-live-trip-response.json`, `/tmp/spotter-live-corridor-response.json`, and `/tmp/spotter-live-{desktop,mobile}-failure.png`. Temporary files are local session artifacts, not committed deliverables.

## Open-Meteo reliability follow-up: real trip passed

Inspection confirmed that the existing provider already requests up to 25 coordinates together, fetching the complete hourly series with calendar-day padding and only `wind_speed_10m,rain,snowfall`. The corridor service constructs the 49 frames locally; the 900-second raw-series cache and network-free frontend slider were retained. No domain, risk, map, provider selection, or frontend changes were needed.

Only the shared HTTP transport's Open-Meteo path gained up to two retries for HTTP 429/502/503/504. Backoff is 1 then 2 seconds, increased when a valid `Retry-After` requires a longer delay. Failed responses close before waiting. Connection/read timeouts are 5/20 seconds, recomputed against the remaining 45-second operation budget on every attempt; an oversized delay fails promptly. Other HTTP statuses, malformed data, and network timeouts are not retried. Photon/OSRM behavior is preserved.

The new recovery regressions failed before implementation, then passed. **All 91 backend tests, typecheck, lint, and all 18 existing desktop/mobile E2E tests passed.** E2E continues to use deterministic demo providers; no live public API was added to that suite. The additional corridor regression verifies bounded batch URLs, full 49-frame coverage, and raw-series reuse when load changes.

Real verification at approximately **2026-10-15 01:29 UTC** used the compiled frontend served by Django with `DJANGO_DEBUG=0`, a fresh live worker/cache, and actual Photon → OSRM → Open-Meteo responses. Temporary httpx event hooks observed actual HTTP attempts without replacing responses or persisting coordinates. The browser completed Berlin → Potsdam with a recommendation and visible heatmap.

| Required measurement | Observed result |
| --- | --- |
| Corridor locations | **144** |
| Open-Meteo HTTP requests | **7 total: 1 checkpoint request + 6 corridor requests** |
| Corridor batch sizes | **25, 25, 25, 25, 25, 19** |
| Total evaluation + corridor time | **12.602 s**, from Evaluate click through corridor JSON receipt; excludes preceding geocoding and subsequent inspection |
| Corridor request time | **10.733 s**, including fetch, parsing, local frame construction, and response transfer |
| All 49 frames populated | **Yes; every frame 144/144 known, total 7,056/7,056** |
| Retries / upstream 503s in this live run | **0 / 0**; all seven responses were HTTP 200 |
| Extra requests from slider/toggle | **0**, both at the browser corridor endpoint and the upstream HTTP counter |

The longest observed corridor URL was 1,222 bytes. Controlled HTTP tests separately exercise transient failures, actual retry exhaustion, response closure before backoff, `Retry-After` seconds/HTTP dates, and delays exceeding the deadline; no failure was injected into the real run. A successful public-service run does not constitute a production SLA.

Changes for this follow-up are limited to `backend/routing/providers/http.py`, `backend/routing/tests/test_http.py`, `backend/routing/tests/test_corridor.py`, and the existing README/provider-contract/verification documentation. No dependencies, tools, audits, stories, or architectural abstractions were added.

Temporary measurement artifacts: `/tmp/spotter-corridor-live-measurement.json`, `/tmp/spotter-open-meteo-events.jsonl`, `/tmp/spotter-corridor-live-map.png`, and `/tmp/spotter-corridor-e2e.json`.

## OSRM live-product verification (before the Valhalla experiment)

**Strict three-real-route acceptance remains FAIL.** A further bounded search of 22 real city pairs used the current OSRM adapter, fixed public host, identifying User-Agent, one-request-per-second limit, and unchanged `alternatives=2`/full GeoJSON/distance-duration annotations. None returned three routes. Original OSRM counts matched normalized distinct counts in every case; no third route was lost through deduplication or fabricated.

- Two routes: New York → Newark; Oakland → Berkeley; Seattle → Bellevue; Washington → Baltimore; Dallas → Fort Worth; Brussels → Antwerp; Frankfurt → Mainz; Tokyo → Yokohama; Osaka → Kyoto; São Paulo → Santo André; Buenos Aires → La Plata; Johannesburg → Pretoria.
- One route: San Jose → Oakland; Los Angeles → Santa Monica; Toronto → Mississauga; Stuttgart → Heilbronn; Bologna → Modena; Zurich → Winterthur; Birmingham → Coventry; San Francisco → Oakland; Rotterdam → Utrecht; Sydney → Parramatta.

The live UI was verified with **Berlin, Germany → Potsdam, Brandenburg, Germany**, two returned routes, 30,000 lb, and 10-mile checkpoints. Separate Chromium contexts used desktop **1440×900** and touch-enabled mobile **390×844**. Actual Photon, OSRM, Open-Meteo, and map-tile responses were used; no API responses were stubbed. The final runs reused the server's recent raw-data cache after the initial live request.

The initial visual check reproduced a blocking defect: the default live map contained route overlays on an empty background, with no streets or place names. A minimal fix in `frontend/src/features/map/TripMap.tsx` and `frontend/src/App.tsx` enables OpenStreetMap raster tiles and visible map attribution for live trips, using the existing MapLibre renderer. Initial bounds use the returned routes to avoid requesting tiles for the old default location. Demo mode retains its offline background. Routing/weather providers, risk logic, dependencies, CSP, and tooling were unchanged. The same live browser check then passed at both viewports.

| Requested requirement | Result | Concrete observation |
| --- | --- | --- |
| At least one pair returning three real routes | **FAIL** | None in the 22 additional pairs; maximum two in raw and normalized results |
| Full live flow, desktop and mobile | **PASS** | Both contexts completed trip, recommendation, checkpoint inspection, and corridor |
| Basemap | **PASS after fix** | Streets, highways, Berlin/Potsdam labels, water/land cover, and on-map OSM attribution render; all requested tiles returned HTTP 200 |
| All returned routes visible and distinguishable | **PASS for the two returned routes** | Both alternatives fit within the map; separate branches and the selected-route halo distinguish them; shared road sections overlap naturally |
| Checkpoints visible | **PASS** | Four per route at 0/10/20 miles and destination; matching checkpoint buttons remain available |
| Checkpoint ETA and risk details accessible | **PASS** | Selecting each route and checkpoint 2 shows its exact backend ETA, Low risk, and wind/rain/snow details |
| Route summaries match backend | **PASS** | 22.0/22.7 mi, 0.6/0.7 h, arrivals, average risk, and Severe/High miles match formatted API values |
| Recommendation matches backend | **PASS** | Route 1, ID `5f39aeb14660971916c5ce1f`, is the only Recommended card; inspection of route 2 does not change it |
| Heatmap | **PASS** | 144 locations, 49 populated frames, 7,056/7,056 known samples; visible density shading and exact risk points |
| Slider 0–48h without new network requests | **PASS, with uniform-data limitation** | End/Home select 48/0 and the displayed UTC time matches the selected backend frame; browser request count does not increase |
| Loading and error states | **PASS** | Evaluate is disabled and labelled while pending; a real past-departure request returns HTTP 400 with a clear message; restoring a future date completes the flow again |
| Mobile overlap, clipping, readability | **PASS** | Document width is exactly 390 px; cards, checkpoint details, controls, legend, and attribution fit; normal vertical scrolling is required |

All 49 frames in this actual trip have identical Low-risk categories. Accordingly, their heatmap colors look the same: the time changes correctly, and the unchanged appearance matches the backend. A visible transition between different real risk colors was **not demonstrated** with these uniform forecasts. No weather data was changed to manufacture a transition.

Screenshots were inspected directly: [desktop map](screenshots/live-desktop.png), [mobile map](screenshots/live-mobile.png), [mobile forecast/details](screenshots/live-mobile-forecast.png), and [mobile real validation error](screenshots/live-mobile-error.png). Map imagery © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).

No additional blocking UI defect was observed. A minor existing issue remains: demo-specific hints/badges also appear in live mode. These were left untouched under the instruction to fix only blocking defects. There were no unexpected JavaScript, CSP, or resource errors; the deliberately triggered HTTP 400 was expected and recovery succeeded in both contexts.

After the fix, typecheck, lint, production build, **20 existing unit/hook tests**, and **all 18 existing desktop/mobile E2E tests** passed. The E2E suite remains deterministic demo, with no new test infrastructure or Storybook work. The existing MapLibre chunk-size warning remains unchanged. Temporary raw evidence: `/tmp/spotter-final-route-discovery.json`, `/tmp/spotter-final-visual.json`, `/tmp/spotter-final-{desktop,mobile}-{trip,corridor}.json`, `/tmp/spotter-final-regression-e2e.json`, and the failed pre-fix screenshot `/tmp/spotter-final-desktop-map-before.png`.

## Compiled demo build and visual inspection

The same compiled build, served by Django with `DJANGO_DEBUG=0` and `PROVIDER_MODE=demo`, completed the full flow: three routes, a recommendation, checkpoint weather and ETA inspection, 49 frames, 147 locations, and **7,203/7,203 known weather samples**. Keyboard changes to hours 48 and 0 and the corridor toggle did not trigger another corridor request. All page/API/asset responses were successful, with no page JavaScript or CSP errors. Document width equalled viewport width at 1440 and 390 pixels.

Desktop and mobile screenshots of the map, forecast, form, summaries, and real-provider failure state were visually inspected. Mobile browser journeys also ran in a fresh touch-enabled Chromium context in E2E. Viewport resizing preserves map zoom, so a resized map can require panning; the fresh mobile E2E view fits the three routes. No physical-device or cross-browser claim is made.

Temporary artifacts: `/tmp/spotter-demo-final.json`, `/tmp/spotter-demo-{desktop,mobile}-{top,map,forecast}.png`, and `/tmp/weather-{desktop,mobile}.png`. Final E2E JSON reports are `/tmp/spotter-e2e-final.json` and `/tmp/spotter-e2e-repeat-final.json`; the failed timing traces are `/tmp/spotter-mobile-timeout-trace.zip` and `/tmp/spotter-mobile-axe-timeout-trace.zip`.

## Files changed in this verification

- Application fixes: `backend/config/frontend.py`, `backend/routing/domain/recommendation.py`.
- Backend coverage: `backend/routing/tests/test_frontend_delivery.py`, `test_demo.py`, `test_risk.py`, `test_end_to_end.py`.
- Frontend coverage/compatibility: `frontend/src/features/trip/useTrip.test.tsx`, `frontend/src/test/fixtures.ts`, `frontend/src/test/tooling.test.ts`, `frontend/e2e/trip-planning.spec.ts`, new `frontend/e2e/recovery.spec.ts`, and its `fixtures/all-blocked.json` / `fixtures/incomplete.json`.
- Documentation: `README.md`, this file. The README also corrects optional basemap configuration to match the existing same-origin schema.

No unrelated production refactors, new dependencies, tooling, stories, vendored packages, governance changes, or architectural abstractions were introduced by this verification.

## Valhalla routing experiment — 2026-10-15 UTC

**Recommendation: switch live routing to Valhalla.** This supersedes the OSRM-specific three-route acceptance gap above. No changes were made to weather, risk, recommendation, checkpoints, map rendering, heatmap logic, or domain/API response contracts. OSRM remains selectable with `LIVE_ROUTING_PROVIDER=osrm`; the live default is `valhalla`. Demo providers are unchanged.

Twenty preselected real city pairs reused the exact coordinates from the preceding OSRM discovery run. This is a bounded local comparison, not a load test or a statistically representative guarantee. Each Valhalla response used the FOSSGIS endpoint, `alternates: 2`, `costing: auto`, full GeoJSON in its OSRM format, and time/length shape annotations. Requests carried an identifying User-Agent and `X-Client-Id`, respected the existing one-request-per-second host limit, and used no credentials. Stable geometry hashes deduplicate actual provider routes; no via points or fabricated routes were used. All 20 responses normalized successfully, with raw and distinct counts matching.

| Number of distinct routes | OSRM, earlier run | Valhalla |
| --- | --- | --- |
| 1 | 10 | 2 |
| 2 | 10 | 4 |
| 3 | 0 | 14 |
| Errors | 0 | 0 |

The 20 Valhalla lookups took 34.572 seconds in total, including transport pacing, response transfer and validation. The earlier OSRM run was not simultaneous. Exact coordinates, route IDs, vertex counts and per-pair times are retained in [experiment results](valhalla-routing-experiment.json).

| Pair | OSRM | Valhalla |
| --- | --- | --- |
| New York → Newark | 2 | 3 |
| Oakland → Berkeley | 2 | 3 |
| San Jose → Oakland | 1 | 3 |
| Los Angeles → Santa Monica | 1 | 1 |
| Seattle → Bellevue | 2 | 2 |
| Washington → Baltimore | 2 | 3 |
| Dallas → Fort Worth | 2 | 3 |
| Toronto → Mississauga | 1 | 3 |
| Brussels → Antwerp | 2 | 2 |
| Frankfurt → Mainz | 2 | 3 |
| Stuttgart → Heilbronn | 1 | 3 |
| Bologna → Modena | 1 | 3 |
| Zurich → Winterthur | 1 | 2 |
| Birmingham → Coventry | 1 | 3 |
| San Francisco → Oakland | 1 | 1 |
| Rotterdam → Utrecht | 1 | 2 |
| Tokyo → Yokohama | 2 | 3 |
| Osaka → Kyoto | 2 | 3 |
| Sydney → Parramatta | 1 | 3 |
| São Paulo → Santo André | 2 | 3 |

The parser preserves full geometry, per-segment distances, and reported leg duration using the existing proportional reconciliation. Intermediate ETA approximation remains explicit. Valhalla annotation lengths are rounded by the upstream serializer and validated with the existing distance tolerance. The provider uses standard automobile driving costs, preserving the previous driving model; this is not a truck-clearance certification or traffic forecast. Time-dependent Valhalla requests were not enabled because they disable alternatives; application departure still controls cumulative checkpoint ETAs and weather selection. See the [official route contract](https://valhalla.github.io/valhalla/api/route/api-reference/) and [annotation serializer](https://github.com/valhalla/valhalla/blob/master/src/tyr/route_serializer_osrm.cc).

### Full live flow with three routes

The compiled app completed actual Photon → Valhalla → Open-Meteo flows in fresh desktop **1440×900** and touch-enabled mobile **390×844** Chromium contexts. Searches were **Oakland, California** → **Berkeley, California**, selecting the city results, not businesses. Photon resolved these to `[-122.271356, 37.8044557]` and `[-122.272863, 37.8708393]`. These slightly differ from the comparison coordinates; the full-flow case independently returned three routes:

- `8d8620b3d729f467cce7b8ec` — **recommended**, 7.8 mi, 779.106 s.
- `cdcc4ab90043cb45c7b9e4f7` — second distinct provider geometry.
- `3f7a6faf935964a9e8427249` — third distinct provider geometry.

City labels alone do not guarantee the same alternatives: Frankfurt → Mainz returned three at the comparison coordinates but two when selecting Photon city centers. No coordinate manipulation was used to make that UI case pass; Oakland → Berkeley was selected instead.

| Verification | Result |
| --- | --- |
| Three real, distinct routes through the UI | PASS, desktop and mobile |
| Basemap, route paths and checkpoints | PASS; OpenStreetMap tiles loaded, all three selectable paths rendered; shared segments overlap naturally |
| ETA, risk and weather detail for each route | PASS; checkpoint details matched backend response |
| Route summaries and recommended route | PASS; distance, duration, average risk, exposure and recommendation matched backend |
| Heatmap | PASS; 135 locations, 49 frames, **6,615/6,615 known samples** |
| Slider 0 → 48 and weather toggle | PASS; no additional network requests; all categories Low in this window, so no category-color transition is claimed |
| Fresh desktop evaluation + corridor | **5.991 s**, excludes geocoding and later inspection |
| Open-Meteo requests | **7 total: 1 checkpoint + 6 corridor batches (25,25,25,25,25,10)**; all 200, no retries/503s |
| Mobile repeat | PASS; 1.225 s evaluation + corridor using the same worker's raw-data caches |
| Loading and real validation-error recovery | PASS; pending action disabled; past departure rejected with actual HTTP 400, corrected input completed again |
| Mobile layout | PASS; document width 390 px, no horizontal overflow, labels and controls readable |
| Demo-only labels in live mode | PASS; generic form/header/empty-state copy, existing mode-aware synthetic label retained for demo only |
| Unexpected JavaScript/CSP/resource errors | None observed |

Visually inspected captures: [desktop map](screenshots/valhalla-live-desktop.png), [mobile map](screenshots/valhalla-live-mobile.png), [mobile forecast/checkpoint details](screenshots/valhalla-live-mobile-forecast.png), and [mobile form without demo labels](screenshots/valhalla-live-mobile-form.png). Map imagery © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). Route alternatives share the Low risk color in this weather window; selection highlights the inspected path. No new blocking UI defect was found, and no styling or map changes were made.

Provider/transport/cache regressions were written and observed failing before the adapter changes. The existing integration test was made explicit about its selected provider and now exercises both OSRM and Valhalla. No new infrastructure, dependencies, audits, stories, or unrelated tests were added. Temporary live scripts only observed actual service responses and reused the installed Playwright browser.

FOSSGIS Valhalla remains a fair-use public demo service without a production SLA; even in this sample it returned fewer than three routes for six pairs. Keep interactive use light and preserve the returned route count. The [public demo policy](https://github.com/valhalla/valhalla#demo-server) asks for identification and notification before publishing apps to end users. This experiment did not publish or contact anyone.

Final verification passed: `npm --prefix frontend run typecheck`, `npm --prefix frontend run lint`, `npm --prefix frontend run build`, **98 backend tests** (`DJANGO_SECRET_KEY=local-test-only backend/.venv/bin/python backend/manage.py test routing.tests`), **20 existing unit/hook tests** (`npm --prefix frontend run test -- --project unit --project hooks`), and **18 existing desktop/mobile E2E tests** (`PLAYWRIGHT_BROWSERS_PATH=$PWD/frontend/.cache/browsers npm --prefix frontend run test:e2e`). E2E remained deterministic demo. The pre-existing MapLibre chunk-size build warning remains; no tooling/configuration work was done to silence it.

Changed application files: `backend/routing/providers/valhalla.py` (new adapter), `backend/routing/providers/http.py` (fixed destination/header/rate-limit inclusion only), `backend/config/settings.py` (routing selection), `backend/routing/services/trips.py` and `cache.py` (provider selection/cache identity), `frontend/src/App.tsx` and `features/trip/TripForm.tsx` (demo copy and routing attribution only). Directly affected tests: `backend/routing/tests/test_valhalla.py` and `test_end_to_end.py`. Documentation/evidence: README, provider contracts, this report, the experiment JSON and four screenshots. No OSRM provider code was deleted or modified.
