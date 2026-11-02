# Rasayanam — AI-Powered Neighborhood Air Quality & Health Platform

**Predicting neighborhood-level air pollution before, during, and after Diwali and telling you exactly what to do about it.**

Rasayanam is an all-in-one platform that combines **historical air-quality data**, **weather conditions**, **traffic/cyclical indicators**, and **ML forecasting** to predict air pollution at the neighborhood (monitoring-station) level across the NCR–Punjab–Haryana region. Around it wraps a complete **health companion**: live AQI, interactive pollutant reports, respiratory-health education, guided breathing exercises, herbal teas & home remedies, and a directory of nearby doctors and ENT specialists.

---

## Problem Statement

Air pollution in Delhi-NCR, Punjab and Haryana spikes dramatically around Diwali due to firecrackers, crop-residue burning, stagnant winter weather, and traffic emissions. Citizens need **one place** that provides:

1. **Present info** — current AQI and pollutant levels for their neighborhood.
2. **Predicted info** — ML-based forecasts of pollution *before, during, and after* Diwali.
3. **Concerns** — what high AQI actually does to the body (authoritative articles).
4. **Solutions** — a "personal nurse" with breathing exercises, herbal teas, home remedies, and local doctor/ENT specialist information.

---

## Features

### 1. Current AQI Dashboard (CAMS model-grid estimate + WebSocket)
- Current pollutant concentrations are fetched from the Open-Meteo Air Quality API (CAMS) and converted to a **CPCB-breakpoint AQI estimate** using this project's `backend/aqi.py`.
- The source is a gridded atmospheric-composition model estimate (roughly 11–45 km), **not a CPCB reference-monitor measurement**. The UI labels this provenance explicitly.
- The live card applies CPCB concentration breakpoints to trailing CAMS model averages (24 hours for most species, 8 hours for CO), only when the available hourly coverage meets minimum thresholds. It remains a model estimate and is not expected to match CPCB's validated monitoring dashboard or other AQI providers.
- The provider also retrieves recent hourly history and samples it into a 3-hour lag window so the ML model does not seed its current forecast from the stale final 2025 CSV row.
- If current provider data is unavailable, `/api/current` sets `aqi` to `null`, reports the source status and timestamp, and nests the CSV value under `historical_observation`. The dashboard does not render that historical AQI as current.
- Per-neighborhood selector across 8 stations. A process-local cache refreshes hourly by default; a batch request covers all configured coordinates and a lock prevents concurrent cache stampedes. WebSocket broadcasts default to every 10 minutes.
- **CPCB-breakpoint AQI estimate** uses the highest valid sub-index only when at least three supported pollutants are valid, including PM2.5 or PM10. CAMS estimates use trailing 24-hour averages (8-hour CO) with minimum coverage, but lack CPCB monitor validation and the full pollutant set.
- Per-neighborhood selector across **8 monitoring stations**: New Delhi (Safdarjung, Anand Vihar), Gurugram, Noida, Ambala, Hisar, Amritsar, Ludhiana.
- Auto-updates: the **WebSocket server broadcasts the latest reading + available forecast every 10 minutes** (configurable), with an on-connect snapshot.

### 2. Interactive PM Reports
- Interactive charts of **PM2.5 / PM10 / NO₂ / SO₂ / CO** trends. The 24-hour range uses recent CAMS model history and will show an explicit unavailable state if that feed cannot provide recent points; it will never silently substitute the old CSV. Longer ranges use the dated historical project CSV and are labelled as historical, not live.
- Station-to-station comparison, pollutant breakdown, and Diwali-window highlighting.

### 3. Predictions (ML)
- **Gradient-boosted forecasting models** (scikit-learn `HistGradientBoostingRegressor`) trained on 5+ years of weather + pollutant lag features.
- **7-day CAMS air-quality outlook** per station, built from hourly forecast pollutant concentrations and converted to AQI using CPCB breakpoints. The local ML models remain available for short-horizon experimentation.
- **Diwali insight panel**: historical before/during/after-Diwali AQI climatology computed from the dataset.

### 4. Health Corner — "Your Personal Nurse"
- **Dynamic health advisory** that changes with the live AQI category (what to do right now).
- **Guided breathing exercises** — box breathing, 4-7-8, and diaphragmatic breathing with an interactive animated pacer.
- **Herbal teas & home remedies** for irritation, cough, congestion, throat dryness and eye discomfort (turmeric milk, tulsi-ginger tea, mulethi, steam inhalation, ...).
- **Doctor & ENT specialist directory** for the nearby area — searchable filter by city and specialty.

### 5. Learn Section
- Curated references to authoritative articles (WHO, CPCB, American Lung Association, NIH/EPA, etc.) on how high AQI causes respiratory and cardiovascular issues.

---

## Dataset

`ncr_punjab_haryana_weather_aqi_2020_2025.csv` — **46,848 rows**, 3-hourly observations from **2020-09-01 → 2025-12-31** across **8 stations / 4 regions**.

| Column group | Fields |
|---|---|
| Identity | `timestamp, state, city, station_id, spatial_level, latitude, longitude` |
| Weather | `temp_c, relative_humidity_pct, dew_point_c, surface_pressure_hpa, precipitation_mm, wind_speed_kmh, wind_direction_deg, u_wind_10m, v_wind_10m` |
| Pollutants | `pm25_ugm3, pm10_ugm3, no2_ugm3, so2_ugm3, co_mgm3, aqi_sub_index` |
| Model features | `temp_lag_1h, temp_lag_24h, pm25_lag_1h, pm25_lag_24h, sin_hour, cos_hour` |

Stations: `DL_SAFDARJUNG`, `DL_ANAND_VIHAR`, `HR_GURUGRAM_SEC51`, `UP_NOIDA_SEC62`, `HR_AMBALA_AFS`, `HR_HISAR_HAU`, `PB_AMRITSAR_GT`, `PB_LUDHIANA_PAU`.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| ML training | Python, pandas, NumPy, scikit-learn (HistGradientBoosting), joblib |
| Backend | FastAPI + Uvicorn (async), REST API + **native WebSocket server** |
| Prediction service | Trained model artifacts loaded at boot, forecast endpoint + push payload |
| Frontend | Vanilla HTML/CSS/JS single-page app, Chart.js interactive charts |
| Realtime | WebSocket pushes every **10 minutes** (env-configurable) with a snapshot on connect |

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full system design.

---

##  API Overview

| Endpoint | Type | Description |
|---|---|---|
| `/ws` | WebSocket | Snapshot and periodic updates; connection status and `data_status` are separate |
| `/api/health` | GET | Service status |
| `/api/stations` | GET | Station metadata (id, city, lat/lon) |
| `/api/current?station=` | GET | Current CAMS estimate and freshness, or `aqi: null` plus explicit source status and nested historical context |
| `/api/history?station=&hours=` | GET | Recent CAMS history for ranges up to 48h; if unavailable, returns an empty series with an explanation rather than stale CSV points. Longer ranges use the historical CSV. Response includes `source` and `source_note`. |
| `/api/forecast?station=&steps=56` | GET | CAMS AQI forecast for returned timestamps; recent-seed local fallback capped at 48 hours, otherwise explicitly unavailable |
| `/api/map` | GET | All station payloads and per-station forecast; unavailable stations remain represented with null AQI |
| `/api/diwali` | GET | Historical before/during/after-Diwali climatology |
| `/api/articles` | GET | Curated respiratory-health article references |
| `/api/doctors` | GET | Doctor / ENT specialist directory |
| `/api/remedies` | GET | Herbal teas & home remedies |


---

## How prediction works

1. **Feature engineering** — per station: pollutant lags (1 step, 24 h), rolling means, current weather, hour/month/day-of-year cycles, wind components, precipitation, humidity, plus **Diwali-proximity flags**.
2. **Targets** — `pm25_ugm3` and CPCB-computed `AQI` at the next time step (3 h ahead), plus a direct 24 h-ahead head.
3. **Model** — `HistGradientBoostingRegressor` (nonlinear, robust to missing values), one model per target, trained on **time-ordered** train/test splits (no leakage).
4. **Serving** — the public forecast prefers actual timestamps and pollutant values from Open-Meteo's CAMS hourly forecast. If that forecast is unavailable but a recent live observation exists, the local recursive model may provide an experimental forecast capped at 48 hours. It holds weather and unmodeled pollutant species constant, so convergence and accumulated error are known limitations. If no recent live seed exists, forecast values are unavailable; the 2025 historical CSV tail is never treated as a 2026 forecast seed.
5. **Evaluation** — MAE/RMSE/R² reported in `ml/artifacts/metrics.json` after training.

---
## Quick Start

```bash
# 1. Create environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Train the prediction models (writes ml/artifacts/)
python -m ml.train

# 3. Start the backend + WebSocket server + website
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** 

### Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `WS_BROADCAST_INTERVAL` | `600` (10 min) | Seconds between WebSocket broadcasts |
| `DATA_PATH` | `ncr_punjab_haryana_weather_aqi_2020_2025.csv` | Dataset location |
| `ARTIFACTS_DIR` | `ml/artifacts` | Trained-model directory |
| `LIVE_DATA_CACHE_SECONDS` | `3600` | Fresh cache lifetime for batched provider responses |
| `LIVE_DATA_MAX_STALE_SECONDS` | `21600` | Maximum stale-cache age eligible for display, always labelled as cached |
| `LIVE_DATA_TIMEOUT_SECONDS` | `8` | Timeout per upstream request |
| `LIVE_DATA_MAX_RETRIES` | `2` | Bounded retry count for transient failures; 429 responses use `Retry-After` and are not immediately retried |
| `LIVE_DATA_MAX_OBSERVATION_AGE_SECONDS` | `43200` | Maximum observation timestamp age treated as current (12 hours) |

Example — broadcast every 2 minutes for a demo:

```bash
WS_BROADCAST_INTERVAL=120 uvicorn backend.main:app --port 8000
```

---

## Current data source, provenance & limitations

Rasayanam queries the public [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) for current PM2.5, PM10, CO, NO2 and SO2 concentrations and forecast/history at configured coordinates. It queries the [Open-Meteo Weather API](https://open-meteo.com/en/docs) for matching weather data. Both documented APIs accept comma-separated coordinate lists; the service sends at most one batched request per endpoint for all eight stations during a cold refresh. Successful raw endpoint responses and per-station bundles are reused. The API values are atmospheric model data, not regulatory ground-monitor observations.

`backend/aqi.py` interpolates the project's CPCB concentration breakpoints, ignores null, negative and non-finite inputs, and reports the maximum sub-index only when at least three supported species are valid and PM2.5 or PM10 is among them. `backend/live.py` averages hourly CAMS model values over trailing 24-hour windows (8 hours for CO) and requires at least 16 (or 6 for CO) hourly values. This improves averaging-period alignment but cannot provide CPCB monitor validation or the full pollutant set. Rasayanam labels its value a **CAMS model estimate using CPCB breakpoints**, never an official CPCB station AQI. See the [CPCB National AQI report](https://cpcb.nic.in/displaypdf.php?id=bWFudWFsLW1vbml0b3JpbmcvQVFJX05BTVBfUmVwX1NlcHRlbWJlcjIwMTYucGRm).

Open-Meteo's Air Quality API documents a maximum of **7 forecast days**. Rasayanam can display up to that provider horizon using hourly CAMS pollutant forecast samples converted to CPCB-breakpoint AQI every three hours. It is a gridded atmospheric-model forecast, not a CPCB ground-monitor forecast. If CAMS is unavailable, a local ML fallback is only returned with a recent live seed and is capped at 48 hours. If no recent seed is available, the forecast is unavailable; later days are not fabricated.

When the provider fails, `/api/current` returns `current_available: false`, `aqi: null`, a status such as `historical_fallback`, and the actual CSV timestamp/AQI in `historical_observation`. The frontend shows the historical timestamp and an unavailable message but never displays that old AQI as today's reading. A previous provider cache may be served for up to six hours after its refresh interval, with `cache_status: stale_cache` and its cache age; it is rejected as current if the observation timestamp is older than the configured 12-hour limit.

### Request management and deployment

`backend/live.py` serializes refreshes within a process, so concurrent REST and WebSocket requests reuse one in-flight batch. Current/history/forecast/map endpoints share this provider. A 429 response is not retried; `Retry-After` is honored and later requests are suppressed until that window expires. Transient network and server errors receive at most two retries with exponential backoff and jitter. Timeouts, malformed provider data, and partial station data are logged and handled as unavailable data. The in-memory cache is per Render process and is lost on restart; correctness does not depend on persistence, and multiple Render instances maintain independent bounded caches.

`render.yaml` binds Uvicorn to `0.0.0.0:$PORT`, installs `requirements.txt`, and uses `/api/health` as the health check. Static assets and model/data paths resolve relative to the checked-out project. Render sleep/restarts clear the process cache; the next request makes a new bounded batch.

Run backend tests and JavaScript syntax validation locally:

```bash
python -m unittest discover -s tests -v
python -m py_compile backend/*.py ml/*.py
python -c "from pathlib import Path; s=Path('static/index.html').read_text(); a=s.index('<script>')+8; b=s.index('</script>',a); Path('/tmp/rasayanam-inline.js').write_text(s[a:b])"
node --check /tmp/rasayanam-inline.js
```

The five-section navigator is placed in normal document flow below the hero rather than floating over dashboard cards. At narrow widths its labels collapse while retaining named 42px touch targets. The AQI value is centered over the ring and the CAMS source label sits beneath it. Regression tests also guard against literal escaped newline text in the HTML. Browser viewport rendering still needs a browser-capable environment; this workspace has no browser automation runtime.

**Attribution:** Air-quality inputs and estimates are provided by [Open-Meteo](https://open-meteo.com/) using CAMS data. See the [Air Quality API documentation](https://open-meteo.com/en/docs/air-quality-api) and its data-source notes.

## Regional AQI intelligence map

The dashboard includes an interactive Leaflet map for the eight configured locations across NCR, Punjab and Haryana. It combines:

- AQI-colored station markers with clickable pollutant details and timestamps.
- A smoothed heat layer to help compare the sampled AQI values spatially.
- Illustrative alert halos for sampled locations above AQI 200; these are visual emphasis only, not measured danger-zone boundaries.
- A time selector for current conditions and available model forecasts at +24h, +48h, Day 3, Day 5 and Day 7; unavailable horizon options are disabled.
- OpenStreetMap basemap tiles with attribution.

The map obtains data from `GET /api/map`. The API returns current station payloads and each station's available 3-hour forecast points. The timeline is limited to the returned forecast horizon; unavailable future station values are omitted. The map is regional and station-sampled: the heat layer interpolates between eight sparse coordinates. It must not be interpreted as street-level pollution, a continuous measured surface, or an official regulatory map. Current pollutant values are Open-Meteo CAMS model-grid estimates where available; fallback records are labelled historical CSV.

The map loads Leaflet and Leaflet.heat from public CDNs and OpenStreetMap standard tiles. Internet access is therefore required for map assets and tiles. Production deployments should review the OpenStreetMap tile usage policy and use an appropriate tile provider if traffic grows.


## Forecast methodology update

The public outlook uses hourly pollutant concentrations from the Open-Meteo Air Quality API (CAMS), sampled at available three-hour timestamps. Rasayanam calculates CPCB breakpoint sub-indices and overall AQI independently at each timestamp, and includes weather values where matching hourly data is available. This is a gridded atmospheric model forecast, not a CPCB monitor forecast. The local HistGradientBoosting models remain for short-horizon experiments and evaluation; fallback is capped at 48 hours and requires a recent live seed. If neither source can provide a defensible forecast, the API returns an empty, explicitly unavailable forecast.

The earlier flat severe local forecasts are consistent with the local recursive rollout: after each 3-hour prediction it fed predicted AQI and PM2.5 back into the model, repeated PM10/NO₂/SO₂/CO from the previous step, and held all weather features constant. A replay from a historical AQI-500 episode (2020-11-01) produced six of eight 56-step traces within 2–9 AQI points across the entire horizon; the other two spanned 16 and 19 points. This illustrates how a high seed and persistence assumptions can trap a tree regressor near a narrow severe range. The live seven-day forecast therefore comes from CAMS pollutant forecast timestamps; the local model is only a labelled ≤48-hour experiment when it has a fresh live seed.

## Opening experience and frontend

The home page uses the supplied `static/assets/rasayanam-intro.mp4` as a muted, inline opening video. The video’s existing Rasayanam wordmark was extracted as `static/assets/rasayanam-wordmark.png`; that single image element fades in over the matching final video frame, then animates into the top-left header position. Visitors can skip the intro; it is shown once per browser session and is bypassed for reduced-motion users. If autoplay or video loading fails, the site proceeds to its regular interface. The video uses cover on landscape screens and contain on portrait screens to keep the embedded logo in frame. The environmental narrative progresses through atmosphere, pollution, intelligence, forecasting and protection; an Intersection Observer rail tracks the active chapter and shifts the ambient accent. The frontend remains a no-build static page in `static/index.html`; it uses Intersection Observer for scroll reveals, Chart.js for pollutant history, and Leaflet for the regional map.

## Remedy recipe pages

The Health Corner recipe cards link to `/remedies/{id}`. Each detail page is populated by `GET /api/remedies/{id}` and includes ingredients, preparation, traditional Ayurvedic context, evidence notes, safety cautions and sources where relevant. Ayurvedic framing is described as traditional context, not clinical proof. Remedies are not presented as protection from pollution or treatment for lung injury.
