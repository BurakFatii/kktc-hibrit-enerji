"""Rüzgâr modeli — windpowerlib (oemof / Reiner Lemoine Institut).

Zincir:
  göbek yüksekliği hızı  10 m ve 100 m ölçümünden logaritmik ara değer
                         (windpowerlib "log_interpolation_extrapolation")
  hava yoğunluğu         barometrik model + doğrusal sıcaklık gradyanı
  güç                    windpowerlib.power_output.power_curve (yoğunluk düzeltmeli)

windpowerlib'in hazır türbin kütüphanesi MW ölçeklidir. Küçük türbinler için güç
eğrisi, kullanıcının katalog tablosundan ya da etiket hızlarından üretilir.
Rüzgâr YÖNÜ hesapları (yön ara değeri, sabit türbin kaybı, rüzgâr gülü) kütüphanede
olmadığı için burada yapılır.
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pandas as pd
from windpowerlib import ModelChain, WindTurbine, power_output

from .meteo import Weather
from .spec import SystemSpec

COMPASS16 = ["K", "KKD", "KD", "DKD", "D", "DGD", "GD", "GGD",
             "G", "GGB", "GB", "BGB", "B", "BKB", "KB", "KKB"]


def compass(deg: float) -> str:
    return COMPASS16[int(((deg % 360) + 11.25) // 22.5) % 16]


# ------------------------------------------------------------------ güç eğrisi
def parse_curve(text: str) -> list[tuple[float, float]] | None:
    """'3:0, 5:400, 8:1500' -> [(3,0), (5,400), (8,1500)] (W). Geçersizse None."""
    pts = []
    for part in (text or "").replace(";", ",").split(","):
        if ":" not in part:
            continue
        a, b = part.split(":", 1)
        try:
            pts.append((float(a.strip().replace(" ", "")), float(b.strip().replace(" ", ""))))
        except ValueError:
            return None
    return sorted(pts) if len(pts) >= 3 else None


@lru_cache(maxsize=16)
def _library_curve(turbine_type: str) -> tuple[pd.DataFrame, float]:
    """windpowerlib (OEDB) türbin güç eğrisi ve anma gücü (W)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = WindTurbine(turbine_type=turbine_type, hub_height=100)
    return t.power_curve.copy(), float(t.nominal_power)


@lru_cache(maxsize=64)
def _curve(rated_kw: float, ci: float, vr: float, co: float, table: str, turbine_type: str = "") -> pd.DataFrame:
    if turbine_type:
        pc, nominal_w = _library_curve(turbine_type)
        out = pc.copy()
        out["value"] = out["value"] / nominal_w * rated_kw * 1000.0  # anma gücüne ölçekle (filo)
        return out
    pts = parse_curve(table)
    if pts:
        v = [p[0] for p in pts]
        p = [p[1] for p in pts]
        last = max(v[-1], co)
        v += [last + 0.01, 40.0]
        p += [0.0, 0.0]
    else:
        v = list(np.arange(0.0, co, 0.5))
        frac = np.clip((np.array(v) ** 3 - ci ** 3) / max(vr ** 3 - ci ** 3, 1e-6), 0, 1)
        p = list(np.where(np.array(v) < ci, 0.0, frac) * rated_kw * 1000.0)
        v += [co, 40.0]
        p += [0.0, 0.0]
    return pd.DataFrame({"wind_speed": v, "value": p})


def power_curve_table(spec: SystemSpec) -> pd.DataFrame:
    return _curve(spec.wind_rated_kw, spec.wind_cut_in_ms, spec.wind_rated_ms,
                  spec.wind_cut_out_ms, spec.wind_power_curve.strip(), spec.wind_turbine_type.strip())


# ------------------------------------------------------------------ göbek yüksekliği
def hub_conditions(w: Weather, spec: SystemSpec) -> tuple[np.ndarray, np.ndarray]:
    """(göbek hızı m/s, göbek hava yoğunluğu kg/m³) — windpowerlib ModelChain."""
    idx = pd.RangeIndex(len(w))
    cols = pd.MultiIndex.from_tuples([
        ("wind_speed", 10), ("wind_speed", 100), ("temperature", 2),
        ("pressure", 0), ("roughness_length", 0)], names=["variable_name", "height"])
    weather = pd.DataFrame(np.column_stack([
        np.maximum(w.ws10, 0), np.maximum(w.ws100, 0), w.temp + 273.15,
        w.pressure * 100.0, np.full(len(w), 0.1)]), index=idx, columns=cols)
    turbine = WindTurbine(hub_height=max(spec.hub_height_m, 2.0),
                          nominal_power=max(spec.wind_rated_kw, 0.1) * 1000.0,
                          power_curve=power_curve_table(spec))
    mc = ModelChain(turbine, wind_speed_model="log_interpolation_extrapolation",
                    density_model="barometric", temperature_model="linear_gradient")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        v = mc.wind_speed_hub(weather)
        rho = mc.density_hub(weather)
    return np.clip(np.nan_to_num(np.asarray(v, dtype=float)), 0, None), np.asarray(rho, dtype=float)


def hub_direction(wd10: np.ndarray, wd100: np.ndarray, hub_m: float) -> np.ndarray:
    """10 m ve 100 m yönleri arasında yüksekliğe göre (dairesel) ara değer."""
    f = np.clip((np.log(max(hub_m, 1.0)) - np.log(10)) / (np.log(100) - np.log(10)), 0, 1)
    a, b = np.radians(wd10), np.radians(wd100)
    x = (1 - f) * np.cos(a) + f * np.cos(b)
    y = (1 - f) * np.sin(a) + f * np.sin(b)
    return np.degrees(np.arctan2(y, x)) % 360


def power_kw(v: np.ndarray, rho: np.ndarray | None, spec: SystemSpec) -> np.ndarray:
    """windpowerlib güç eğrisi (hava yoğunluğu düzeltmeli)."""
    if spec.wind_rated_kw <= 0:
        return np.zeros_like(np.asarray(v, dtype=float))
    pc = power_curve_table(spec)
    v_s = pd.Series(np.asarray(v, dtype=float))
    if rho is not None:
        out = power_output.power_curve(v_s, pc["wind_speed"], pc["value"],
                                       density=pd.Series(np.asarray(rho, dtype=float)),
                                       density_correction=True)
    else:
        out = power_output.power_curve(v_s, pc["wind_speed"], pc["value"])
    return np.clip(np.nan_to_num(np.asarray(out, dtype=float)), 0, None) / 1000.0


def misalignment_speed(v: np.ndarray, wind_from: np.ndarray, facing_deg: float) -> np.ndarray:
    """Sabit yönlü türbinde rotora dik düşen hız bileşeni."""
    return v * np.clip(np.cos(np.radians(wind_from - facing_deg)), 0, None)


def best_fixed_facing(v: np.ndarray, wind_from: np.ndarray, rho: np.ndarray | None,
                      spec: SystemSpec, step: int = 5) -> tuple[float, float]:
    """Yıllık enerjiyi en yükselten sabit yön. (yön_derece, enerji_kWh)."""
    best = (0.0, -1.0)
    for d in range(0, 360, step):
        e = float(power_kw(misalignment_speed(v, wind_from, d), rho, spec).sum())
        if e > best[1]:
            best = (float(d), e)
    return best


def wind_rose(v: np.ndarray, wind_from: np.ndarray,
              bins: tuple[float, ...] = (0, 3, 5, 8, 11, 100)) -> dict:
    """16 yön × hız aralığı saat yüzdeleri (rüzgâr gülü)."""
    sector = (((wind_from % 360) + 11.25) // 22.5).astype(int) % 16
    out = {}
    n = max(len(v), 1)
    for i in range(len(bins) - 1):
        m = (v >= bins[i]) & (v < bins[i + 1])
        label = f"{bins[i]:g}–{bins[i+1]:g} m/s" if bins[i + 1] < 100 else f"≥{bins[i]:g} m/s"
        out[label] = [float(((sector == s) & m).sum()) / n * 100 for s in range(16)]
    return out
