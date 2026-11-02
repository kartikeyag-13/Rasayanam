"""Rasayanam backend application.

FastAPI service that hosts:
  * REST API           /api/*      — current AQI, history, forecasts, content
  * WEBSOCKET server   /ws         — snapshot on connect + broadcast of the
                                     latest readings & fresh ML forecasts every
                                     WS_BROADCAST_INTERVAL seconds (default 600
                                     = 10 minutes)
  * the website        /           — static single-page frontend

Run:
    uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import content
from .aqi import classify
from .feed import DataFeed
from .forecast import ForecastService
from .live import LiveDataProvider, LiveDataUnavailable

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger("rasayanam")

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static"

INTERVAL = max(10, int(os.environ.get("WS_BROADCAST_INTERVAL", "600")))

feed: DataFeed | None = None
svc: ForecastService | None = None
live_provider: LiveDataProvider | None = None
_seq = itertools.count(1)


# ------------------------------------------------------------- websocket hub --
class Hub:
    """Registry of connected WebSocket clients + fan-out."""

    def __init__(self) -> None:
        self.clients: dict[WebSocket, None] = {}

    def add(self, ws: WebSocket) -> None:
        self.clients[ws] = None

    def remove(self, ws: WebSocket) -> None:
        self.clients.pop(ws, None)

    def __len__(self) -> int:
        return len(self.clients)

    async def broadcast(self, payload: dict) -> int:
        text = json.dumps(payload, separators=(",", ":"))
        delivered = 0
        dead: list[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_text(text)
                delivered += 1
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove(ws)
        return delivered


hub = Hub()


# ----------------------------------------------------------------- payloads --
def _require_feed() -> DataFeed:
    if feed is None:
        raise HTTPException(status_code=503, detail="dataset not loaded yet")
    return feed


def _meta_map(f: DataFeed) -> dict[str, dict]:
    return {m["station_id"]: m for m in f.metadata()}


def _live_bundle(station_meta: dict) -> dict | None:
    """Return cached current + hourly CAMS forecast bundle; None on provider failure."""
    if live_provider is None:
        return None
    try:
        return live_provider.get_station(station_meta)
    except Exception as exc:
        logger.warning("live provider unavailable for %s: %s", station_meta["station_id"], exc)
        return None


def _live_record(station_meta: dict) -> dict | None:
    bundle = _live_bundle(station_meta)
    return bundle.get("current") if bundle else None


def _current_record(station_id: str, meta: dict) -> tuple[dict, str]:
    live = _live_record(meta)
    if live is not None:
        return live, "external_model_estimate"
    rec = _require_feed().latest(station_id)
    rec["source"] = "historical_csv_fallback"
    rec["source_note"] = "Live provider unavailable; showing last historical CSV observation."
    return rec, "historical_fallback"


def _station_payload(rec: dict, meta: dict) -> dict:
    cls = classify(rec["aqi"])
    return {
        "station_id": rec["station_id"],
        "city": meta["city"],
        "state": meta["state"],
        "area": meta["area"],
        "label": meta["label"],
        "latitude": meta["latitude"],
        "longitude": meta["longitude"],
        "timestamp": rec["timestamp"],
        "source": rec.get("source", "historical CSV"),
        "source_note": rec.get("source_note", "Historical dataset observation."),
        "dominant": rec["dominant"],
        "reading": {
            k: rec[k]
            for k in (
                "pm25",
                "pm10",
                "no2",
                "so2",
                "co",
                "temp_c",
                "relative_humidity_pct",
                "dew_point_c",
                "precipitation_mm",
                "wind_speed_kmh",
                "wind_direction_deg",
            )
        },
        "aqi": cls["aqi"],
        "category": cls["category"],
        "color": cls["color"],
        "range": cls["range"],
        "severity": cls["severity"],
        "advisory": {
            "summary": cls["summary"],
            "sensitive": cls["sensitive"],
            "do": cls["do"],
            "avoid": cls["avoid"],
            "mask": cls["mask"],
            "outdoor": cls["outdoor"],
        },
    }


def _all_station_payloads(f: DataFeed) -> list[dict]:
    metas = _meta_map(f)
    return [_station_payload(rec, metas[rec["station_id"]]) for rec in f.latest_per_station()]


def build_payload(msg_type: str, seq_no: int = 0) -> dict:
    f = _require_feed()
    metas = _meta_map(f)
    live_bundles = {}
    current_records = []
    for sid in f.station_ids:
        bundle = _live_bundle(metas[sid])
        rec = bundle["current"] if bundle else None
        if rec is None:
            rec, _source = _current_record(sid, metas[sid])
        current_records.append(_station_payload(rec, metas[sid]))
        if bundle:
            live_bundles[sid] = bundle
    forecasts = svc.forecast_all(56, live_bundles) if svc else {}
    return {
        "type": msg_type,
        "seq": seq_no,
        "server_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "interval_seconds": INTERVAL,
        "data_as_of": max((x["timestamp"] for x in current_records), default=f.latest_ts.isoformat()),
        "stations": current_records,
        "forecast": {
            sid: {
                "base_time": fp["base_time"],
                "horizon_hours": fp["horizon_hours"],
                "horizon_days": fp["horizon_days"],
                "forecast_type": fp.get("forecast_type"),
                "forecast_source": fp.get("forecast_source"),
                "confidence_note": fp["confidence_note"],
                "peak": fp["peak"],
                "next_24h": fp["next_24h"],
                "points": fp["points"],
            }
            for sid, fp in forecasts.items()
        },
    }


# ------------------------------------------------------------ broadcast loop --
async def broadcast_loop() -> None:
    """Push latest data + fresh forecast to every client every INTERVAL seconds."""
    while True:
        await asyncio.sleep(INTERVAL)
        if not len(hub):
            logger.info("broadcast tick with no clients — skipping push")
            continue
        try:
            payload = build_payload("broadcast", next(_seq))
            delivered = await hub.broadcast(payload)
            logger.info(
                "broadcast seq=%s -> %d client(s) (data as of %s)",
                payload["seq"],
                delivered,
                payload["data_as_of"],
            )
        except Exception:
            logger.exception("broadcast failed")


# ---------------------------------------------------------------- lifespan --
@asynccontextmanager
async def lifespan(app: FastAPI):
    global feed, svc, live_provider
    feed = DataFeed()
    live_provider = LiveDataProvider()
    logger.info(
        "dataset loaded: %s rows | %s stations | %s -> %s",
        len(feed.df),
        len(feed.station_ids),
        feed.earliest_ts,
        feed.latest_ts,
    )
    try:
        svc = ForecastService(feed)
        logger.info("Rasayanam forecast service ready")
    except Exception:
        logger.exception("FAILED to load ML artifacts — /api/forecast and pushes will lack forecasts")
        svc = None
    task = asyncio.create_task(broadcast_loop())
    app.state.broadcast_task = task
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(
    title="Rasayanam API",
    description="Neighborhood air-quality prediction & health platform (Diwali focus)",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------- websocket --
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Live push channel: snapshot on connect, then a broadcast every 10 minutes."""
    await ws.accept()
    hub.add(ws)
    logger.info("ws client connected (%d online)", len(hub))
    try:
        await ws.send_text(json.dumps(build_payload("snapshot"), separators=(",", ":")))
        while True:
            await ws.receive_text()  # clients are silent; this waits for frames / disconnect
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("websocket error")
    finally:
        hub.remove(ws)
        logger.info("ws client disconnected (%d online)", len(hub))


# --------------------------------------------------------------------- REST --
@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "ws_interval_seconds": INTERVAL,
        "ws_clients": len(hub),
        "ws_endpoint": "/ws",
        "data_loaded": feed is not None,
        "model_loaded": svc is not None,
        "historical_data_as_of": feed.latest_ts.isoformat() if feed else None,
        "live_provider": "Open-Meteo CAMS (gridded estimate)" if live_provider else None,
        "stations": len(feed.station_ids) if feed else 0,
        "model": svc.info if svc else None,
        "server_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/api/stations")
def stations() -> dict:
    f = _require_feed()
    return {"count": len(f.station_ids), "stations": f.metadata()}


@app.get("/api/current")
def current(station: str | None = Query(None)) -> dict:
    f = _require_feed()
    metas = _meta_map(f)
    if station:
        if station not in metas:
            raise HTTPException(status_code=404, detail=f"unknown station: {station}")
        rec, source_status = _current_record(station, metas[station])
        return {"data_as_of": rec["timestamp"], "source_status": source_status,
                "station": _station_payload(rec, metas[station])}
    items = []
    for sid in f.station_ids:
        rec, _status = _current_record(sid, metas[sid])
        items.append(_station_payload(rec, metas[sid]))
    return {"data_as_of": max((x["timestamp"] for x in items), default=f.latest_ts.isoformat()),
            "stations": items}


@app.get("/api/map")
def map_data() -> dict:
    """Regional map payload: current sampled AQI plus per-station 7-day forecasts.

    Spatial values are sampled at the eight configured station coordinates. The
    frontend may visualize a smoothed heat layer, but it must not imply that the
    interpolated surface is a measured street-level boundary.
    """
    f = _require_feed()
    metas = _meta_map(f)
    current_items = []
    live_bundles = {}
    for sid in f.station_ids:
        bundle = _live_bundle(metas[sid])
        rec = bundle["current"] if bundle else None
        if rec is None:
            rec, _status = _current_record(sid, metas[sid])
        current_items.append(_station_payload(rec, metas[sid]))
        if bundle:
            live_bundles[sid] = bundle
    forecasts = svc.forecast_all(56, live_bundles) if svc else {}
    return {
        "region": "NCR · Punjab · Haryana",
        "data_as_of": max((x["timestamp"] for x in current_items), default=None),
        "stations": current_items,
        "forecast": {
            sid: {"base_time": value["base_time"], "step_hours": value["step_hours"],
                  "forecast_type": value.get("forecast_type"), "forecast_source": value.get("forecast_source"),
                  "horizon_hours": value.get("horizon_hours"), "confidence_note": value["confidence_note"], "points": value["points"]}
            for sid, value in forecasts.items()
        },
        "spatial_note": "Markers are sampled CAMS model-grid estimates at station coordinates, not CPCB ground monitors. The smoothed heat layer is a visual interpolation between sparse sample points; it is not a measured pollution boundary or street-level exposure map.",
    }


@app.get("/api/history")
def history(
    station: str | None = Query(None),
    hours: float | None = Query(None, gt=0, le=50000),
    max_points: int = Query(500, ge=10, le=2000),
) -> dict:
    f = _require_feed()
    sid = station or f.station_ids[0]
    if sid not in f.station_ids:
        raise HTTPException(status_code=404, detail=f"unknown station: {sid}")

    # Short-range charts must never silently fall back to the old CSV: that
    # would plot December 2025 beside a November 2026 live AQI reading.
    # Open-Meteo timestamps are local wall-clock strings; normalize any offset
    # before comparing them with the hourly archive timestamps.
    if hours is not None and hours <= 48:
        if live_provider is None:
            return {"station_id": sid, "count": 0, "points": [],
                    "source": "Live history unavailable",
                    "source_note": "The live air-quality provider is not initialized; historical CSV data was deliberately not substituted."}
        try:
            meta = _meta_map(f)[sid]
            live_bundle = live_provider.get_station(meta)
            live_points = live_bundle["current"].get("_history", [])
            from datetime import datetime, timedelta
            def local_time(value: str):
                parsed = datetime.fromisoformat(value)
                return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
            now = local_time(live_bundle["current"]["timestamp"])
            cutoff = now - timedelta(hours=float(hours))
            points = [p for p in live_points if local_time(p["timestamp"]) >= cutoff]
            if points:
                return {"station_id": sid, "count": len(points), "points": points,
                        "source": "Open-Meteo CAMS live model history",
                        "source_note": "Recent gridded model estimates; not CPCB ground-monitor observations."}
            return {"station_id": sid, "count": 0, "points": [],
                    "source": "Live history unavailable",
                    "source_note": "The provider returned no observations inside the requested time window; historical CSV data was deliberately not substituted."}
        except Exception as exc:
            logger.warning("live history unavailable for %s: %s", sid, exc)
            return {"station_id": sid, "count": 0, "points": [],
                    "source": "Live history unavailable",
                    "source_note": str(exc)}

    # Longer ranges are historical project data, not recent live observations.
    points = f.history(sid, hours=hours, max_points=max_points)
    return {"station_id": sid, "count": len(points), "points": points,
            "source": "historical project dataset",
            "source_note": f"Historical CSV ends at {f.latest_ts.isoformat()}; not live observations."}


@app.get("/api/forecast")
def forecast(
    station: str | None = Query(None),
    steps: int = Query(56, ge=4, le=56),
) -> dict:
    f = _require_feed()
    if svc is None:
        raise HTTPException(status_code=503, detail="model artifacts not loaded")
    if station:
        try:
            f.station_df(station)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"unknown station: {station}")
        bundle = _live_bundle(_meta_map(f)[station])
        result = {station: svc.forecast_all(steps, {station: bundle} if bundle else {}).get(station)}
    else:
        live_bundles = {}
        for sid in f.station_ids:
            bundle = _live_bundle(_meta_map(f)[sid])
            if bundle is not None:
                live_bundles[sid] = bundle
        result = svc.forecast_all(steps, live_bundles)
    return {"model": svc.info, "stations": result}


@app.get("/api/diwali")
def diwali() -> dict:
    return _require_feed().diwali_climatology()


@app.get("/api/articles")
def articles() -> dict:
    return {"count": len(content.ARTICLES), "articles": content.ARTICLES}


@app.get("/api/doctors")
def doctors(
    city: str | None = Query(None),
    specialty: str | None = Query(None),
) -> dict:
    items = content.filter_doctors(city, specialty)
    facets = content.doctor_facets()
    return {
        "count": len(items),
        "doctors": items,
        "cities": facets["cities"],
        "specialties": facets["specialties"],
        "note": "Curated directory of hospitals with ENT & respiratory care. "
        "Verify timings, doctors-on-duty and contact details before visiting; "
        "in an emergency dial 112 / 108.",
    }


@app.get("/api/remedies")
def remedies() -> dict:
    return {
        "count": len(content.REMEDIES),
        "remedies": [content.get_remedy(item["id"]) for item in content.REMEDIES],
        "note": "Supportive comfort measures and traditional context only; not a cure, lung cleanse, pollution shield, or substitute for medical care.",
    }


@app.get("/api/remedies/{remedy_id}")
def remedy_detail(remedy_id: str) -> dict:
    item = content.get_remedy(remedy_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Remedy not found")
    return {"remedy": item}


# ------------------------------------------------------------------- static --
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/remedies/{remedy_id}", include_in_schema=False)
def remedy_page(remedy_id: str) -> FileResponse:
    if content.get_remedy(remedy_id) is None:
        raise HTTPException(status_code=404, detail="Remedy not found")
    return FileResponse(STATIC_DIR / "remedy.html")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
