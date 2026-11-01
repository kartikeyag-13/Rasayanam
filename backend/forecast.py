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

from backend.aqi import classify
from ml.features import (
    FEATURE_COLUMNS,
    HISTORY_KEYS,
    WEATHER_FEATURES,
    make_rollout_row,
)

logger = logging.getLogger("rasaynam.forecast")

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
        key = (station_id, steps, (live_record or {}).get('timestamp', 'historical'))
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < CACHE_TTL:
            return cached[1]

        t0, hist, weather = self._latest_row(station_id)
        if live_record:
            live_ts = pd.Timestamp(live_record["timestamp"])
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

    def forecast_all(self, steps: int = DEFAULT_STEPS, live_records: dict | None = None) -> dict[str, dict]:
        live_records = live_records or {}
        return {sid: self.forecast_station(sid, steps, live_records.get(sid)) for sid in self.feed.station_ids}
