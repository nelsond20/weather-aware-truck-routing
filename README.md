# Weather-aware truck routing — Spotter assessment

A React + Django application for comparing weather exposure across up to three real driving routes. It estimates arrival times at checkpoints, applies wind/rain/snow risk rules using the entered truck load, and recommends the best eligible route under those rules. MapLibre displays the routes, checkpoints, and a weather heatmap with 49 hourly frames from hour 0 through hour 48.

**No third-party credentials, API keys, or paid accounts are required.** Live mode uses Photon for geocoding, Valhalla for routing by default, and Open-Meteo for weather. OSRM remains available by configuration. A separate deterministic demo mode works without external services.

## Run locally

Prerequisites: Python 3.12 and Node 24.15+ (24.x), with npm. Run commands from the repository root.

For a fresh checkout:

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.lock
npm --prefix frontend ci --ignore-scripts
```

If your Python installation has no `venv`/`ensurepip` support and you already use `uv`, the equivalent Python setup is:

```sh
uv venv --python 3.12 backend/.venv
uv pip install --python backend/.venv/bin/python -r backend/requirements.lock
```

Start Django in **live mode** in one terminal:

```sh
export DJANGO_SECRET_KEY="$(backend/.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export DJANGO_DEBUG=1
export PROVIDER_MODE=live
export LIVE_ROUTING_PROVIDER=valhalla
backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 --noreload
```

Start React in another:

```sh
npm --prefix frontend run dev
```

Open **http://127.0.0.1:5173**. Vite proxies `/api/` to Django. The generated `DJANGO_SECRET_KEY` is an application secret required by Django; it is not a credential for any third-party service. Do not commit it. Live mode needs internet access to the public APIs and OpenStreetMap tiles.

Search **Oakland, California** and **Berkeley, California**, select the city candidates, keep a near-future departure with an explicit UTC offset, and evaluate. Inspect route summaries and checkpoints, then move the forecast slider. This pair produced three distinct routes during verification; public services and exact selected coordinates can change that result.

To run the deterministic demo instead, stop Django, set `PROVIDER_MODE=demo` in that terminal, and rerun the same backend command. No other configuration change is needed. If omitted, `PROVIDER_MODE` defaults to `demo`; the commands above explicitly enable live mode.

## Try the deterministic assessment flow

Use `PROVIDER_MODE=demo` for this repeatable scenario. Its routes and forecasts are synthetic and require no external weather requests or map tiles.

1. Search **West** for origin and select **West Depot · Synthetic origin**. Search **East** and select **East Depot · Synthetic destination**.
2. Enter a future departure with an explicit UTC offset, such as an ISO timestamp ending in `Z`. Choose checkpoint spacing of 10, 25, or 50 miles.
3. Evaluate at **30,000 lb**, then at **30,001 lb**. The northern route becomes **No Travel** when its wind meets the heavy-load rule; blocked routes remain inspectable.
4. Compare route summaries, the recommendation, ETAs, and checkpoint weather. Click a route on the map or use its inspection button; checkpoint buttons provide the same details without map interaction.
5. Move the forecast slider between **0 and 48**. Frames are already loaded, so changing the hour makes no additional API request. Toggle corridor weather to compare it with arrival-time route risk.

The demo is synthetic and geographically limited to West Depot → East Depot. Both endpoints are shared by all routes, so some exposure is shared. A corridor forecast failure leaves the route recommendation available.

## Live providers

Backend environment configuration:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PROVIDER_MODE` | `demo` | `live` uses public APIs; `demo` uses deterministic local data. |
| `LIVE_ROUTING_PROVIDER` | **`valhalla`** | Live routing engine: `valhalla` or `osrm`. Ignored by demo routing. |
| `DJANGO_SECRET_KEY` | Required | Django application secret; not a third-party credential. |
| `DJANGO_DEBUG` | `0` | Set to `1` for local development only. |

Valhalla is the **default routing provider when live mode is enabled**. Photon geocoding and Open-Meteo weather stay the same when switching routing engines. To use the retained OSRM implementation, stop Django and run in the configured backend terminal:

```sh
export PROVIDER_MODE=live
export LIVE_ROUTING_PROVIDER=osrm
backend/.venv/bin/python backend/manage.py runserver 127.0.0.1:8000 --noreload
```

Use `LIVE_ROUTING_PROVIDER=valhalla` to switch back. Restart Django after changing either variable. Invalid provider values fail at startup; route-cache keys include the selected provider. OSRM is an explicit alternative, not an automatic failover.

Valhalla requests `alternates: 2`, ordinary driving costs (`auto`), full GeoJSON geometry, and segment time/distance annotations through its OSRM-compatible response format. Time-dependent Valhalla routing is disabled because it does not support alternatives; the application's departure still determines checkpoint ETAs and forecast selection. Routes do not certify truck dimensions or road-weight restrictions.

OSRM remains available and requests `alternatives=2`, `geometries=geojson`, `overview=full`, and `annotations=distance,duration`. Both providers request up to three distinct routes; fewer alternatives are returned as-is with the existing warning. Photon candidates retain the same ID/label/coordinate format consumed by the frontend. Exact coordinates affect the alternatives, even within the same city.

Segment-duration annotations can differ from reported leg time, including turn costs. The parser distributes reported leg duration proportionally across the annotated segments so total travel time is preserved, and marks intermediate ETAs approximate when this adjustment is needed. Provider details are documented in [provider contracts](docs/provider-contracts.md).

### Public endpoint limitations

**These public endpoints are suitable for assessment/demo use, not production SLA usage.** Photon, FOSSGIS Valhalla, OSRM, Open-Meteo, and map tiles can throttle, reject requests, change coverage/data, or become unavailable. Neither routing engine guarantees three alternatives. Fewer distinct routes are shown as returned, with a warning; the app never fabricates routes or inserts artificial via points. Missing forecast coverage remains unknown.

The server identifies API requests as `WeatherAwareTruckRouting/0.1 (Spotter assessment/demo)` and additionally sends `X-Client-Id: weather-aware-truck-routing-spotter-assessment` to Valhalla. Requests are spaced at most once per second per public geocoding/routing host across users in one worker; HTTP 429 pauses requests to that host for its `Retry-After` interval (60 seconds if absent/invalid). Photon/Valhalla/OSRM requests are not automatically retried. Raw routes are cached for one hour; geocoding results are not cached. Keep usage interactive and light; do not use these endpoints for bulk jobs or load tests. See the [Photon usage terms](https://github.com/komoot/photon#demo-server), [FOSSGIS Valhalla demo policy](https://github.com/valhalla/valhalla#demo-server), and [OSRM demo policy](https://github.com/Project-OSRM/osrm-backend/wiki/Api-usage-policy). FOSSGIS asks apps published to end users to identify themselves and notify the maintainers via GitHub Discussions.

Open-Meteo requests group up to 25 locations and fetch the entire hourly window with calendar-day padding, requesting only `wind_speed_10m,rain,snowfall`. The server constructs all 49 frames locally and caches raw series for 900 seconds; moving the slider makes no network requests. Only Open-Meteo HTTP 429/502/503/504 responses are retried, at most twice, with 1- and 2-second exponential backoff or a longer valid `Retry-After`. Connections allow 5 seconds and reads 20 seconds, both clamped to the remaining 45-second operation budget. A retry that cannot fit the budget fails without waiting; network timeouts, invalid data, and other HTTP errors are not retried.

Live services can return incomplete weather or provider errors; the UI reports these rather than fabricating results. Browser E2E tests retain deterministic demo providers. Real public-provider requests are checked separately with a bounded number of public-location queries.

Live maps use OpenStreetMap raster tiles in MapLibre, with visible on-map attribution; routes, checkpoints, and heatmap layers render locally. Demo mode retains its empty background and works without external tiles. The browser requests only the current map view, uses ordinary HTTP caching, and sends its normal Referer; observe the [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/) and avoid bulk/offline downloads. The optional `VITE_MAP_STYLE_URL` accepts only a same-origin path such as `/map-styles/custom.json`, configured **before building**. The operator must serve that reviewed style and its required assets; the assessment build does not ship a `/map-styles/` delivery route. Arbitrary external style URLs are rejected by the environment schema. Any value prefixed `VITE_` is public.

## Risk model and assumptions

The assessment uses fixed rule-based categories, not calibrated accident probabilities. Wind is in **mph**, rain and snowfall rates in **inches/hour**, and entered load in **pounds**. The baseline thresholds are:

| Level | Wind (mph) | Rain (in/hr) | Snow (in/hr) |
| --- | --- | --- | --- |
| Low | <25 | <0.10 | <0.5 |
| Moderate | 25–<35 | 0.10–<0.25 | 0.5–<1 |
| High | 35–<45 | 0.25–<0.50 | 1–<2 |
| Severe | 45–<55 | 0.50–1.00 | 2–3 |
| No Travel | ≥55 | >1.00 | >3 |

Wind of 45–<55 mph with load **>30,000 lb** is No Travel. Wind of 35–<45 mph with load **>40,000 lb** is Severe. The inequalities are strict: exactly 30,000 or 40,000 lb does not trigger the corresponding override. Load is assumed constant throughout the trip and affects these wind rules only; it does not configure routing weight restrictions.

Weather and timing assumptions:

- Wind uses Open-Meteo `wind_speed_10m`, not gusts or wind direction. At a checkpoint ETA, the nearest covered hourly value within 30 minutes is selected; an equal-distance tie uses the earlier hour.
- Rain uses `rain`, converted from mm to inches; snowfall uses `snowfall`, converted from cm to inches. Both are preceding-hour accumulations treated as hourly average rates for the interval containing the ETA. They are not instantaneous precipitation intensity. The separate `showers` variable is not requested, so convective showers are excluded from the rain model.
- All calculations use UTC. No weather is extrapolated beyond returned coverage. Missing, negative, or non-finite measurements remain unknown; they are never silently classified as Low.
- Checkpoints include the origin and destination, with samples every 10, 25, or 50 annotated route miles. ETAs accumulate provider segment times and interpolate within a segment. Rest/fuel/loading stops, mandatory driving breaks, and departure-dependent traffic are not modeled. Sampling can miss hazards between checkpoints.

With complete weather, the worst wind/rain/snow category determines checkpoint risk. If any variable is missing, the checkpoint's overall category is unknown, while its worst known condition remains visible. A known No Travel condition blocks a route even if other weather is missing.

Each interval takes the worse category of its two endpoint checkpoints; an incomplete endpoint makes that interval's exposure unknown. The route average is distance-weighted using Low=0, Moderate=1, High=2, Severe=3, and No Travel=4. It is a comparison score, not a safety probability, and remains unavailable for incomplete routes. Only complete, unblocked routes are eligible for recommendation, ordered by:

1. Fewest Severe miles.
2. Fewest High miles.
3. Lowest distance-weighted average risk.
4. Shortest duration, then stable route ID to resolve ties.

If no route is eligible, the app gives no recommendation. The result ranks only the alternatives actually returned by the provider; it is not a guarantee of safe travel.

The corridor extends 20 miles to either side, uses an adaptive grid capped at 150 locations, and has 49 hourly frames anchored to the current whole UTC hour by default, independently of departure time. Smoothed heatmap intensity blends sample density and risk weight; point colors show exact sampled categories. This sampled forecast is not continuous road-condition coverage. Moving the corridor slider does not change the arrival-based recommendation.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health/` | Status and provider mode |
| `GET /api/geocode/?q=West` | Location candidates |
| `POST /api/trips/evaluate/` | Route alternatives, checkpoints, exposure, recommendation |
| `POST /api/weather/corridor/` | Corridor locations and hourly weather-risk frames |

Trip bodies contain `origin` and `destination` objects (`longitude`, `latitude`), a future ISO 8601 `departure_at` with an explicit UTC offset, numeric `load_lb`, and `spacing_miles` (10, 25, or 50). Choose a near-future departure within the available forecast horizon; farther-future timestamps can have incomplete weather coverage.

Corridor bodies contain `routes` (GeoJSON LineStrings from the trip response), `load_lb`, and optionally `base_time` (a recent whole UTC hour). Errors use `{code, message, retryable}`. Backend inputs are validated with strict DRF serializers; frontend responses are validated with Zod.

## Verify

Install Chromium once before running the full frontend or E2E suite:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend exec -- playwright install chromium
```

```sh
npm --prefix frontend run typecheck
npm --prefix frontend run lint
PROVIDER_MODE=demo backend/.venv/bin/python backend/manage.py test routing.tests
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test
npm --prefix frontend run build
```

For E2E, stop any servers occupying ports 8000/5173. The tests start their own backend and frontend:

```sh
PLAYWRIGHT_BROWSERS_PATH="$PWD/frontend/.cache/browsers" npm --prefix frontend run test:e2e
```

The last implementation verification passed **98 backend tests, 20 frontend unit/hook tests, and 18 desktop/mobile E2E tests**, plus typecheck, lint, and build. To run just the unit/hook projects, use `npm --prefix frontend run test -- --project unit --project hooks`; the full `test` command also includes existing browser-based stories. Run browser suites sequentially. E2E starts deterministic demo providers; its core journey uses the real Django backend and recovery journeys stub selected responses. It does not depend on live public APIs.

See [verification evidence and remaining delivery gaps](docs/verification.md) for reproducible commands, desktop/mobile checks, and the Valhalla comparison. Valhalla returned three distinct routes for **14 of 20** tested pairs, versus **0 of 20** for the same pairs in the earlier OSRM run. This supports the live default without guaranteeing three alternatives for every trip. Passing tests provide evidence for these cases; they do not prove that every possible input or service failure is covered.

The latest real **Oakland → Berkeley** browser check passed with zero third-party credentials in desktop and mobile: **three distinct Valhalla routes**, arrival weather, a backend-matching recommendation, **135 corridor locations, all 49 frames, and 6,615/6,615 known samples**. The fresh desktop evaluation plus corridor took **5.99 seconds**. Open-Meteo received **7 requests: 1 for checkpoints and 6 corridor batches**, all HTTP 200, with zero retries/503s. Moving the slider made no requests. All sampled risk categories remained Low across this weather window, so no category-color transition is claimed. Earlier live checks had failed during public-service unavailability; this successful run does not provide a production SLA.

## Production deployment

Build React locally with `npm --prefix frontend run build`. Deploy `backend/` and `frontend/dist/` together, retaining that directory layout. Django serves the compiled page at `/`, hashed JS/CSS at `/assets/`, and the API at `/api/` on one origin. No database migrations or persistent database are needed. `config.wsgi.application` is the production entry point; **`runserver` is only for local use**.

One deployment option that needs no additional project dependencies is a host with managed Django WSGI support, such as [PythonAnywhere](https://help.pythonanywhere.com/pages/DeployExistingDjangoProject). Upload the code and compiled frontend, create a Python 3.12 virtual environment, install `backend/requirements.lock`, and create a **Manual Configuration** web app using that environment.

In the host's private WSGI configuration, adapt the paths/domain and set the environment before loading Django:

```python
import os
import sys

sys.path.insert(0, '/home/YOUR_USERNAME/weather-aware-truck-routing/backend')
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['DJANGO_SECRET_KEY'] = 'REPLACE_WITH_A_RANDOM_SECRET_STORED_ONLY_ON_THE_HOST'
os.environ['DJANGO_ALLOWED_HOSTS'] = 'YOUR_USERNAME.pythonanywhere.com'
os.environ['DJANGO_DEBUG'] = '0'
os.environ['PROVIDER_MODE'] = 'demo'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

Generate the production secret independently; never reuse local/test keys or commit the private WSGI file. For credential-free live mode, change `PROVIDER_MODE` to `live`. This application's HTTP client disables environment proxies; PythonAnywhere's [free-tier outbound proxy restrictions](https://help.pythonanywhere.com/pages/403ForbiddenError) mean demo mode is the suitable free-tier path. Live mode needs direct HTTPS access to `photon.komoot.io`, `valhalla1.openstreetmap.de` (or `router.project-osrm.org` when selecting OSRM), and `api.open-meteo.com`. Hosting the application does not give the public routing/geocoding services a production SLA; sustained production usage needs appropriately hosted or contracted services.

Enable the host's forced-HTTPS option. If HTTPS reaches Django directly, you can additionally set `DJANGO_SECURE_SSL_REDIRECT=1`. Behind a trusted proxy that strips/replaces `X-Forwarded-Proto`, also set `DJANGO_TRUST_PROXY_HTTPS=1` before enabling Django redirects; otherwise let the host enforce HTTPS to avoid redirect loops. Production responses include CSP, framing protection, and content-type/referrer headers. Scripts require the same origin; inline styles remain allowed because MapLibre positions its canvas and controls dynamically. Zod runs without dynamic code generation.

Keep **one application worker** for this assessment: caches, admission control, and rate limits are process-local. Expensive operations allow two concurrent requests and a 45-second budget. Geocoding/evaluation/corridor limits are 30/10/5 requests per minute per directly connected IP; a proxy may make that a shared limit. Multiple workers require shared limits/cache outside this assessment's scope. Disable or redact access-log query strings at the host because geocoding queries can contain personal location data.

After reloading the host, check `/api/health/`, open `/`, and repeat the demo flow on desktop and mobile. Verify no missing assets, CSP errors, or HTTP redirects. Deployment is **prepared locally, not published**; the public URL, GitHub repository URL, and 5–10 minute Loom link remain delivery items to fill after hosting/upload.

## Implementation notes and limits

- `backend/routing/domain/`: risk rules, geometry/checkpoints, forecast alignment, recommendation.
- `backend/routing/providers/`: deterministic demo, Photon, Valhalla, retained OSRM, Open-Meteo, bounded HTTP calls.
- `backend/routing/services/` and `api/`: orchestration, raw-data caching, validation, request limits.
- `frontend/src/`: trip form/state, route summaries, lazy MapLibre map, corridor slider, strict API contracts.

Weather is an hourly forecast, not a guarantee of safe travel. Arrival estimates follow the provider's driving timings, not truck-specific road restrictions or hours-of-service rules. Open-Meteo `rain` excludes its separate `showers` field; rain classification here uses that documented product. Checkpoint sampling can miss hazards between samples. Unknown data is never silently treated as Low risk.

Original assessment, approved design, and plan are under `docs/docs/`.

## Attribution

Map and geocoding data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). Routing by [Valhalla, hosted by FOSSGIS](https://valhalla.openstreetmap.de/) or the retained [OSRM](https://project-osrm.org/), geocoding by [Photon](https://photon.komoot.io/), and weather by [Open-Meteo](https://open-meteo.com/). These sources and an OpenStreetMap correction link are also displayed in the application. Attribution does not imply endorsement or guaranteed service availability.
