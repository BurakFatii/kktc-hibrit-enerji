"""Harita katmanları için KKTC üzerinde ızgara verisi (Open-Meteo, anahtarsız).

- Güneş: geçmiş yılın günlük ışınım toplamından yıllık yatay ışınım (kWh/m²), yalnızca KKTC kara noktaları.
  Geçmiş yıl verisi meteo.HISTORY_MODEL ile; yanıt diske önbelleklenir (.cache/), aynı yıl tekrar indirilmez.
- Rüzgâr: şu anki 100 m rüzgâr hızı ve yönü (u, v bileşenleri), denizi de kapsayan dikdörtgen ızgara.
  Haritada parçacık akımı olarak canlandırılır. 15 dk önbellek.

Kara sınırı assets/kisit_bolgeleri.geojson içindeki 'sinir' çizgilerinden kurulur.
"""
from __future__ import annotations

import json
import math
import time
from functools import lru_cache
from pathlib import Path

import httpx
import numpy as np
from shapely import STRtree
from shapely.geometry import Point, Polygon, shape
from shapely.ops import unary_union

from . import meteo

BORDER = Path(__file__).resolve().parents[2] / "assets" / "kisit_bolgeleri.geojson"
# KKTC'yi kapsayan dikdörtgen (sınır çizgilerinin kutusu + pay)
LAT0, LAT1, LON0, LON1 = 34.95, 35.75, 32.55, 34.65
STEP = 0.1          # ~9–11 km; geçmiş yıl modelinin çözünürlüğüne yakın
WIND_TTL_S = 15 * 60

_wind_cache: dict = {}


def grid(step: float = STEP) -> tuple[np.ndarray, np.ndarray]:
    lats = np.round(np.arange(LAT0, LAT1 + 1e-9, step), 3)
    lons = np.round(np.arange(LON0, LON1 + 1e-9, step), 3)
    return lats, lons


@lru_cache(maxsize=1)
def land() -> Polygon:
    """KKTC kara alanı: sınır çizgileri tamponlanır, kapalı iç halkalar alan olarak alınır."""
    g = json.loads(BORDER.read_text(encoding="utf-8"))
    lines = shape(next(f for f in g["features"] if f["properties"].get("cls") == "sinir")["geometry"])
    b = lines.buffer(0.005)
    holes = [Polygon(i) for p in getattr(b, "geoms", [b]) for i in p.interiors]
    return unary_union(holes).buffer(0.005)


@lru_cache(maxsize=1)
def clip_rings(tol: float = 0.002) -> list[list[list[float]]]:
    """Haritada ısı katmanını kırpmak için kara alanının dış halkaları [[lon, lat], ...] (sadeleştirilmiş)."""
    poly = land().simplify(tol)
    return [[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords] for p in getattr(poly, "geoms", [poly])]


def land_points(step: float = STEP) -> list[tuple[float, float]]:
    """Kara içindeki ızgara noktaları + kıyıya 0,05°'den yakın olanlar (kıyı şeridi boş kalmasın)."""
    poly = land()
    near = poly.buffer(0.05)
    lats, lons = grid(step)
    tree = STRtree([near])
    return [(float(la), float(lo)) for la in lats for lo in lons
            if len(tree.query(Point(lo, la), predicate="within"))]


def _get(url: str, params: dict, timeout: float = 90) -> list[dict]:
    for attempt in range(4):
        r = httpx.get(url, params=params, timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else [data]
        time.sleep(3 * (attempt + 1))
    r.raise_for_status()
    return []


def _chunks(pts: list, n: int = 50):
    for i in range(0, len(pts), n):
        yield pts[i:i + n]


def solar_field(year: int | None = None) -> dict:
    """Yıllık yatay ışınım ızgarası: {"points": [[lat, lon, kWh/m²], ...], "min", "max", "year"}."""
    year = year or meteo.last_full_year()
    meteo.CACHE_DIR.mkdir(exist_ok=True)
    path = meteo.CACHE_DIR / f"field_solar_{meteo.HISTORY_MODEL}_{STEP}_{year}.json"
    lats, lons = grid()
    meta = {"lat0": LAT0, "lon0": LON0, "step": STEP, "nlat": len(lats), "nlon": len(lons), "clip": clip_rings()}
    if path.exists():
        return {**json.loads(path.read_text()), **meta}
    pts = land_points()
    out = []
    for chunk in _chunks(pts):
        res = _get(meteo.ARCHIVE_URL, {
            "latitude": ",".join(f"{p[0]}" for p in chunk), "longitude": ",".join(f"{p[1]}" for p in chunk),
            "start_date": f"{year}-01-01", "end_date": f"{year}-12-31",
            "daily": "shortwave_radiation_sum", "models": meteo.HISTORY_MODEL, "timezone": "GMT",
        })
        for (la, lo), r in zip(chunk, res):
            mj = np.array(r["daily"]["shortwave_radiation_sum"], dtype=float)  # MJ/m²/gün
            if np.isfinite(mj).sum() < 300:
                continue
            out.append([la, lo, round(float(np.nanmean(mj)) * 365 / 3.6, 1)])  # kWh/m²/yıl
    vals = [p[2] for p in out]
    field = {"points": out, "min": min(vals), "max": max(vals), "year": year}
    path.write_text(json.dumps(field))
    return {**field, **meta}


def wind_field() -> dict:
    """Şu anki 100 m rüzgârı: {"lats", "lons", "u", "v" (satır = enlem), "max", "time"}. u: doğuya, v: kuzeye (m/s)."""
    now = time.time()
    if _wind_cache and now - _wind_cache["at"] < WIND_TTL_S:
        return _wind_cache["field"]
    lats, lons = grid(0.15)
    pts = [(float(la), float(lo)) for la in lats for lo in lons]
    res: list[dict] = []
    for chunk in _chunks(pts, 100):
        res += _get(meteo.FORECAST_URL, {
            "latitude": ",".join(f"{p[0]}" for p in chunk), "longitude": ",".join(f"{p[1]}" for p in chunk),
            "current": "wind_speed_100m,wind_direction_100m", "wind_speed_unit": "ms", "timezone": "GMT",
        }, timeout=30)
    u = np.zeros((len(lats), len(lons)))
    v = np.zeros_like(u)
    for i, r in enumerate(res):
        c = r.get("current", {})
        sp, d = c.get("wind_speed_100m"), c.get("wind_direction_100m")
        if sp is None or d is None:
            continue
        a = math.radians(float(d))  # meteorolojik yön: rüzgârın GELDİĞİ yön
        u.flat[i], v.flat[i] = -sp * math.sin(a), -sp * math.cos(a)
    field = {"lats": lats.tolist(), "lons": lons.tolist(), "u": np.round(u, 2).tolist(),
             "v": np.round(v, 2).tolist(), "max": round(float(np.hypot(u, v).max()), 1),
             "time": (res[0].get("current", {}).get("time", "") if res else "")}
    _wind_cache.update(at=now, field=field)
    return field
