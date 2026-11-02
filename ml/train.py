"""Rasayanam prediction-model training pipeline.

Usage:
    python -m ml.train

Reads the historical dataset, engineers features (see ml.features), trains
gradient-boosting regressors for PM2.5 and AQI at 3-hour and 24-hour horizons,
evaluates on a strictly time-ordered 2025 hold-out, and writes:

    ml/artifacts/model.joblib      trained models
    ml/artifacts/metrics.json      MAE / RMSE / R2 + persistence baselines
    ml/artifacts/feature_spec.json feature list & training metadata
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from ml.features import FEATURE_COLUMNS, TARGETS, prepare_training_frame

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "ncr_punjab_haryana_weather_aqi_2020_2025.csv"
DATA_PATH = Path(os.environ.get("DATA_PATH", DEFAULT_DATA))
ARTIFACTS_DIR = Path(os.environ.get("ARTIFACTS_DIR", Path(__file__).parent / "artifacts"))

TRAIN_END = pd.Timestamp("2024-12-31 23:59:59")  # test = 2025 (strictly future)

MODEL_PARAMS = dict(
    max_iter=250,
    learning_rate=0.08,
    max_leaf_nodes=31,
    min_samples_leaf=30,
    l2_regularization=0.1,
    random_state=42,
)


def load_dataset(path: Path) -> pd.DataFrame:
    print(f"[rasayanam] reading {path}")
    df = pd.read_csv(path)
    # timestamps in the file look like "2020-09-01 00:%00:%00" — keep date + hour
    ts = pd.to_datetime(
        df["timestamp"].astype(str).str.slice(0, 13) + ":00:00",
        format="%Y-%m-%d %H:%M:%S",
    )
    df["timestamp"] = ts
    print(f"[rasayanam] {len(df)} rows, {df['station_id'].nunique()} stations, "
          f"{df['timestamp'].min()} -> {df['timestamp'].max()}")
    return df


def metrics_block(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 3),
        "r2": round(float(r2_score(y_true, y_pred)), 4),
    }


def main() -> int:
    if not DATA_PATH.exists():
        print(f"[rasayanam] ERROR: dataset not found at {DATA_PATH}", file=sys.stderr)
        return 1

    t0 = time.time()
    raw = load_dataset(DATA_PATH)
    frame = prepare_training_frame(raw)

    train = frame[frame["timestamp"] <= TRAIN_END]
    test = frame[frame["timestamp"] > TRAIN_END]
    print(f"[rasayanam] train rows={len(train)} (<= {TRAIN_END.date()})  "
          f"test rows={len(test)} (2025 hold-out)")
    print(f"[rasayanam] features: {len(FEATURE_COLUMNS)}")

    # persistence baselines: "tomorrow looks like right now"
    baseline_col = {"pm25_3h": "pm25_ugm3", "aqi_3h": "aqi_now",
                    "pm25_24h": "pm25_ugm3", "aqi_24h": "aqi_now"}

    models: dict[str, HistGradientBoostingRegressor] = {}
    metrics: dict[str, dict] = {}

    for target_name, target_col in TARGETS.items():
        tr = train.dropna(subset=[target_col])
        te = test.dropna(subset=[target_col])
        X_tr, y_tr = tr[FEATURE_COLUMNS], tr[target_col].to_numpy(dtype=float)
        X_te, y_te = te[FEATURE_COLUMNS], te[target_col].to_numpy(dtype=float)

        print(f"\n[rasayanam] target={target_name}  train={len(X_tr)} test={len(X_te)}")
        model = HistGradientBoostingRegressor(**MODEL_PARAMS)
        model.fit(X_tr, y_tr)
        y_pred = model.predict(X_te)

        m = metrics_block(y_te, y_pred)
        base_pred = te[baseline_col[target_name]].to_numpy(dtype=float)
        base = metrics_block(y_te, base_pred)
        m["baseline_persistence_mae"] = base["mae"]
        m["improvement_over_baseline_pct"] = round(
            100 * (base["mae"] - m["mae"]) / max(base["mae"], 1e-9), 1
        )
        metrics[target_name] = m
        models[target_name] = model
        print(f"[rasayanam]   MAE={m['mae']}  RMSE={m['rmse']}  R2={m['r2']}  "
              f"(persistence MAE={base['mae']} -> {m['improvement_over_baseline_pct']}% better)")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(models, ARTIFACTS_DIR / "model.joblib")

    feature_spec = {
        "features": FEATURE_COLUMNS,
        "targets": TARGETS,
        "history_keys": ["pm25_ugm3", "pm10_ugm3", "no2_ugm3", "so2_ugm3", "co_mgm3", "aqi"],
        "step_hours": 3,
        "rollout_steps": 56,  # legacy rollout setting; public 7-day forecast now uses hourly CAMS air-quality forecasts
        "model_type": "HistGradientBoostingRegressor",
        "model_params": MODEL_PARAMS,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "data_path": str(DATA_PATH),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_until": str(TRAIN_END.date()),
        "stations": sorted(frame["station_id"].unique().tolist()),
    }
    (ARTIFACTS_DIR / "feature_spec.json").write_text(json.dumps(feature_spec, indent=2))
    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))

    print(f"\n[rasayanam] artifacts -> {ARTIFACTS_DIR}")
    print("[rasayanam] metrics.json:")
    print(json.dumps(metrics, indent=2))
    print(f"[rasayanam] done in {time.time() - t0:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
