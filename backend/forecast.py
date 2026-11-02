"""ML forecast service — loads trained artifacts and rolls them forward.

Recursive multi-step forecasting: predict step t+1 from features at t, feed the
prediction back into the pollutant history, and repeat for 48 h (16 steps of
3 h). Weather is held at its last observed value (persistence assumption);
time and Diwali features come from the target timestamp itself.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from backend.aqi import classify, overall_aqi
from ml.features import (
    FEATURE_COLUMNS,
    HISTORY_KEYS,
    WEATHER_FEATURES,
    make_rollout_row,
)

logger = logging.getLogger("rasayanam.forecast")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS = ROOT / "ml" / "artifacts"
STEP = pd.Timedelta(hours=3)
DEFAULT_STEPS = 56  # 7 days; recursive horizon is experimental beyond 48h
CACHE_TTL = 300.0  # seconds


class ForecastService:
    def __init__(self, feed, artifacts_dir: str | Path | None = None) -> None:
        self.feed = feed
        self.dir = Path(artifacts_dir or os.environ.get("ARTIFACTS_DIR") or DEFAULT_ARTIFACTS)
        self.models: dict = joblib.load(self.dir / "model.joblib")
        self.spec = json.loads((self.dir / "feature_spec.json").read_text())
        try:
            self.metrics = json.loads((self.dir / "metrics.json").read_text())
        except FileNotFoundError:
            self.metrics = {}
        missing = [f for f in FEATURE_COLUMNS if f not in self.spec["features"]]
        if missing:
            raise RuntimeError(f"artifact feature spec mismatch, missing: {missing}")
        self._cache: dict[tuple, tuple[float, dict]] = {}
        logger.info(
            "loaded models from %s (trained %s)",
            self.dir,
            self.spec.get("trained_at", "?"),
        )

    # ---------------------------------------------------------------- helpers --
    def _histories(self, sdf: pd.DataFrame) -> dict[str, list[float]]:
        tail = sdf.tail(24)
        return {k: [float(v) for v in tail[k].tolist()] for k in HISTORY_KEYS}

    def _latest_row(self, station_id: str) -> tuple[pd.Timestamp, dict, dict]:
        sdf = self.feed.station_df(station_id)
        last = sdf.iloc[-1]
        hist = self._histories(sdf)
        weather = {w: float(last[w]) for w in WEATHER_FEATURES}
        return pd.Timestamp(last["timestamp"]), hist, weather

    # ------------------------------------------------------------------ API ---
    @property
    def info(self) -> dict:
        return {
            "model_type": self.spec.get("model_type"),
            "default_forecast_steps": DEFAULT_STEPS,
            "default_forecast_days": DEFAULT_STEPS * 3 / 24,
            "trained_at": self.spec.get("trained_at"),
            "train_rows": self.spec.get("train_rows"),
            "test_rows": self.spec.get("test_rows"),
            "holdout": self.spec.get("train_until"),
            "metrics": self.metrics,
        }

    def forecast_station(
        self, station_id: str, steps: int = DEFAULT_STEPS,
        live_record: dict | None = None,
    ) -> dict:
        if not live_record or not live_record.get("timestamp"):
            raise ValueError("local ML forecast requires a current live observation as its seed")
        seed_time = pd.Timestamp(live_record["timestamp"])
        if seed_time.tzinfo is None:
            seed_time = seed_time.tz_localize("Asia/Kolkata")
        else:
            seed_time = seed_time.tz_convert("Asia/Kolkata")
        age = (pd.Timestamp.now(tz="Asia/Kolkata") - seed_time).total_seconds()
        if age < -3600 or age > 6 * 3600:
            raise ValueError("local ML forecast seed is stale or future-dated; a recent live observation is required")
        key = (station_id, steps, (live_record or {}).get('timestamp', 'historical'))
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL:
            return cached[1]

        t0, hist, weather = self._latest_row(station_id)
        if live_record:
            live_ts = pd.Timestamp(live_record["timestamp"])
            if live_ts.tzinfo is not None:
                live_ts = live_ts.tz_convert("Asia/Kolkata").tz_localize(None)
            t0 = live_ts
            # Seed lag features with the provider's recent 3-hourly history when available.
            live_history = live_record.get("_history") or []
            if len(live_history) >= 8:
                field_map = {"pm25_ugm3": "pm25", "pm10_ugm3": "pm10",
                             "no2_ugm3": "no2", "so2_ugm3": "so2",
                             "co_mgm3": "co", "aqi": "aqi"}
                for key, field in field_map.items():
                    values = [row.get(field) for row in live_history if row.get(field) is not None]
                    if values:
                        hist[key] = [float(v) for v in values][-24:]
            else:
                for key, field in (("pm25_ugm3", "pm25"), ("pm10_ugm3", "pm10"),
                                   ("no2_ugm3", "no2"), ("so2_ugm3", "so2"),
                                   ("co_mgm3", "co"), ("aqi", "aqi")):
                    value = live_record.get(field)
                    if value is not None:
                        hist[key][-1] = float(value)
            for key in WEATHER_FEATURES:
                if live_record.get(key) is not None:
                    weather[key] = float(live_record[key])
        pm25_model = self.models["pm25_3h"]
        aqi_model = self.models["aqi_3h"]

        seed_hist = {key: list(values) for key, values in hist.items()}
        points: list[dict] = []
        t = t0
        for _ in range(steps):
            row = make_rollout_row(t, hist, weather)
            pm25_hat = max(float(pm25_model.predict(row)[0]), 0.0)
            aqi_hat = float(np.clip(aqi_model.predict(row)[0], 0.0, 500.0))
            t = t + STEP
            points.append(
                {
                    "ts": t.isoformat(),
                    "aqi": int(round(aqi_hat)),
                    "pm25": round(pm25_hat, 1),
                }
            )
            # feed predictions back into the history for the next step
            hist["pm25_ugm3"].append(pm25_hat)
            hist["aqi"].append(aqi_hat)
            for k in ("pm10_ugm3", "no2_ugm3", "so2_ugm3", "co_mgm3"):
                hist[k].append(hist[k][-1])  # persistence for un-modelled species
            for k in HISTORY_KEYS:
                hist[k] = hist[k][-24:]

        # direct next-day (24 h) estimate from the 24 h models, built from the
        # *observed* history at the latest timestamp
        row_now = make_rollout_row(t0, seed_hist, weather)
        next_day = {
            "pm25": round(max(float(self.models["pm25_24h"].predict(row_now)[0]), 0.0), 1),
            "aqi": int(
                round(float(np.clip(self.models["aqi_24h"].predict(row_now)[0], 0.0, 500.0)))
            ),
            "from": t0.isoformat(),
        }

        peak = max(points, key=lambda p: p["aqi"])
        payload = {
            "station_id": station_id,
            "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
            "horizon_hours": steps * 3,
            "horizon_days": round(steps * 3 / 24, 1),
            "forecast_type": "recursive_ml",
            "experimental_beyond_hours": 48,
            "confidence_note": "Recursive extrapolation beyond 48 hours is experimental and has not been separately validated. Weather is persisted at the latest available value during rollout.",
            "step_hours": 3,
            "base_time": t0.isoformat(),
            "base_source": (live_record or {}).get("source", "historical dataset"),
            "points": points,
            "next_24h": next_day,
            "peak": {
                "aqi": peak["aqi"],
                "ts": peak["ts"],
                "category": classify(peak["aqi"])["category"],
                "color": classify(peak["aqi"])["color"],
            },
        }
        self._cache[key] = (time.monotonic(), payload)
        return payload


    def forecast_station_from_cams(self, station_id: str, live_bundle: dict, steps: int = DEFAULT_STEPS) -> dict:
        """Build a 3-hourly AQI outlook from CAMS hourly pollutant forecasts.

        This is a provider-model forecast, not the local recursive ML model.
        CPCB-style breakpoints are applied to trailing CAMS concentration
        averages (24 hours, or 8 hours for CO) where minimum coverage exists.
        Missing upstream values are omitted; we never fill them by repeating a
        previous pollutant value.
        """
        from datetime import datetime, timedelta
        from .live import average_cams_concentrations

        current = live_bundle.get("current") or {}
        hourly = live_bundle.get("air_hourly") or {}
        weather = live_bundle.get("weather_hourly") or {}
        times = hourly.get("time") or []
        if not current.get("timestamp") or not times:
            raise ValueError("CAMS hourly forecast is unavailable")

        base = datetime.fromisoformat(str(current["timestamp"]).replace("Z", "+00:00"))
        parsed = []
        for i, value in enumerate(times):
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if dt.tzinfo and base.tzinfo is None:
                    dt = dt.replace(tzinfo=None)
                elif base.tzinfo and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=base.tzinfo)
                parsed.append((dt, i))
            except (TypeError, ValueError):
                continue

        fields = {
            "pm25": "pm2_5", "pm10": "pm10", "no2": "nitrogen_dioxide",
            "so2": "sulphur_dioxide", "co": "carbon_monoxide",
        }
        weather_fields = {
            "temp_c": "temperature_2m",
            "relative_humidity_pct": "relative_humidity_2m",
            "wind_speed_kmh": "wind_speed_10m",
            "wind_direction_deg": "wind_direction_10m",
            "precipitation_mm": "precipitation",
        }
        weather_times = weather.get("time") or []
        weather_parsed = []
        for i, value in enumerate(weather_times):
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                if dt.tzinfo and base.tzinfo is None:
                    dt = dt.replace(tzinfo=None)
                elif base.tzinfo and dt.tzinfo is None:
                    dt = dt.replace(tzinfo=base.tzinfo)
                weather_parsed.append((dt, i))
            except (TypeError, ValueError):
                continue
        points = []
        used = set()
        for step in range(1, min(int(steps), 56) + 1):
            target = base + timedelta(hours=3 * step)
            candidates = [(abs((dt-target).total_seconds()), dt, idx) for dt, idx in parsed
                          if idx not in used and abs((dt-target).total_seconds()) <= 3600]
            if not candidates:
                continue
            _, dt, idx = min(candidates, key=lambda item: item[0])
            used.add(idx)
            values = average_cams_concentrations(hourly, dt)
            aqi_value, dominant = overall_aqi(values)
            if aqi_value is None:
                continue
            aqi_value = int(round(aqi_value))
            category = classify(aqi_value)
            weather_at = {}
            nearest_weather = min(weather_parsed, key=lambda item: abs((item[0] - dt).total_seconds()), default=None)
            if nearest_weather and abs((nearest_weather[0] - dt).total_seconds()) <= 3600:
                weather_idx = nearest_weather[1]
                for output_key, source_key in weather_fields.items():
                    series = weather.get(source_key) or []
                    weather_at[output_key] = (float(series[weather_idx])
                                              if weather_idx < len(series) and series[weather_idx] is not None
                                              else None)
            points.append({
                "ts": dt.isoformat(), "aqi": aqi_value, "pm25": values["pm25"],
                "pm10": values["pm10"], "no2": values["no2"], "so2": values["so2"],
                "co": values["co"], "dominant": dominant,
                "category": category["category"], "color": category["color"],
                **weather_at,
            })

        if not points:
            raise ValueError("CAMS returned no usable future pollutant samples")
        peak = max(points, key=lambda point: point["aqi"])
        next_day = min(points, key=lambda point: abs((datetime.fromisoformat(point["ts"]) - (base + timedelta(hours=24))).total_seconds()))
        actual_hours = max(0, round((datetime.fromisoformat(points[-1]["ts"]) - base).total_seconds() / 3600))
        return {
            "station_id": station_id, "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
            "horizon_hours": actual_hours, "horizon_days": round(actual_hours / 24, 1),
            "forecast_type": "cams_air_quality_model", "step_hours": 3,
            "base_time": base.isoformat(), "base_source": current.get("source", "Open-Meteo CAMS"),
            "forecast_source": "Open-Meteo Air Quality API · CAMS model forecast",
            "confidence_note": "CAMS concentrations are averaged over trailing 24-hour windows (8 hours for CO), requiring minimum hourly coverage, then sampled at 3-hour intervals and converted with Rasayanam's CPCB breakpoint calculation. These are gridded model estimates, not CPCB monitor forecasts. Forecast uncertainty increases with lead time; availability may end before exactly 168 hours.",
            "points": points,
            "next_24h": {"aqi": next_day["aqi"], "pm25": next_day["pm25"], "from": base.isoformat(), "ts": next_day["ts"]},
            "peak": {"aqi": peak["aqi"], "ts": peak["ts"], "category": peak["category"], "color": peak["color"]},
        }

    def forecast_all(self, steps: int = DEFAULT_STEPS, live_records: dict | None = None) -> dict[str, dict]:
        """Prefer the 7-day CAMS forecast; only use local ML as a labelled 48h fallback."""
        live_records = live_records or {}
        results = {}
        for sid in self.feed.station_ids:
            bundle = live_records.get(sid)
            try:
                if bundle and bundle.get("air_hourly"):
                    results[sid] = self.forecast_station_from_cams(sid, bundle, steps)
                elif bundle and bundle.get("current"):
                    fallback = self.forecast_station(sid, min(int(steps), 16), (bundle or {}).get("current"))
                    fallback["confidence_note"] = (
                        "CAMS forecast unavailable. Showing only the local recursive ML forecast up to 48 hours; "
                        "no seven-day values are fabricated. " + fallback.get("confidence_note", "")
                    )
                    fallback["forecast_type"] = "local_ml_fallback_48h"
                    results[sid] = fallback
                else:
                    raise ValueError("No recent live observation is available to seed a local forecast")
            except Exception as exc:
                logger.warning("CAMS forecast unavailable for %s: %s", sid, exc)
                try:
                    current = (bundle or {}).get("current")
                    fallback = self.forecast_station(sid, min(int(steps), 16), current)
                    fallback["forecast_type"] = "local_ml_fallback_48h"
                    fallback["confidence_note"] = (
                        "CAMS forecast unavailable; showing only the local recursive ML forecast up to 48 hours. "
                        "This experimental forecast holds current weather and unmodeled pollutant species constant. "
                        + str(exc)
                    )
                    results[sid] = fallback
                except Exception as seed_exc:
                    results[sid] = {
                        "station_id": sid,
                        "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
                        "horizon_hours": 0,
                        "horizon_days": 0,
                        "forecast_type": "unavailable",
                        "step_hours": 3,
                        "base_time": (bundle or {}).get("current", {}).get("timestamp"),
                        "base_source": (bundle or {}).get("current", {}).get("source"),
                        "forecast_source": None,
                        "confidence_note": "Forecast unavailable: " + str(seed_exc),
                        "points": [],
                        "next_24h": None,
                        "peak": None,
                    }
        return results
