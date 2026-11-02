from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

import uvicorn
import websockets

from backend import main
from backend.live import LiveDataUnavailable


class OfflineLiveProvider:
    """Controlled upstream outage used only for API integration checks."""

    available_station = None

    @staticmethod
    def _bundle(station_id):
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None, second=0, microsecond=0).isoformat(timespec="minutes")
        current = {
            "station_id": station_id, "timestamp": timestamp, "aqi": 75,
            "category": "Satisfactory", "color": "#8bc34a", "severity": 1,
            "dominant": "pm25", "pm25": 45, "pm10": 80, "no2": 20,
            "so2": 15, "co": 1.0, "temp_c": 21,
            "relative_humidity_pct": 55, "dew_point_c": 11,
            "precipitation_mm": 0, "wind_speed_kmh": 5,
            "wind_direction_deg": 180, "source": "Open-Meteo CAMS gridded estimate",
            "source_note": "Controlled test fixture", "current_available": True,
            "_history": [],
        }
        return {"current": current, "air_hourly": {}, "weather_hourly": {},
                "cache_status": "fresh", "cache_age_seconds": 0}

    def get_stations(self, stations):
        if self.available_station:
            return {self.available_station: self._bundle(self.available_station)}
        return {}

    def get_station(self, station):
        if station["station_id"] == self.available_station:
            return self._bundle(self.available_station)
        raise LiveDataUnavailable("controlled upstream outage")


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provider_patch = patch.object(main, "LiveDataProvider", OfflineLiveProvider)
        cls.provider_patch.start()
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            cls.port = probe.getsockname()[1]
        cls.server = uvicorn.Server(uvicorn.Config(
            main.app, host="127.0.0.1", port=cls.port, log_level="critical",
            lifespan="on", access_log=False,
        ))
        cls.thread = threading.Thread(target=cls.server.run, daemon=True)
        cls.thread.start()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if cls.server.started:
                break
            if not cls.thread.is_alive():
                raise RuntimeError("Uvicorn exited before startup completed")
            time.sleep(0.05)
        else:
            cls.server.should_exit = True
            raise TimeoutError("Uvicorn did not start in 30 seconds")
        cls.base = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(timeout=10)
        cls.provider_patch.stop()

    @classmethod
    def get_json(cls, path):
        with urlopen(cls.base + path, timeout=10) as response:
            return response.status, json.loads(response.read())

    def test_all_rest_routes_and_static_assets(self):
        status, health = self.get_json("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(health["data_loaded"])

        _, stations = self.get_json("/api/stations")
        self.assertEqual(stations["count"], 8)
        sid = stations["stations"][0]["station_id"]

        _, current = self.get_json("/api/current?station=" + sid)
        self.assertEqual(current["data_status"], "unavailable")
        self.assertFalse(current["station"]["current_available"])
        self.assertIsNone(current["station"]["aqi"])
        self.assertIsNotNone(current["station"]["historical_observation"]["timestamp"])

        _, current_all = self.get_json("/api/current")
        self.assertEqual(len(current_all["stations"]), 8)
        self.assertEqual(current_all["data_status"], "unavailable")

        _, map_payload = self.get_json("/api/map")
        self.assertEqual(len(map_payload["stations"]), 8)
        self.assertTrue(all(item["aqi"] is None for item in map_payload["stations"]))

        _, recent_history = self.get_json(f"/api/history?station={sid}&hours=24")
        self.assertEqual(recent_history["count"], 0)
        self.assertIn("unavailable", recent_history["source"].lower())

        _, week_history = self.get_json(f"/api/history?station={sid}&hours=168")
        self.assertGreater(week_history["count"], 0)
        self.assertIn("historical", week_history["source"].lower())

        _, month_history = self.get_json(f"/api/history?station={sid}&hours=720")
        self.assertGreater(month_history["count"], 0)
        self.assertIn("Historical CSV ends at", month_history["source_note"])

        _, forecast = self.get_json(f"/api/forecast?station={sid}&steps=56")
        self.assertEqual(forecast["stations"][sid]["forecast_type"], "unavailable")
        self.assertEqual(forecast["stations"][sid]["points"], [])

        for route in ("/api/diwali", "/api/articles", "/api/doctors", "/api/remedies"):
            response_status, payload = self.get_json(route)
            self.assertEqual(response_status, 200)
            self.assertIsInstance(payload, dict)

        _, remedies = self.get_json("/api/remedies")
        remedy_id = remedies["remedies"][0]["id"]
        self.assertEqual(self.get_json(f"/api/remedies/{remedy_id}")[0], 200)

        with urlopen(self.base + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"Rasayanam", response.read(10000))
        with urlopen(self.base + "/static/assets/rasayanam-intro.mp4") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("video", response.headers.get_content_type())
        with urlopen(self.base + f"/remedies/{remedy_id}") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"Recipe", response.read(1000))

        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/api/current?station=UNKNOWN", timeout=10)
        self.assertEqual(error.exception.code, 404)

    def test_websocket_snapshot_keeps_transport_and_data_status_separate(self):
        async def receive_snapshot():
            async with websockets.connect(f"ws://127.0.0.1:{self.port}/ws", open_timeout=10) as socket:
                return json.loads(await asyncio.wait_for(socket.recv(), timeout=10))

        payload = asyncio.run(receive_snapshot())
        self.assertEqual(payload["type"], "snapshot")
        self.assertEqual(payload["connection_status"], "connected")
        self.assertEqual(payload["data_status"], "unavailable")
        self.assertEqual(len(payload["stations"]), 8)
        self.assertTrue(all(item["current_available"] is False for item in payload["stations"]))

    def test_partial_live_station_response_preserves_other_map_locations(self):
        _, all_stations = self.get_json("/api/stations")
        sid = all_stations["stations"][0]["station_id"]
        OfflineLiveProvider.available_station = sid
        try:
            _, current = self.get_json(f"/api/current?station={sid}")
            self.assertTrue(current["station"]["current_available"])
            self.assertEqual(current["station"]["aqi"], 75)

            _, regional = self.get_json("/api/map")
            available = [item for item in regional["stations"] if item["current_available"]]
            unavailable = [item for item in regional["stations"] if not item["current_available"]]
            self.assertEqual(len(available), 1)
            self.assertEqual(len(unavailable), 7)
        finally:
            OfflineLiveProvider.available_station = None


if __name__ == "__main__":
    unittest.main()
