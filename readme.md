# Rasayanam — AI-Powered Neighborhood Air Quality & Health Advisory System

**Predicting neighborhood-level air pollution before, during, and after Diwali and telling you exactly what to do about it.**

Rasayanam is an all-in-one platform that combines **historical air-quality data**, **weather conditions**, **traffic/cyclical indicators**, and **ML forecasting** to predict air pollution at the neighborhood (monitoring-station) level across the NCR–Punjab–Haryana region. Around it wraps a complete **health companion**: live AQI, interactive pollutant reports, respiratory-health education, guided breathing exercises, herbal teas & home remedies, and a directory of nearby doctors and ENT specialists.

---

## Problem Statement

Air pollution in Delhi-NCR, Punjab, and Haryana spikes dramatically around Diwali due to firecrackers, crop-residue burning, stagnant winter weather, and traffic emissions. Citizens need **one place** that provides:

1. **Present info** — current AQI and pollutant levels for their neighborhood.
2. **Predicted info** — ML-based forecasts of pollution *before, during, and after* Diwali.
3. **Concerns** — what high AQI actually does to the body (authoritative articles).
4. **Solutions** — a "personal nurse" with breathing exercises, herbal teas, home remedies, and local doctor/ENT specialist information.

---

## Features

### 1. Current AQI Dashboard (CAMS model-grid estimate + WebSocket)
- Current pollutant concentrations are fetched per station from the Open-Meteo Air Quality API (CAMS) and converted to a **CPCB-style AQI** using this project's `backend/aqi.py` breakpoints.
- The source is a gridded atmospheric-composition model estimate (roughly 11–45 km), **not a CPCB reference-monitor measurement**. The UI labels this provenance explicitly.
- The provider also retrieves recent hourly history and samples it into a 3-hour lag window so the ML model does not seed its current forecast from the stale final 2025 CSV row.
- If the upstream provider is unavailable, Rasaynam falls back to the latest CSV observation and labels it as historical; it never labels that fallback as live.
- Per-neighborhood selector across 8 stations. Current estimates are cached for 15 minutes; WebSocket broadcasts default to every 10 minutes.
- CPCB-standard **AQI computation** (PM2.5, PM10, NO₂, SO₂, CO sub-indices → overall AQI + category).
- Per-neighborhood selector across **8 monitoring stations**: New Delhi (Safdarjung, Anand Vihar), Gurugram, Noida, Ambala, Hisar, Amritsar, Ludhiana.
- Auto-updates: the **WebSocket server broadcasts the latest reading + fresh forecast every 10 minutes** (configurable), with an on-connect snapshot and a countdown to the next push.

### 2. Interactive PM Reports
- Interactive charts of **PM2.5 / PM10 / NO₂ / SO₂ / CO** trends. The 24-hour range uses recent CAMS model history and will show an explicit unavailable state if that feed cannot provide recent points; it will never silently substitute the old CSV. Longer ranges use the dated historical project CSV and are labelled as historical, not live.
- Station-to-station comparison, pollutant breakdown, and Diwali-window highlighting.

### 3. Predictions (ML)
- **Gradient-boosted forecasting models** (scikit-learn `HistGradientBoostingRegressor`) trained on 5+ years of weather + pollutant lag features.
- **7-day recursive ML outlook** of PM2.5 and AQI per station, refreshed on the configured push cycle; days beyond 48 hours are experimental.
- **Diwali insight panel**: historical before/during/after-Diwali AQI climatology computed from the dataset.

### 4. Health Corner — "Your Personal Nurse"
- **Dynamic health advisory** that changes with the live AQI category (what to do right now).
- **Guided breathing exercises** — box breathing, 4-7-8, and diaphragmatic breathing with an interactive animated pacer.
- **Herbal teas & home remedies** for irritation, cough, congestion, throat dryness, and eye discomfort (turmeric milk, tulsi-ginger tea, mulethi, steam inhalation, ...).
- **Doctor & ENT specialist directory** for the nearby area — searchable by city and specialty.

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
| Realtime | WebSocket pushes every **10 minutes** (env-configurable), live countdown UI |

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for the full system design.

---

##  API Overview

| Endpoint | Type | Description |
|---|---|---|
| `/ws` | WebSocket | Live push: latest readings + AQI + forecast, every 10 min |
| `/api/health` | GET | Service status |
| `/api/stations` | GET | Station metadata (id, city, lat/lon) |
| `/api/current` | GET | Current CAMS gridded estimate converted to CPCB-style AQI; historical CSV fallback is explicitly labelled |
| `/api/history?station=&hours=` | GET | Recent CAMS history for ranges up to 48h; if unavailable, returns an empty series with an explanation rather than stale CSV points. Longer ranges use the historical CSV. Response includes `source` and `source_note`. |
| `/api/forecast?station=&steps=56` | GET | 7-day recursive ML forecast (56 × 3-hour AQI/PM2.5 points); max 56 steps |
| `/api/diwali` | GET | Historical before/during/after-Diwali climatology |
| `/api/articles` | GET | Curated respiratory-health article references |
| `/api/doctors` | GET | Doctor / ENT specialist directory |
| `/api/remedies` | GET | Herbal teas & home remedies |


---

## How prediction works

1. **Feature engineering** — per station: pollutant lags (1 step, 24 h), weather lags, rolling means, hour sin/cos, month, day-of-year, wind components, precipitation, humidity, plus **Diwali-proximity flags** (days to Diwali, firecracker-season window).
2. **Targets** — `pm25_ugm3` and CPCB-computed `AQI` at the next time step (3 h ahead), plus a direct 24 h-ahead head.
3. **Model** — `HistGradientBoostingRegressor` (nonlinear, robust to missing values), one model per target, trained on **time-ordered** train/test splits (no leakage).
4. **Serving** — the backend starts from the latest current CAMS estimate when available, otherwise the labelled historical fallback, and iteratively rolls the 3-hour models forward for **7 days (56 steps)**. This is an experimental recursive horizon: forecast error can accumulate and the later days are not separately validated.
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
| `LIVE_DATA_CACHE_SECONDS` | `900` | Intended cache period for upstream current conditions (15 min; currently set in `backend/live.py`) |

Example — broadcast every 2 minutes for a demo:

```bash
WS_BROADCAST_INTERVAL=120 uvicorn backend.main:app --port 8000
```

---

## Current data source, provenance & limitations

Rasaynam queries the public [Open-Meteo Air Quality API](https://open-meteo.com/en/docs/air-quality-api) for current PM2.5, PM10, CO, NO2 and SO2 concentrations at each station coordinate. It queries the [Open-Meteo Weather API](https://open-meteo.com/en/docs) for current weather covariates. The API's air-quality current conditions are based on atmospheric model data, not a regulatory ground monitor. Rasaynam computes its displayed index using the project's CPCB breakpoint implementation; this should be described as a **CPCB-breakpoint AQI estimate from CAMS model-grid concentrations**, not an official CPCB station AQI.

Open-Meteo's Air Quality API currently documents a maximum of **7 forecast days**. Rasaynam therefore targets a 7-day forecast, not 10 days. The 7-day ML trajectory recursively applies models trained on 3-hour and 24-hour targets; beyond 48 hours, it is experimental, and error may accumulate. The present rollout persists the latest weather values, so weather-forecast feature injection and multi-horizon backtesting are required before presenting days 3–7 as validated predictions.

If Open-Meteo is unreachable, `/api/current` falls back to the last row of the 2020–2025 CSV and marks the response `historical_fallback`. Do not present this fallback as today's measured AQI.

**Attribution:** Air-quality inputs and estimates are provided by [Open-Meteo](https://open-meteo.com/) using CAMS data. See the [Air Quality API documentation](https://open-meteo.com/en/docs/air-quality-api) and its data-source notes.

## Regional AQI intelligence map

The dashboard includes an interactive Leaflet map for the eight configured locations across NCR, Punjab and Haryana. It combines:

- AQI-colored station markers with clickable pollutant details and timestamps.
- A smoothed heat layer to help compare the sampled AQI values spatially.
- Illustrative alert halos for sampled locations above AQI 200; these are visual emphasis only, not measured danger-zone boundaries.
- A time selector for current conditions and model forecasts at +24h, +48h, Day 3, Day 5 and Day 7.
- OpenStreetMap basemap tiles with attribution.

The map obtains data from `GET /api/map`. The API returns the current station payloads and each station's 56-point, 3-hour-step forecast. The map is regional and station-sampled: the heat layer interpolates between eight sparse coordinates. It must not be interpreted as street-level pollution, a continuous measured surface, or an official regulatory map. Current pollutant values are Open-Meteo CAMS model-grid estimates where available; fallback records are labelled historical CSV. The seven-day forecast is experimental beyond 48 hours.

The map loads Leaflet and Leaflet.heat from public CDNs and OpenStreetMap standard tiles. Internet access is therefore required for map assets and tiles. Production deployments should review the OpenStreetMap tile usage policy and use an appropriate tile provider if traffic grows.
