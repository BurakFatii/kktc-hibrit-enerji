"""Open-Meteo istemcisi: ücretsiz, anahtarsız, KKTC'yi kapsar."""
from __future__ import annotations

import requests

BASE = "https://api.open-meteo.com/v1/forecast"


def fetch_open_meteo(lat: float, lon: float, timeout: int = 15) -> dict:
    """Saatlik güneş + rüzgar + hava durumu verisini çek."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join([
            "shortwave_radiation",
            "direct_normal_irradiance",
            "wind_speed_10m",
            "temperature_2m",
            "weathercode",
        ]),
        "current": ",".join([
            "shortwave_radiation",
            "wind_speed_10m",
            "temperature_2m",
            "weathercode",
        ]),
        "timezone": "Asia/Nicosia",
        "forecast_days": 3,
        "wind_speed_unit": "ms",
    }
    r = requests.get(BASE, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def current_values(payload: dict) -> dict:
    """Anlık değerleri tek sözlük olarak döndür."""
    cur = payload.get("current", {})
    return {
        "ghi": float(cur.get("shortwave_radiation", 0.0) or 0.0),  # W/m2
        "wind_ms": float(cur.get("wind_speed_10m", 0.0) or 0.0),   # m/s
        "temp_c": float(cur.get("temperature_2m", 0.0) or 0.0),
        "weathercode": int(cur.get("weathercode", 0) or 0),
    }
