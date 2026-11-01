#  Rasayanam — System Architecture

This document describes the complete architecture of the Rasayanam platform: an AI-powered neighborhood air-pollution prediction and health-advisory system for the NCR–Punjab–Haryana region, focused on the Diwali pollution cycle.

---

## 1. High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                DATA LAYER                                       │
│                                                                                 │
│  Historical training/chart dataset (2020–2025)                               │
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
│   ├─ feature engineering (lags, rolling, seasonality, Diwali proximity)        │
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
│  backend/forecast.py  recursive 7-day (56 × 3h) ML rollout per station          │
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
│  │ gauge +      │ │ interactive    │ │ 7-day recursive forecast  │ │ nurse · breathing    │  │
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

**Serving (`backend/forecast.py`)** — recursive rollout: take the latest observed row, predict step *t+1*, append prediction as the lag for step *t+2*, repeat to build a 7-day (56-step) trajectory of PM2.5 and AQI per station. Model artifacts are loaded once at process start; forecasts are recomputed on each broadcast tick (cheap: 8 stations × 16 steps).

**Why gradient boosting:** tabular, mixed-scale, non-linear interaction between wind/humidity/lags and pollutants; robust to missing values; trains in seconds on this dataset; interpretable enough via `feature_importances_`.

### 2.3 Backend Layer (FastAPI)

| Module | Responsibility |
|---|---|
| `backend/aqi.py` | CPCB 2014 sub-index breakpoints for PM2.5, PM10, NO₂, SO₂, CO → overall AQI = max sub-index; category (Good → Severe); `advisory_for(aqi)` returns population-specific guidance |
| `backend/feed.py` | In-memory dataset; `latest_per_station()`, `history(station, hours)`, station metadata |
| `backend/forecast.py` | Artifact loading + 7-day (56-step) recursive forecast; days 3–7 experimental |
| `backend/main.py` | App wiring: REST routes, **WebSocket `/ws`**, static hosting, background broadcast task |

#### REST endpoints

```
GET /api/health        → status, interval, model info
GET /api/stations      → 8 stations with metadata
GET /api/current       → current CAMS grid estimate → CPCB-breakpoint AQI;
                           historical CSV fallback is explicitly marked
GET /api/history       → recent CAMS time series up to 48h; returns no points rather than stale CSV if live history is unavailable; longer ranges use labelled CSV history
GET /api/forecast      → 7-day recursive AQI/PM2.5 forecast (?station, ?steps=56)
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
    forecasts = forecast.rollout_all(horizon=7 days / 56 steps)
    await hub.broadcast({type: "broadcast", ...})  # to all open client sockets
```

### 2.4 Frontend Layer (Static SPA)

```
static/
├── index.html      sections: hero/live AQI · PM reports · predictions ·
│                   health corner (nurse/breathing/remedies/doctors) · learn
├── css/styles.css  mobile-first responsive design, AQI color system
└── js/app.js       ws client + reconnect/backoff · REST fetchers ·
                    Chart.js rendering · station selector · breathing pacer ·
                    countdown timer · filters for doctors/remedies
```

**Realtime client:** opens `ws://<host>/ws`, renders snapshot instantly, updates gauge/tables/charts on each `broadcast`, shows a **countdown to the next 10-minute push**, and reconnects automatically with exponential backoff. REST is the fallback source for history/articles/doctors.

**Sections & data sources:**

| Section | Source |
|---|---|
| Live AQI gauge + pollutant chips | WS `stations` + `/api/current` |
| PM reports (interactive charts) | `/api/history` + Chart.js; 24h uses live CAMS history only (empty/error state if unavailable; no silent stale-CSV substitution); longer windows use historical CSV with explicit source metadata |
| Predicted AQI (7-day recursive outlook) + Diwali panel | WS `forecast` + `/api/forecast` + `/api/diwali` |
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
      └────── renders: live AQI · PM charts · 7-day recursive forecast · Diwali panel ·
                      health nurse · breathing · remedies · doctors · articles
```


## 6. Current conditions and extended forecast (updated)

### Current AQI source

`backend/live.py` calls the Open-Meteo Air Quality API for PM2.5, PM10, CO, NO2 and SO2 at each station's latitude/longitude, plus the Open-Meteo Weather API for current weather covariates. The live response is cached for 15 minutes. The provider also retrieves the previous two days of hourly pollutant and weather values and constructs a recent 3-hourly lag window; the ML forecast uses this instead of stale historical tail values. `backend/main.py` applies `backend/aqi.py` CPCB pollutant breakpoints to the returned concentrations and attaches source metadata.

**Important provenance:** Open-Meteo's air-quality values are CAMS atmospheric model-grid estimates (approximately 11–45 km), not CPCB reference-monitor readings. The dashboard labels them as model estimates. If the upstream API fails, the service falls back to the last historical CSV row and labels it `historical_fallback`; it must not be represented as current measured data.

### 7-day ML forecast

`backend/forecast.py` now defaults to 56 recursive steps at 3-hour intervals (7 days). The latest CAMS estimate replaces the last row in the model's seed history and current weather values replace the historical weather seed. The existing 3-hour AQI and PM2.5 models are recursively applied to each subsequent step.

This extends the original 48-hour rollout but does **not** mean the model was trained or validated as a 7-day direct predictor. The models were trained for next-3-hour and next-24-hour targets. Recursive error can compound, and the current implementation persists the latest weather covariates across the rollout. The API returns `confidence_note` and `experimental_beyond_hours=48`; the frontend displays this limitation. Before using days 3–7 for operational health decisions, add forecast-weather covariates and run rolling-origin backtests by station and horizon.

Open-Meteo's Air Quality API documents a maximum of 7 forecast days; Rasaynam therefore presents a 7-day horizon rather than claiming a supported 10-day air-quality outlook.

References:
- Open-Meteo Air Quality API: https://open-meteo.com/en/docs/air-quality-api
- Open-Meteo Weather API: https://open-meteo.com/en/docs

## Regional AQI map

The frontend includes a Leaflet-based regional map for the eight configured sample locations in NCR, Punjab, and Haryana. It consumes `GET /api/map`, which returns the same current station payloads used by the dashboard plus 56 forecast points per station. The map renders AQI-colored markers, pollutant-detail popups, an optional heat layer, and optional illustrative alert halos for AQI values above 200. A time selector samples each station forecast at +24h, +48h, Day 3, Day 5, and Day 7.

**Spatial interpretation constraint:** the eight coordinates are sparse point samples. The heat layer is a smoothed visual interpolation, not a measured continuous pollution field. Alert halos are for visual emphasis only, not validated danger-zone boundaries. Current values are CAMS model-grid estimates where available (not CPCB ground-monitor readings); historical CSV fallback is source-labelled. Forecasts after 48 hours remain experimental recursive ML outputs. The frontend uses Leaflet and Leaflet.heat from CDNs and OpenStreetMap tiles with attribution.

### Map API

`GET /api/map`

Returns `region`, `data_as_of`, `stations[]`, `forecast{station_id:{base_time,step_hours,confidence_note,points[]}}`, and `spatial_note`. Each station includes its configured latitude/longitude, AQI category/color, timestamp, source, and pollutant readings. Forecast `points` are spaced at three-hour intervals; the client chooses the nearest forecast point for the selected map time.
