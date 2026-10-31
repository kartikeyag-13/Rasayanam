# VayuSathi — AI-Powered Neighborhood Air Quality & Health Platform

**Predicting neighborhood-level air pollution before, during, and after Diwali and telling you exactly what to do about it.**

VayuSathi is an all-in-one platform that combines **historical air-quality data**, **weather conditions**, **traffic/cyclical indicators**, and **ML forecasting** to predict air pollution at the neighborhood (monitoring-station) level across the NCR–Punjab–Haryana region. Around it wraps a complete **health companion**: live AQI, interactive pollutant reports, respiratory-health education, guided breathing exercises, herbal teas & home remedies, and a directory of nearby doctors and ENT specialists.

---

## Problem Statement

Air pollution in Delhi-NCR, Punjab and Haryana spikes dramatically around Diwali due to firecrackers, crop-residue burning, stagnant winter weather, and traffic emissions. Citizens need **one place** that provides:

1. **Present info** — current AQI and pollutant levels for their neighborhood.
2. **Predicted info** — ML-based forecasts of pollution *before, during, and after* Diwali.
3. **Concerns** — what high AQI actually does to the body (authoritative articles).
4. **Solutions** — a "personal nurse" with breathing exercises, herbal teas, home remedies, and local doctor/ENT specialist information.

---

## Features

### 1. Live AQI Dashboard (Backend-pushed over WebSocket)
- CPCB-standard **AQI computation** (PM2.5, PM10, NO₂, SO₂, CO sub-indices → overall AQI + category).
- Per-neighborhood selector across **8 monitoring stations**: New Delhi (Safdarjung, Anand Vihar), Gurugram, Noida, Ambala, Hisar, Amritsar, Ludhiana.
- Auto-updates: the **WebSocket server broadcasts the latest reading + fresh forecast every 10 minutes** (configurable), with an on-connect snapshot and a countdown to the next push.

### 2. Interactive PM Reports
- Interactive charts of **PM2.5 / PM10 / NO₂ / SO₂ / CO** trends (24h, 7-day, 30-day, full-history views).
- Station-to-station comparison, pollutant breakdown, and Diwali-window highlighting.

### 3. Predictions (ML)
- **Gradient-boosted forecasting models** (scikit-learn `HistGradientBoostingRegressor`) trained on 5+ years of weather + pollutant lag features.
- **48-hour ahead forecast** of PM2.5 and AQI per station, refreshed on every push.
- **Diwali insight panel**: historical before/during/after-Diwali AQI climatology computed from the dataset.

### 4. Health Corner — "Your Personal Nurse"
- **Dynamic health advisory** that changes with the live AQI category (what to do right now).
- **Guided breathing exercises** — box breathing, 4-7-8, and diaphragmatic breathing with an interactive animated pacer.
- **Herbal teas & home remedies** for irritation, cough, congestion, throat dryness and eye discomfort (turmeric milk, tulsi-ginger tea, mulethi, steam inhalation, ...).
- **Doctor & ENT specialist directory** for the nearby area — searchable filter by city and specialty.

### 5. Learn Section
- Curated references to authoritative articles (WHO, CPCB, American Lung Association, NIH/EPA, etc.) on how high AQI causes respiratory and cardiovascular issues.

---

## 🗂️ Dataset

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
| `/api/current` | GET | Latest reading + computed AQI + advisory for all/one station |
| `/api/history?station=&hours=` | GET | Historical time series for charts |
| `/api/forecast?station=&hours=48` | GET | ML forecast (AQI, PM2.5) |
| `/api/diwali` | GET | Historical before/during/after-Diwali climatology |
| `/api/articles` | GET | Curated respiratory-health article references |
| `/api/doctors` | GET | Doctor / ENT specialist directory |
| `/api/remedies` | GET | Herbal teas & home remedies |


---

## How prediction works

1. **Feature engineering** — per station: pollutant lags (1 step, 24 h), weather lags, rolling means, hour sin/cos, month, day-of-year, wind components, precipitation, humidity, plus **Diwali-proximity flags** (days to Diwali, firecracker-season window).
2. **Targets** — `pm25_ugm3` and CPCB-computed `AQI` at the next time step (3 h ahead), plus a direct 24 h-ahead head.
3. **Model** — `HistGradientBoostingRegressor` (nonlinear, robust to missing values), one model per target, trained on **time-ordered** train/test splits (no leakage).
4. **Serving** — the backend iteratively rolls the model forward to produce a **48-hour trajectory**, which is attached to every WebSocket push and exposed at `/api/forecast`.
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

Example — broadcast every 2 minutes for a demo:

```bash
WS_BROADCAST_INTERVAL=120 uvicorn backend.main:app --port 8000
```

---
