from __future__ import annotations

import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from email.message import Message
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
from urllib.error import HTTPError

from backend.aqi import overall_aqi, sub_index
from backend.forecast import ForecastService
from backend.live import AIR_URL, WEATHER_URL, LiveDataProvider, LiveDataUnavailable


def provider_payload(now: str, air: bool) -> dict:
    timestamps = [f"2026-11-02T{hour:02d}:00" for hour in range(24)]
    if air:
        return {
            "current": {"time": now, "pm2_5": 40, "pm10": 70,
                        "carbon_monoxide": 1000, "nitrogen_dioxide": 20,
                        "sulphur_dioxide": 10},
            "hourly": {"time": timestamps,
                       "pm2_5": [40] * 24, "pm10": [70] * 24,
                       "carbon_monoxide": [1000] * 24,
                       "nitrogen_dioxide": [20] * 24,
                       "sulphur_dioxide": [10] * 24},
        }
    return {
        "current": {"temperature_2m": 20, "relative_humidity_2m": 50,
                    "dew_point_2m": 10, "surface_pressure": 1000,
                    "precipitation": 0, "wind_speed_10m": 5,
                    "wind_direction_10m": 180},
        "hourly": {"time": timestamps,
                   "temperature_2m": [20] * 24,
                   "relative_humidity_2m": [50] * 24,
                   "dew_point_2m": [10] * 24,
                   "surface_pressure": [1000] * 24,
                   "precipitation": [0] * 24,
                   "wind_speed_10m": [5] * 24,
                   "wind_direction_10m": [180] * 24},
    }


class AQIValidationTests(unittest.TestCase):
    def test_cpcb_breakpoint_interpolation(self):
        self.assertEqual(sub_index("pm25", 30), 50)
        self.assertEqual(sub_index("pm25", 45), 75)
        self.assertEqual(sub_index("co", 1), 50)

    def test_overall_requires_three_species_including_particulate(self):
        aqi, dominant = overall_aqi({"pm25": 80, "no2": 50, "so2": 60})
        self.assertIsNotNone(aqi)
        self.assertEqual(dominant, "pm25")
        self.assertEqual(overall_aqi({"pm25": 80, "no2": 50}), (None, None))
        self.assertEqual(overall_aqi({"no2": 50, "so2": 60, "co": 2}), (None, None))


class LiveProviderTests(unittest.TestCase):
    def setUp(self):
        self.provider = LiveDataProvider()
        self.stations = [
            {"station_id": f"S{i}", "latitude": 28 + i / 10, "longitude": 77 + i / 10}
            for i in range(8)
        ]

    def _json_response(self, url, params):
        count = len(params["latitude"].split(","))
        is_air = url == AIR_URL
        rows = [provider_payload("2026-11-02T23:00", is_air) for _ in range(count)]
        return rows[0] if count == 1 else rows

    def test_eight_locations_are_batched_and_reused(self):
        with patch.object(self.provider, "_get_json", side_effect=self._json_response) as get_json:
            results = self.provider.get_stations(self.stations)
            self.assertEqual(set(results), {station["station_id"] for station in self.stations})
            self.assertEqual(get_json.call_count, 2)
            self.assertEqual(results["S0"]["current"]["co"], 1.0)
            self.assertTrue(results["S0"]["current"]["current_available"])
            self.assertGreater(results["S0"]["current"]["aqi"], 0)

            again = self.provider.get_stations(self.stations)
            self.assertEqual(get_json.call_count, 2)
            self.assertEqual(again["S0"]["cache_status"], "fresh")

    def test_simultaneous_cold_requests_share_one_batch(self):
        with patch.object(self.provider, "_get_json", side_effect=self._json_response) as get_json:
            with ThreadPoolExecutor(max_workers=6) as pool:
                results = list(pool.map(lambda _: self.provider.get_stations(self.stations), range(6)))
            self.assertTrue(all(len(result) == 8 for result in results))
            self.assertEqual(get_json.call_count, 2)

    def test_stale_bundle_is_returned_with_explicit_status_after_failure(self):
        with patch.object(self.provider, "_get_json", side_effect=self._json_response):
            self.provider.get_stations(self.stations[:1])
        self.provider._cache["S0"] = (self.provider._cache["S0"][0] - 3601, self.provider._cache["S0"][1])
        self.provider._raw_cache["S0"] = {
            key: (stamp - 3601, payload)
            for key, (stamp, payload) in self.provider._raw_cache["S0"].items()
        }
        with patch.object(self.provider, "_get_json", side_effect=LiveDataUnavailable("offline")):
            result = self.provider.get_stations(self.stations[:1])["S0"]
        self.assertEqual(result["cache_status"], "stale_cache")
        self.assertGreaterEqual(result["cache_age_seconds"], 3601)

    def test_429_retry_after_suppresses_followup_requests(self):
        headers = Message()
        headers["Retry-After"] = "60"
        error = HTTPError(AIR_URL, 429, "rate limited", headers, None)
        with patch("backend.live.urlopen", side_effect=error) as open_url:
            with self.assertRaises(LiveDataUnavailable):
                self.provider._get_json(AIR_URL, {})
            with self.assertRaisesRegex(LiveDataUnavailable, "rate-limited"):
                self.provider._get_json(AIR_URL, {})
        self.assertEqual(open_url.call_count, 1)
        self.assertGreaterEqual(self.provider._blocked_until[AIR_URL], 0)

    def test_timeout_retries_are_bounded(self):
        with patch("backend.live.urlopen", side_effect=TimeoutError("timed out")) as open_url, \
                patch("backend.live.time.sleep"):
            with self.assertRaises(LiveDataUnavailable):
                self.provider._get_json(WEATHER_URL, {})
        self.assertEqual(open_url.call_count, 3)

    def test_malformed_batch_response_is_ignored_without_crashing(self):
        with patch.object(self.provider, "_get_json", side_effect=[{"unexpected": True}, provider_payload("2026-11-02T23:00", False)]):
            self.assertEqual(self.provider.get_stations(self.stations[:2]), {})

    def test_valid_timestamped_cams_forecast_points(self):
        now = datetime.now(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None, minute=0, second=0, microsecond=0)
        timestamps = [(now - timedelta(hours=23 - i)).isoformat(timespec="minutes") for i in range(24)]
        timestamps.extend((now + timedelta(hours=3 * i)).isoformat(timespec="minutes") for i in range(1, 5))
        hourly = {"time": timestamps}
        for key, value in (("pm2_5", 45), ("pm10", 75), ("carbon_monoxide", 900),
                           ("nitrogen_dioxide", 20), ("sulphur_dioxide", 12)):
            hourly[key] = [value] * len(timestamps)
        service = ForecastService.__new__(ForecastService)
        forecast = service.forecast_station_from_cams(
            "S0", {"current": {"timestamp": now.isoformat(timespec="minutes"), "source": "CAMS"},
                   "air_hourly": hourly, "weather_hourly": {}}, steps=4,
        )
        self.assertEqual(len(forecast["points"]), 4)
        self.assertTrue(all(point["aqi"] is not None for point in forecast["points"]))
        self.assertEqual(forecast["base_time"], now.isoformat())


if __name__ == "__main__":
    unittest.main()
