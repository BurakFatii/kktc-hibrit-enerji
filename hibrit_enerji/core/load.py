"""Tüketim profili: aylık fatura değerinden saatlik tüketim tahmini.

Gerçek sayaç verisi bağlanana kadar tipik KKTC profili kullanılır:
yaz klima, kış ısıtma etkisi aylık katsayılarla temsil edilir.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import LOCAL_TZ
from .spec import SystemSpec

_HOURLY = {
    "ev": [0.60, 0.50, 0.45, 0.45, 0.45, 0.50, 0.70, 0.90, 0.85, 0.75, 0.70, 0.70,
           0.75, 0.75, 0.75, 0.80, 0.95, 1.20, 1.50, 1.60, 1.55, 1.40, 1.10, 0.80],
    "isletme": [0.45, 0.40, 0.40, 0.40, 0.40, 0.45, 0.60, 0.90, 1.20, 1.35, 1.45, 1.50,
                1.50, 1.50, 1.45, 1.40, 1.30, 1.20, 1.10, 1.00, 0.90, 0.75, 0.60, 0.50],
}
_MONTHLY = np.array([1.10, 1.05, 0.90, 0.80, 0.85, 1.05, 1.30, 1.35, 1.15, 0.90, 0.90, 1.10])


def local_times(times_utc: np.ndarray) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(times_utc).tz_localize("UTC").tz_convert(LOCAL_TZ)


def load_kw(times_utc: np.ndarray, spec: SystemSpec) -> np.ndarray:
    lt = local_times(times_utc)
    shape = np.array(_HOURLY.get(spec.load_profile, _HOURLY["ev"]))
    shape = shape / shape.mean()
    month = _MONTHLY / _MONTHLY.mean()
    daily_mean_kwh = max(spec.monthly_kwh, 0) * 12 / 365
    return daily_mean_kwh / 24 * shape[lt.hour.to_numpy()] * month[lt.month.to_numpy() - 1]
