"""Batarya + EV (V2H) mantığı."""
from __future__ import annotations


def update_soc(soc_kwh: float, capacity_kwh: float,
               production_kw: float, consumption_kw: float,
               dt_h: float = 1.0) -> tuple[float, float]:
    """Bir adım batarya güncelle. Dönen: (yeni_soc, şebekeden_çekilen_kw)."""
    net = (production_kw - consumption_kw) * dt_h  # +şarj, -deşarj
    new_soc = min(capacity_kwh, max(0.0, soc_kwh + net))
    grid_kw = 0.0
    if soc_kwh + net < 0:  # üretim + batarya yetmedi
        grid_kw = round(-(soc_kwh + net) / dt_h, 3)
    return round(new_soc, 3), grid_kw


def soc_percent(soc_kwh: float, capacity_kwh: float) -> float:
    if capacity_kwh <= 0:
        return 0.0
    return round(100.0 * max(0.0, min(1.0, soc_kwh / capacity_kwh)), 1)
