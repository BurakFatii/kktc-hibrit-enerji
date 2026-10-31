"""Meteoroloji verisi: Open-Meteo (tahmin) + geçmiş yıl saatlik arşiv.

Geçmiş yıl verisi: Open-Meteo arşivinden ECMWF IFS (~9 km). ERA5 (~25 km) KKTC'deki
aday bölgeleri ayırt edemediği için (birden çok bölge aynı hücreye düşüyordu) IFS seçildi.
Arayüzde model adı gösterilmez; yalnızca "geçmiş yıl" denir (ürün kararı).
İkisi de ücretsiz ve anahtarsızdır. Arşiv yanıtları diske önbelleklenir
(.cache/), aynı 0.25° hücre ikinci kez indirilmez.
"""
from __future__ import annotations

import datetime as dt
import json
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import numpy as np

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = [
    "shortwave_radiation",
    "direct_normal_irradiance",
    "diffuse_radiation",
    "temperature_2m",
    "wind_speed_10m",
    "wind_speed_100m",
    "wind_direction_10m",
    "wind_direction_100m",
    "surface_pressure",
]
CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"
_FORECAST_TTL_S = 30 * 60
_forecast_mem: dict[tuple, tuple[float, "Weather"]] = {}


@dataclass
class Weather:
    """Saatlik seri. Zaman UTC; radyasyon değerleri ÖNCEKİ saatin ortalamasıdır."""

    time: np.ndarray  # datetime64[s], UTC
    ghi: np.ndarray   # W/m2
    dni: np.ndarray   # W/m2
    dhi: np.ndarray   # W/m2
    temp: np.ndarray  # °C
    ws10: np.ndarray  # m/s
    ws100: np.ndarray
    wd10: np.ndarray  # derece, rüzgârın GELDİĞİ yön
    wd100: np.ndarray
    pressure: np.ndarray  # hPa, yüzey
    grid_lat: float
    grid_lon: float
    source: str

    def __len__(self) -> int:
        return len(self.time)

    def slice(self, mask: np.ndarray) -> "Weather":
        kw = {k: getattr(self, k)[mask] for k in
              ("time", "ghi", "dni", "dhi", "temp", "ws10", "ws100", "wd10", "wd100",
                   "pressure")}
        return Weather(**kw, grid_lat=self.grid_lat, grid_lon=self.grid_lon, source=self.source)


def _to_weather(payload: dict, source: str) -> Weather:
    h = payload["hourly"]

    n = len(h["time"])

    def arr(key: str, fill: float = 0.0) -> np.ndarray:
        # Eksik değerleri doldur (gece radyasyonu vb.)
        vals = h.get(key) or [fill] * n
        return np.array([fill if v is None else float(v) for v in vals])

    return Weather(
        time=np.array(h["time"], dtype="datetime64[s]"),
        ghi=arr("shortwave_radiation"),
        dni=arr("direct_normal_irradiance"),
        dhi=arr("diffuse_radiation"),
        temp=arr("temperature_2m"),
        ws10=arr("wind_speed_10m"),
        ws100=arr("wind_speed_100m"),
        wd10=arr("wind_direction_10m"),
        wd100=arr("wind_direction_100m"),
        pressure=arr("surface_pressure", 1013.25),
        grid_lat=float(payload.get("latitude", 0.0)),
        grid_lon=float(payload.get("longitude", 0.0)),
        source=source,
    )


def fetch_forecast(lat: float, lon: float, past_days: int = 1, days: int = 2) -> Weather:
    """Dün + bugün + yarın saatlik tahmin (Open-Meteo en iyi model karışımı)."""
    key = (round(lat, 3), round(lon, 3), past_days, days)
    hit = _forecast_mem.get(key)
    if hit and time.time() - hit[0] < _FORECAST_TTL_S:
        return hit[1]
    params = {
        "latitude": lat, "longitude": lon, "hourly": ",".join(HOURLY_VARS),
        "past_days": past_days, "forecast_days": days,
        "wind_speed_unit": "ms", "timezone": "GMT",
    }
    r = httpx.get(FORECAST_URL, params=params, timeout=20)
    r.raise_for_status()
    w = _to_weather(r.json(), "Open-Meteo tahmin")
    _forecast_mem[key] = (time.time(), w)
    return w


def last_full_year() -> int:
    return dt.date.today().year - 1


HISTORY_MODEL = "ecmwf_ifs"


def snap_key(lat: float, lon: float) -> tuple[float, float]:
    """Önbellek anahtarı: ~5 km'ye (0.05°) yuvarla.

    İstek TAM koordinatla gider; hücreyi Open-Meteo seçer (kıyıda kara hücresini
    tercih eder). Koordinatı kendimiz 0.25° ızgaraya yuvarlarsak kıyı noktalarında
    deniz hücresi seçilebilir — bu yüzden yalnızca anahtar yuvarlanır.
    """
    return round(round(lat * 20) / 20, 2), round(round(lon * 20) / 20, 2)


def fetch_history_year(lat: float, lon: float, year: int | None = None) -> Weather:
    """Bir yıllık saatlik geçmiş veri (8760 saat), HISTORY_MODEL ile."""
    year = year or last_full_year()
    slat, slon = snap_key(lat, lon)
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"hist_{HISTORY_MODEL}_{slat:.2f}_{slon:.2f}_{year}.json"
    if path.exists():
        payload = json.loads(path.read_text())
    else:
        params = {
            "latitude": round(lat, 4), "longitude": round(lon, 4),
            "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
            "hourly": ",".join(HOURLY_VARS), "models": HISTORY_MODEL,
            "wind_speed_unit": "ms", "timezone": "GMT",
        }
        for attempt in range(4):  # arşiv API'si art arda yıllık isteklerde hız sınırı uygulayabilir
            r = httpx.get(ARCHIVE_URL, params=params, timeout=90)
            if r.status_code == 200:
                break
            time.sleep(3 * (attempt + 1))
        r.raise_for_status()
        payload = r.json()
        path.write_text(json.dumps(payload))
    return _to_weather(payload, f"{year} saatlik verisi")


def current_index(w: Weather, now_utc: dt.datetime | None = None) -> int:
    """Şu anki saati kapsayan satır (radyasyon 'önceki saat' olduğu için tavan)."""
    now = now_utc or dt.datetime.now(dt.timezone.utc)
    now64 = np.datetime64(now.replace(tzinfo=None), "s")
    idx = int(np.searchsorted(w.time, now64, side="left"))
    return max(0, min(idx, len(w) - 1))
