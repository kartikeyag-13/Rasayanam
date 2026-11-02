# 🏗️ Rasayanam — System Architecture

This document describes the complete architecture of the Rasayanam platform: an AI-powered neighborhood air-pollution prediction and health-advisory system for the NCR–Punjab–Haryana region, focused on the Diwali pollution cycle.

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA LAYER                                       │
│                                                                                 │
│  Historical training / chart dataset (2020–2025)                               │
│  Open-Meteo Air Quality API (CAMS) + Weather API for current model-grid inputs  │
│  (46,848 rows · 3-hourly · 8 stations · 2020-09 → 2025-12)                      │
│  weather · pollutants · lags · cyclic time features                             │
└───────────────┬─────────────────────────────────────────────────────────────────┘
                │  batch read (pandas)
                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 ML LAYER                                        │
│                                                                                 │
│  ml/train.py                                                                    │
│   ├─ feature engineering (lags, rollings, seasonality, Diwali proximity)        │
│   ├─ CPCB AQI target computation                                               │
│   ├─ time-ordered train/test split                                              │
│   ├─ HistGradientBoostingRegressor × {PM2.5, AQI} (3h & 24h horizons)          │
│   └─ exports → ml/artifacts/{model.joblib, metrics.json, feature_spec.json}    │
└───────────────┬─────────────────────────────────────────────────────────────────┘
                │  joblib load at boot
                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               BACKEND LAYER                                     │
│                        FastAPI + Uvicorn (async Python)                         │
│                                                                                 │
│  backend/feed.py      historical dataset access + chart history                 │
│  backend/live.py      cached Open-Meteo CAMS current pollutant estimates         │
│  backend/aqi.py       CPCB sub-index math, AQI category, health advisories      │
│  backend/forecast.py  hourly CAMS forecast → CPCB AQI, sampled every 3h (up to 7 days)          │
│  backend/main.py      ┌──────────────────────────────┐                          │
│                       │  REST API (JSON)             │  /api/*                 │
│                       ├──────────────────────────────┤                          │
│                       │  WEBSOCKET SERVER  /ws       │  broadcast every 10 min  │
│                       ├──────────────────────────────┤                          │
│                       │  Static file host            │  /static + /            │
│                       └──────────────────────────────┘                          │
└───────────────┬─────────────────────────────────────────────────────────────────┘
                │  JSON over HTTP / frames over WS
                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                        (SPA)       │
│                     vanilla HTML/CSS/JS + Chart.js                              │
│                                                                                 │
│  ┌──────────────┐ ┌────────────────┐ ┌───────────────┐ ┌──────────────────────┐  │
│  │ Live AQI     │ │ PM Reports     │ │ Predictions   │ │ Health Corner        │  │
│  │ gauge +      │ │ interactive    │ │ 7-day CAMS AQI forecast  │ │ nurse · breathing    │  │
│  │ station      │ │ pollutant      │ │ + Diwali      │ │ exercises · teas &   │  │
│  │ selector     │ │ charts         │ │ climatology   │ │ remedies · doctors   │  │
│  └──────────────┘ └────────────────┘ └───────────────┘ └──────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────────┐    │
│  │ Learn: authoritative articles on AQI → respiratory disease               │    │
│  └──────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Detail

### 2.1 Data Layer

| Aspect | Design |
|---|---|
| Source file | `ncr_punjab_haryana_weather_aqi_2020_2025.csv` (repo root, overridable via `DATA_PATH`) |
| Grain | 3-hourly observations per station |
| Coverage | 4 regions — Delhi, NCR (Gurugram, Noida), Haryana (Ambala, Hisar), Punjab (Amritsar, Ludhiana) |
| Access pattern | Loaded **once into memory** (pandas) at process start; per-station sorted DataFrames with an index on `timestamp`; time-range slices served from cache |
| Re-read strategy | `feed.reload()` available; production would swap this module for a streaming DB (TimescaleDB/InfluxDB) without touching callers |

### 2.2 ML Layer

**Goal:** predict neighborhood-level pollution *before, during, and after Diwali*.

```
raw rows
  → clean timestamps (date + hour), per-station sort
  → CPCB AQI computation from pollutant columns (target `aqi`)
  → features:
        pollutants: pm25/pm10/no2/so2/co lags (1 step, 8 steps=24h), rolling means (24h)
        weather:    temp, humidity, dew point, pressure, precipitation,
                    wind speed/direction, u/v 10m components + lags
        cyclical:   sin/cos hour, sin/cos month, day-of-year
        diwali:     days_to_diwali, is_diwali_window (Oct 1 – Nov 30)
  → time-ordered split: train ≤ 2024-12-31, test = 2025 (strictly future)
  → models: HistGradientBoostingRegressor
        pm25_h3, aqi_h3   (3-hour-ahead, primary)
        pm25_h24, aqi_h24 (24-hour-ahead, next-day advisory)
  → artifacts: ml/artifacts/model.joblib + metrics.json + feature_spec.json
```

**Serving (`backend/forecast.py`)** — the user-facing outlook samples available CAMS pollutant values every three hours and recalculates CPCB sub-indices at each timestamp. Weather values are attached when matching hourly forecasts exist. The local gradient-boosted models remain available for short-horizon experiments; recursive fallback is limited to 48 hours, requires a recent live observation, and explicitly notes that weather and unmodeled species persist. Without a recent live seed, forecast points are empty and marked unavailable.

**Why gradient boosting:** tabular, mixed-scale, non-linear interaction between wind/humidity/lags and pollutants; robust to missing values; trains in seconds on this dataset; interpretable enough via `feature_importances_`.

### 2.3 Backend Layer (FastAPI)

| Module | Responsibility |
|---|---|
| `backend/aqi.py` | CPCB breakpoint interpolation for supported PM2.5, PM10, NO₂, SO₂ and CO values → maximum valid sub-index; category (Good → Severe). Missing species are excluded; these five CAMS species do not constitute all CPCB AQI inputs or regulatory 24-hour monitor averages. |
| `backend/feed.py` | In-memory dataset; `latest_per_station()`, `history(station, hours)`, station metadata |
| `backend/forecast.py` | CAMS hourly pollutant and matching weather forecasts → CPCB AQI at available 3-hour timestamps; recent-seed local ML fallback capped at 48h |
| `backend/main.py` | App wiring: REST routes, **WebSocket `/ws`**, static hosting, background broadcast task |

#### REST endpoints

```
GET /api/health        → status, interval, model info
GET /api/stations      → 8 stations with metadata
GET /api/current       → current CAMS grid estimate → CPCB-breakpoint AQI;
                           historical CSV fallback is explicitly marked
GET /api/history       → recent CAMS time series up to 48h; returns no points rather than stale CSV if live history is unavailable; longer ranges use labelled CSV history
GET /api/forecast      → timestamped CAMS forecast for available horizon; recent-seed ML fallback ≤48h; otherwise unavailable
GET /api/diwali        → historical before/during/after Diwali climatology
GET /api/articles      → curated respiratory-health references
GET /api/doctors       → doctor & ENT directory (?city, ?specialty)
GET /api/remedies      → herbal teas & home remedies
```

#### WebSocket protocol (`/ws`)

*Server → client frames (JSON):*

```jsonc
// 1) sent immediately on connect (snapshot)
{ "type": "snapshot", "server_time": "...", "interval_seconds": 600,
  "stations": [ { "station_id", "city", "state", "lat", "lon",
                  "reading": { temp_c, humidity, pm25, pm10, no2, so2, co, ... },
                  "aqi": 312, "category": "Severe", "color": "#7e0023",
                  "advisory": { "summary", "do", "avoid" } } ],
  "forecast": { "station_id": [ { "ts", "aqi", "pm25" }, ... ] } }

// 2) every 10 minutes (WS_BROADCAST_INTERVAL, default 600 s)
{ "type": "broadcast", "server_time": "...", "seq": 42,
  "stations": [ ... same shape ... ],
  "forecast": { ... } }

// 3) heartbeats
{ "type": "ping", "server_time": "..." }
```

*Client → server:* none required; the server answers WS ping frames automatically (uvicorn) and tolerates silent clients. Clients receive `snapshot` on connect, so the UI is never empty between broadcasts.

**Broadcast loop** (asyncio task started on app startup):

```
every WS_BROADCAST_INTERVAL seconds:
    stations = feed.latest_per_station()          # latest cached CAMS model-grid estimate (or labelled historical fallback)
    for s in stations: s["aqi"], s["category"] = aqi.compute(...)
    forecasts = forecast.forecast_all(steps=56, live_bundles)
    await hub.broadcast({type: "broadcast", ...})  # to all open client sockets
```

### 2.4 Frontend Layer (Static SPA)

```
static/
├── index.html      complete responsive SPA, inline design system and scripts
├── remedy.html     data-driven recipe detail page
└── assets/         supplied Rasayanam intro video
```

**Realtime client:** opens `ws://<host>/ws`, renders the snapshot and updates the AQI gauge and forecast on each broadcast, then reconnects with exponential backoff. REST serves history, map, forecast and health content.

**Sections & data sources:**

| Section | Source |
|---|---|
| Live AQI gauge + pollutant chips | WS `stations` + `/api/current` |
| PM reports (interactive charts) | `/api/history` + Chart.js; 24h uses live CAMS history only (empty/error state if unavailable; no silent stale-CSV substitution); longer windows use historical CSV with explicit source metadata |
| Forecast outlook + Diwali panel | WS `forecast` + `/api/forecast` + `/api/diwali`; only returned timestamps are displayed |
| Health advisory ("personal nurse") | derived from AQI category server-side |
| Breathing exercises | pure client-side guided animation (box / 4-7-8 / diaphragmatic) |
| Teas & remedies | `/api/remedies` |
| Doctors & ENT specialists | `/api/doctors` (filter by city/specialty) |
| Learn (articles) | `/api/articles` |

---

## 3. Deployment Topology

**Development / demo (this repo):**

```
uvicorn backend.main:app --host 0.0.0.0 --port 8000
        │
        ├─ serves static/ website on /
        ├─ REST on /api/*
        └─ WebSocket on /ws   (broadcast default: every 600 s)
```

**Production (target):**

```
                 ┌── Nginx (TLS, /ws upgrade, static cache)
                 ▼
        ┌────────────────────┐        ┌──────────────────────┐
        │ Uvicorn workers ×N │───────▶│ Redis pub/sub         │
        │ FastAPI + WS hub   │        │ (cross-worker fanout) │
        └────────┬───────────┘        └──────────────────────┘
                 │
        ┌────────▼───────────┐        ┌──────────────────────┐
        │ TimescaleDB / PG   │◀───────│ CPCB + OpenAQ ingest │
        │ time-series store  │        │ (streaming collector)│
        └────────┬───────────┘        └──────────────────────┘
                 │ nightly/rolling retrain
        ┌────────▼───────────┐
        │ ML retrain pipeline│ → model registry (S3/MLflow)
        └────────────────────┘
```

---

## 4. Key Design Decisions

1. **One Python service** for ML + REST + WebSocket — predictions and pushes share the same in-memory model/data, no serialization hop, minimal moving parts.
2. **Push ≠ polling**: clients never poll; the 10-minute cadence lives server-side (`WS_BROADCAST_INTERVAL`), with an on-connect snapshot so the UI is instant.
3. **AQI computed server-side** with official CPCB breakpoints so every client sees identical, authoritative numbers.
4. **Strictly time-ordered ML splits** — a random split would leak the future and inflate metrics; the 2025 hold-out mirrors real forecasting.
5. **Data access behind `feed.py`** — swapping the CSV for a live database is a one-module change.
6. **Static vanilla frontend** — no build step, opens anywhere, Chart.js for interactivity; easily replaceable by React/Next.js later without backend changes.
7. **10-minute default, env-configurable** — meets the spec while keeping demos practical (`WS_BROADCAST_INTERVAL=30`).

---

## 5. Data / Control Flow Summary

```
[CSV 2020-2025] ──train──▶ [ML artifacts]
                              │ load
[client browser] ◀──WS/10min──[FastAPI backend]──load──▶ [in-memory feed]
      │                          │  ▲
      │ fetch REST               │  │ REST /api/*
      └──────────────────────────┘  │
      └────── renders: live AQI · PM charts · 7-day CAMS AQI forecast · Diwali panel ·
                      health nurse · breathing · remedies · doctors · articles
```


## 6. Current conditions and extended forecast (updated)

### Current AQI source

`backend/live.py` calls the Open-Meteo Air Quality API for PM2.5, PM10, CO, NO₂ and SO₂ at each station's latitude/longitude, plus the Open-Meteo Weather API for current and hourly weather. Responses are cached for 15 minutes. The provider retrieves recent hourly pollutant/weather history for lag features. `backend/main.py` applies `backend/aqi.py` CPCB pollutant breakpoints and attaches source metadata.

**Important provenance:** Open-Meteo's air-quality values are CAMS atmospheric model-grid estimates (approximately 11–45 km), not CPCB reference-monitor readings. The dashboard labels them as model estimates. If the upstream API fails, the service can show the latest CSV row only with historical provenance; it must not be represented as current measured data.

### Timestamped CAMS AQI forecast

`backend/live.py` retains the complete hourly air-quality response from Open-Meteo. `ForecastService.forecast_station_from_cams()` samples future hourly pollutant concentrations at 3-hour targets, converts CO from µg/m³ to mg/m³, calculates CPCB sub-indices for each available pollutant, and takes the maximum valid sub-index as the AQI. It returns only timestamps for which upstream pollutant values are available; it does not repeat missing pollutant values or recursively feed predictions into the next step.

The local `HistGradientBoostingRegressor` artifacts are retained for short-horizon experimentation. If the CAMS hourly forecast is unavailable, a clearly labelled local ML fallback is permitted only when the current observation is no more than six hours old, and is limited to 48 hours. The fallback persists weather and four pollutant species, so it is experimental. Without a recent seed, the API returns an unavailable forecast with no points. CAMS forecasts are gridded model estimates, not CPCB monitor forecasts.

The API may return fewer than 56 points if the provider does not supply a full 168-hour window from the current timestamp. The frontend timeline selects from the returned points and must not invent missing values.

References:
- Open-Meteo Air Quality API: https://open-meteo.com/en/docs/air-quality-api
- Open-Meteo Weather API: https://open-meteo.com/en/docs

## Regional AQI map

The frontend includes a Leaflet-based regional map for the eight configured NCR, Punjab and Haryana sample locations. It consumes `GET /api/map`, which returns current station payloads plus available timestamped forecast points per station. The map renders AQI-colored markers, pollutant and weather detail popups, an optional heat layer, and optional illustrative alert halos for AQI values above 200. Its 3-hour timeline and play/pause control stop at the longest timestamp actually returned; stations without a matching point are omitted for that time.

**Spatial interpretation constraint:** the eight coordinates are sparse point samples. The heat layer is a smoothed visual interpolation, not a measured continuous pollution field. Alert halos are illustrative visual emphasis, not validated danger-zone boundaries. Current values are CAMS model-grid estimates where available (not CPCB ground-monitor readings); historical CSV fallback is source-labelled. Forecast values are CAMS model-grid estimates; uncertainty increases with forecast lead time and the sparse station sample does not establish street-level conditions. The frontend uses Leaflet and Leaflet.heat from CDNs and OpenStreetMap tiles with attribution.

### Map API

`GET /api/map`

Returns `region`, `data_as_of`, `stations[]`, `forecast{station_id:{base_time,step_hours,confidence_note,points[]}}`, and `spatial_note`. Each station includes configured coordinates, AQI category/color, timestamp, source and pollutant readings. Forecast points contain their actual timestamp, AQI, available pollutant concentrations and matching weather fields. No missing timestamps or values are synthesized.


## Forecasting correction (current implementation)

The public forecast is sourced from the hourly CAMS air-quality forecast returned by `backend/live.py`. `ForecastService.forecast_station_from_cams()` samples available hourly pollutant values at 3-hour targets, converts CO from µg/m³ to mg/m³, computes each pollutant CPCB sub-index, and takes the maximum valid sub-index as AQI. Missing samples are not filled by persistence. The returned horizon reflects actual provider coverage. Local HistGradientBoosting models are retained for short-horizon experiments; fallback requires a live seed no older than six hours, is capped at 48 hours, and documents its persistence assumptions. If such a seed is missing or stale, there are no forecast points.

The old near-constant severe local rollout is reproducible from the model code: every predicted AQI and PM2.5 value feeds the next 3-hour step, four other pollutants are persisted, and weather is held constant. Starting from a historical AQI-500 event (2020-11-01), six of eight station traces stayed within a 2–9 point band over 56 recursive steps; the remaining traces spanned 16 and 19 points. That behavior is input-dependent convergence under persistence assumptions, not a credible seven-day trajectory. The public forecast avoids that loop by evaluating CAMS pollutant concentrations at their returned timestamps; the local recursive model is retained only as a labelled ≤48-hour experiment with a recent live seed.

### Frontend opening animation

The static home page uses `static/assets/rasayanam-intro.mp4`. The logo from its final frame is provided as the transparent `static/assets/rasayanam-wordmark.png`. A single image element in the header is faded in over that frame, then animated into its final top-left coordinates while navigation and page content reveal. The video uses `cover` on landscape and `contain` on portrait screens. Skip, video-error, autoplay-failure, once-per-session and `prefers-reduced-motion` paths bypass or end the sequence. Intersection Observer drives both content reveals and a five-stage chapter rail; the active chapter updates a subtle ambient accent from atmosphere through protection. Core data remains accessible without animation.

### Remedy detail routes

`GET /api/remedies` returns recipe cards; `/remedies/{id}` serves `static/remedy.html`, which loads `GET /api/remedies/{id}`. Recipe detail includes ingredients, preparation, time/servings where appropriate, traditional Ayurvedic framing, evidence limits, cautions and references. No remedy is described as preventing or reversing pollution injury.
