"""Güneş modeli — pvlib (Sandia/NREL kökenli, PV modellemede sektör standardı).

Zincir:
  güneş konumu        pvlib.solarposition.get_solarposition (NREL SPA)
  eğik yüzey ışınımı  pvlib.irradiance.get_total_irradiance (Perez gök modeli)
  geliş açısı kaybı   pvlib.iam.ashrae
  hücre sıcaklığı     pvlib.temperature.ross (panel etiketindeki NOCT ile)
  DC güç              pvlib.pvsystem.pvwatts_dc (etiket Pmax + sıcaklık katsayısı)
  sistem kayıpları    pvlib.pvsystem.pvwatts_losses
  AC güç              pvlib.inverter.pvwatts (inverter etiket verimi)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib

from .meteo import Weather
from .spec import SystemSpec

ALBEDO = 0.20
TRACKER_MAX_TILT = 80.0
# Kıbrıs için kayıp varsayımları (%): toz/kir 3, uyumsuzluk 2, kablo 2, bağlantı 0.5,
# ışıkla bozunma 1.5, etiket toleransı 1. Gölge ve kullanılabilirlik 0 (ayrı ele alınır).
SYSTEM_LOSSES_PCT = float(pvlib.pvsystem.pvwatts_losses(
    soiling=3, shading=0, snow=0, mismatch=2, wiring=2, connections=0.5, lid=1.5,
    nameplate_rating=1, age=0, availability=0))


def _index(times_utc: np.ndarray, shift_minutes: float) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(times_utc).tz_localize("UTC") + pd.Timedelta(minutes=shift_minutes)


def sun_position(times_utc: np.ndarray, lat: float, lon: float,
                 shift_minutes: float = -30.0) -> tuple[np.ndarray, np.ndarray]:
    """(görünür zenit, azimut) derece. Azimut kuzeyden saat yönünde (180 = güney).

    shift_minutes=-30: Open-Meteo radyasyonu önceki saatin ortalaması olduğu için
    güneş konumu saat ortasında hesaplanır.
    """
    sp = pvlib.solarposition.get_solarposition(_index(times_utc, shift_minutes), lat, lon)
    return sp["apparent_zenith"].to_numpy(), sp["azimuth"].to_numpy()


def _aux(w: Weather, zen: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    dni_extra = pvlib.irradiance.get_extra_radiation(_index(w.time, -30)).to_numpy()
    airmass = pvlib.atmosphere.get_relative_airmass(zen)
    return dni_extra, np.nan_to_num(airmass, nan=0.0)


def _effective(w: Weather, zen, az, tilt, surf_az) -> np.ndarray:
    """Panel yüzeyine düşen ve hücreye ulaşan ışınım (W/m²). tilt/surf_az dizi olabilir."""
    dni_extra, airmass = _aux(w, zen)
    poa = pvlib.irradiance.get_total_irradiance(
        tilt, surf_az, zen, az, w.dni, w.ghi, w.dhi, dni_extra=dni_extra, airmass=airmass,
        albedo=ALBEDO, model="perez")
    aoi = pvlib.irradiance.aoi(tilt, surf_az, zen, az)
    iam = np.nan_to_num(pvlib.iam.ashrae(aoi), nan=0.0)
    direct = np.nan_to_num(np.asarray(poa["poa_direct"], dtype=float))
    diffuse = np.nan_to_num(np.asarray(poa["poa_diffuse"], dtype=float))
    return np.clip(direct * iam + diffuse, 0, None)


def poa_fixed(w: Weather, zen, az, tilt, surf_az) -> np.ndarray:
    return _effective(w, zen, az, tilt, surf_az)


def poa_tracker(w: Weather, zen, az) -> np.ndarray:
    """Çift eksen takipçi: panel güneşe dik (eğim sınırı TRACKER_MAX_TILT, gece düz)."""
    tilt = np.where(zen < 90, np.minimum(zen, TRACKER_MAX_TILT), 0.0)
    return _effective(w, zen, az, tilt, az)


def pv_power_kw(poa_eff: np.ndarray, temp_c: np.ndarray, spec: SystemSpec) -> np.ndarray:
    """Panel ve inverter etiket değerleriyle AC güç (kW)."""
    pdc0 = spec.pv_kwp * 1000.0
    if pdc0 <= 0:
        return np.zeros_like(np.asarray(poa_eff, dtype=float))
    t_cell = pvlib.temperature.ross(poa_eff, temp_c, noct=spec.noct_c)
    pdc = pvlib.pvsystem.pvwatts_dc(poa_eff, t_cell, pdc0, spec.temp_coeff_pct / 100.0)
    pdc = np.asarray(pdc, dtype=float) * (1 - SYSTEM_LOSSES_PCT / 100.0)
    eta = spec.inverter_eff_pct / 100.0
    pac = pvlib.inverter.pvwatts(pdc, pdc0 * eta, eta_inv_nom=eta)
    return np.clip(np.nan_to_num(np.asarray(pac, dtype=float)), 0, None) / 1000.0


def rule_of_thumb_tilt(lat: float) -> float:
    """Geçmiş yıl verisi alınamazsa kullanılan yaklaşık en iyi sabit eğim."""
    return round(0.76 * abs(lat) + 3.1)
