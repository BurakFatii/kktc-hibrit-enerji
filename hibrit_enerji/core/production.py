"""Bir konum + sistem tanımı için saatlik güneş ve rüzgâr üretimi."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import solar, wind
from .meteo import Weather
from .spec import SystemSpec


@dataclass
class Orientation:
    """Sabit sistemler için kurulum yönleri (takip/otomatik sistemlerde bilgi amaçlı)."""

    tilt_deg: float
    azimuth_deg: float
    wind_facing_deg: float
    source: str  # "kullanıcı" | "optimize" | "yaklaşık"


@dataclass
class Production:
    pv_kw: np.ndarray
    wind_kw: np.ndarray
    sun_zen: np.ndarray
    sun_az: np.ndarray
    hub_ws: np.ndarray
    hub_wd: np.ndarray
    hub_rho: np.ndarray

    @property
    def total_kw(self) -> np.ndarray:
        return self.pv_kw + self.wind_kw


def compute(w: Weather, spec: SystemSpec, lat: float, lon: float,
            orient: Orientation, pv_mount: str | None = None,
            wind_yaw: str | None = None) -> Production:
    mount = pv_mount or spec.pv_mount
    yaw = wind_yaw or spec.wind_yaw
    zen, az = solar.sun_position(w.time, lat, lon)
    if mount == "takipci":
        poa = solar.poa_tracker(w, zen, az)
    else:
        poa = solar.poa_fixed(w, zen, az, orient.tilt_deg, orient.azimuth_deg)
    pv = solar.pv_power_kw(poa, w.temp, spec)

    v, rho = wind.hub_conditions(w, spec)
    d = wind.hub_direction(w.wd10, w.wd100, spec.hub_height_m)
    if spec.wind_rated_kw <= 0:
        wk = np.zeros_like(v)
    elif yaw == "sabit":
        wk = wind.power_kw(wind.misalignment_speed(v, d, orient.wind_facing_deg), rho, spec)
    else:
        wk = wind.power_kw(v, rho, spec)
    return Production(pv_kw=pv, wind_kw=wk, sun_zen=zen, sun_az=az, hub_ws=v, hub_wd=d, hub_rho=rho)


def user_orientation(spec: SystemSpec, lat: float, optimum: Orientation | None) -> Orientation:
    """Ayarlar 'otomatik' ise optimum (yoksa yaklaşık) kullanılır, değilse kullanıcının girdisi."""
    tilt = spec.fixed_tilt_deg
    az = spec.fixed_azimuth_deg
    facing = spec.wind_fixed_dir_deg
    src = "kullanıcı"
    if spec.auto_orient:
        if optimum:
            tilt, az, src = optimum.tilt_deg, optimum.azimuth_deg, optimum.source
        else:
            tilt, az, src = solar.rule_of_thumb_tilt(lat), 180.0, "yaklaşık"
    if spec.auto_wind_dir and optimum:
        facing = optimum.wind_facing_deg
    return Orientation(tilt_deg=tilt, azimuth_deg=az, wind_facing_deg=facing, source=src)
