"""Üretim hesapları: güneş (takipçi) + rüzgar."""
from __future__ import annotations


def solar_power_kw(ghi_wm2: float, pv_kwp: float, tracking_gain: float = 0.25) -> float:
    """1000 W/m2 -> anma güç. Takipçi sabit panele göre kazanç ekler."""
    base = max(0.0, ghi_wm2) / 1000.0 * max(0.0, pv_kwp)
    return round(base * (1.0 + max(0.0, tracking_gain)), 3)


def wind_power_kw(wind_ms: float, rated_kw: float) -> float:
    """Basit güç eğrisi: 3 m/s cut-in, 12 m/s anma, 25 m/s cut-out."""
    if wind_ms < 3 or wind_ms >= 25:
        return 0.0
    if wind_ms >= 12:
        return round(rated_kw, 3)
    ratio = (wind_ms - 3) / (12 - 3)
    return round(rated_kw * (ratio ** 3), 3)


def total_power_kw(solar_kw: float, wind_kw: float) -> float:
    return round(max(0.0, solar_kw) + max(0.0, wind_kw), 3)
