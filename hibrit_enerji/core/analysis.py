"""Konum analizi (harita), en iyi kurulum yönleri, senaryo karşılaştırması ve kapasite taraması."""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from . import solar, wind
from .config import GRID_EMISSION_KG_PER_KWH, SYSTEM_LIFETIME_YEARS
from .ems import EmsResult, simulate
from .load import load_kw, local_times
from .meteo import Weather
from .production import Orientation, compute
from .spec import SystemSpec

MONTHS_TR = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


# ---------------------------------------------------------------- yönler
def unit_spec(spec: SystemSpec) -> tuple[SystemSpec, float]:
    """1 kWp panel + kullanıcının türbini (yoksa 1 kW varsayılan eğri).

    Dönen ölçek, rüzgâr çıktısını 'kW anma gücü başına' çevirir. Kullanıcı katalog
    eğrisi girdiyse eğri ölçeklenmez; gerçek türbin çıktısı anma gücüne bölünür.
    """
    u = copy.copy(spec)
    u.panel_wp, u.panel_count = 1000.0, 1
    if spec.wind_rated_kw <= 0:
        u.wind_rated_kw, u.wind_power_curve = 1.0, ""
    return u, 1.0 / u.wind_rated_kw


def optimum_orientation(w: Weather, spec: SystemSpec, lat: float, lon: float) -> Orientation:
    """Sabit panel için yıllık AC üretimi en yükselten eğim/yön (pvlib, Perez)
    + sabit türbin için en iyi yön (windpowerlib)."""
    u, _ = unit_spec(spec)
    zen, az = solar.sun_position(w.time, lat, lon)

    def search(tilts: np.ndarray, azs: np.ndarray) -> tuple[float, float]:
        poa = solar.poa_fixed(w, zen, az, tilts[:, None, None], azs[None, :, None])
        e = solar.pv_power_kw(poa, w.temp, u).sum(axis=-1)
        i, j = np.unravel_index(int(np.argmax(e)), e.shape)
        return float(tilts[i]), float(azs[j])

    t0, a0 = search(np.arange(0.0, 61.0, 5.0), np.arange(120.0, 241.0, 10.0))  # kaba
    tilt, azim = search(np.arange(max(t0 - 4, 0), t0 + 5, 1.0),                 # ince
                        np.arange(a0 - 8, a0 + 9, 2.0))
    v, rho = wind.hub_conditions(w, u)
    d = wind.hub_direction(w.wd10, w.wd100, u.hub_height_m)
    facing, _ = wind.best_fixed_facing(v, d, rho, u)
    return Orientation(tilt_deg=tilt, azimuth_deg=azim, wind_facing_deg=facing, source="optimize")


# ---------------------------------------------------------------- metrikler
def complementarity(pv: np.ndarray, wk: np.ndarray) -> dict:
    """Güneş-rüzgâr tamamlayıcılığı VARSAYILMAZ; saatlik veriyle ölçülür."""
    corr = float(np.corrcoef(pv, wk)[0, 1]) if pv.std() > 0 and wk.std() > 0 else 0.0
    dark = pv < 0.01 * max(pv.max(), 1e-9)
    wind_total = wk.sum()
    night_share = float(wk[dark].sum() / wind_total * 100) if wind_total > 0 else 0.0
    return {"corr": corr, "wind_share_no_sun_pct": night_share}


def variability(prod: np.ndarray, times_utc: np.ndarray) -> dict:
    lt = local_times(times_utc)
    daily = np.bincount((lt.dayofyear.to_numpy() - 1), weights=prod)
    daily = daily[daily > 0] if (daily > 0).any() else daily
    mean_h = prod.mean()
    return {
        "hourly_cv": float(prod.std() / mean_h) if mean_h > 0 else 0.0,
        "daily_cv": float(daily.std() / daily.mean()) if daily.size and daily.mean() > 0 else 0.0,
        "zero_hours_pct": float((prod < 0.01 * max(prod.max(), 1e-9)).mean() * 100),
    }


def capex_usd(spec: SystemSpec, pv_on: bool = True, wind_on: bool = True, batt_on: bool = True) -> float:
    c = 0.0
    if pv_on:
        c += spec.pv_kwp * 1000 * spec.cost_pv_usd_per_wp
        if spec.pv_mount == "takipci":
            c += spec.pv_kwp * 1000 * spec.cost_tracker_usd_per_wp
    if wind_on:
        c += spec.wind_rated_kw * spec.cost_wind_usd_per_kw
    if batt_on:
        c += spec.battery_kwh * spec.cost_battery_usd_per_kwh
    return c


def summarize(r: EmsResult, spec: SystemSpec, times_utc: np.ndarray, capex: float) -> dict:
    load = r.load.sum()
    prod = r.prod.sum()
    imp = r.grid_import.sum()
    exp = r.export.sum()
    cur = r.curtail.sum()
    used = load - imp
    saving = used * spec.price_import_usd_kwh + exp * spec.price_export_usd_kwh
    years = len(r.prod) / 8760
    annual_saving = saving / years if years > 0 else 0.0
    co2 = (used + exp) * GRID_EMISSION_KG_PER_KWH / 1000 / max(years, 1e-9)
    net_cost = capex / SYSTEM_LIFETIME_YEARS + (imp * spec.price_import_usd_kwh
                                                 - exp * spec.price_export_usd_kwh) / max(years, 1e-9)
    v = variability(r.prod, times_utc)
    return {
        "production_kwh": prod, "load_kwh": load, "import_kwh": imp, "export_kwh": exp,
        "curtail_kwh": cur,
        "self_sufficiency_pct": used / load * 100 if load > 0 else 0.0,
        "renewable_use_pct": (prod - cur) / prod * 100 if prod > 0 else 0.0,
        "capex_usd": capex, "annual_saving_usd": annual_saving,
        "payback_years": capex / annual_saving if annual_saving > 0 else float("inf"),
        "co2_t_per_year": co2, "annual_net_cost_usd": net_cost, **v,
    }


# ---------------------------------------------------------------- senaryolar
SCENARIOS = [
    # (kod, ad, güneş, rüzgâr, batarya, strateji)
    ("S1", "Yalnızca güneş", True, False, False, "yok"),
    ("S2", "Yalnızca rüzgâr", False, True, False, "yok"),
    ("S3", "Güneş + rüzgâr (hibrit)", True, True, False, "yok"),
    ("S4a", "Hibrit + batarya (basit kural)", True, True, True, "basit"),
    ("S4", "Hibrit + batarya + akıllı yönetim", True, True, True, "akilli"),
]


@dataclass
class ScenarioRun:
    code: str
    name: str
    summary: dict
    monthly_prod: list[float]
    monthly_import: list[float]
    monthly_curtail: list[float]


def _monthly(x: np.ndarray, months: np.ndarray) -> list[float]:
    return [float(v) for v in np.bincount(months, weights=x, minlength=12)[:12]]


def run_scenarios(w: Weather, spec: SystemSpec, lat: float, lon: float,
                  orient: Orientation) -> list[ScenarioRun]:
    p = compute(w, spec, lat, lon, orient)
    load = load_kw(w.time, spec)
    months = local_times(w.time).month.to_numpy() - 1
    out = []
    for code, name, pv_on, wind_on, batt_on, strat in SCENARIOS:
        prod = (p.pv_kw if pv_on else 0) + (p.wind_kw if wind_on else 0)
        prod = np.asarray(prod, dtype=float) * np.ones(len(w))
        r = simulate(prod, load, spec, strategy=strat)
        s = summarize(r, spec, w.time, capex_usd(spec, pv_on, wind_on, batt_on))
        out.append(ScenarioRun(code, name, s, _monthly(prod, months),
                               _monthly(r.grid_import, months), _monthly(r.curtail, months)))
    return out


def capacity_sweep(w: Weather, spec: SystemSpec, lat: float, lon: float, orient: Orientation,
                   pv_opts=(0, 3, 5, 8, 10), wind_opts=(0, 1.5, 3, 5),
                   batt_opts=(0, 5, 10, 15)) -> list[dict]:
    """'Hangi kapasitede?' sorusu: kombinasyonları akıllı EMS ile yıllık simüle et."""
    unit, wscale = unit_spec(spec)
    p = compute(w, unit, lat, lon, orient)
    pv_1kwp, wind_1kw = p.pv_kw, p.wind_kw * wscale
    load = load_kw(w.time, spec)
    rows = []
    for kwp in pv_opts:
        for wkw in wind_opts:
            for bkwh in batt_opts:
                if kwp == 0 and wkw == 0:
                    continue
                s = copy.copy(spec)
                s.panel_count = 1 if kwp > 0 else 0
                s.panel_wp = kwp * 1000.0
                s.wind_rated_kw, s.battery_kwh = float(wkw), float(bkwh)
                prod = pv_1kwp * kwp + wind_1kw * wkw
                r = simulate(prod, load, s, strategy="akilli" if bkwh > 0 else "yok")
                m = summarize(r, s, w.time, capex_usd(s))
                rows.append({"pv_kwp": kwp, "wind_kw": wkw, "battery_kwh": bkwh, **m})
    rows.sort(key=lambda d: d["annual_net_cost_usd"])
    return rows


# ---------------------------------------------------------------- harita: konum analizi
def site_analysis(w: Weather, spec: SystemSpec, lat: float, lon: float) -> dict:
    opt = optimum_orientation(w, spec, lat, lon)
    unit, wscale = unit_spec(spec)
    fixed = compute(w, unit, lat, lon, opt, pv_mount="sabit", wind_yaw="otomatik")
    flat30 = compute(w, unit, lat, lon, Orientation(30, 180, opt.wind_facing_deg, "sabit"),
                     pv_mount="sabit", wind_yaw="sabit")
    track = compute(w, unit, lat, lon, opt, pv_mount="takipci", wind_yaw="sabit")

    y_fixed = float(fixed.pv_kw.sum())
    y_track = float(track.pv_kw.sum())
    y_flat30 = float(flat30.pv_kw.sum())
    wind_auto = float(fixed.wind_kw.sum())
    wind_fixed = float(track.wind_kw.sum())  # track çağrısı sabit yön + optimum yönle hesaplandı
    cf = wind_auto * wscale / len(w) * 100
    v_mean = float(fixed.hub_ws.mean())
    ghi_kwh = float(w.ghi.sum() / 1000)

    # Hakim yön: en çok enerji taşıyan 22.5° sektör. (Vektör ortalaması, iki yönlü
    # rüzgârda -örn. KD ve GB- birbirini götürüp anlamsız bir yön verir.)
    sector = (((fixed.hub_wd % 360) + 11.25) // 22.5).astype(int) % 16
    e_sec = np.bincount(sector, weights=fixed.wind_kw, minlength=16)
    order = np.argsort(e_sec)[::-1]
    prevailing = float(order[0] * 22.5) if e_sec.sum() > 0 else opt.wind_facing_deg
    # İkinci tepe en az %60 ise ve komşu sektör değilse rüzgâr iki yönlüdür.
    gap = min((order[1] - order[0]) % 16, (order[0] - order[1]) % 16)
    second = (float(order[1] * 22.5)
              if e_sec.sum() > 0 and e_sec[order[1]] >= 0.6 * e_sec[order[0]] and gap > 1 else None)

    comp = complementarity(fixed.pv_kw, fixed.wind_kw * wscale)

    # Isıl kayıp: aynı ışınımda hücre hep 25 °C olsaydı üretim ne olurdu? (pvlib Ross/NOCT)
    poa = solar.poa_fixed(w, fixed.sun_zen, fixed.sun_az, opt.tilt_deg, opt.azimuth_deg)
    temp_for_25 = 25.0 - (unit.noct_c - 20.0) / 800.0 * poa
    pv_25 = solar.pv_power_kw(poa, temp_for_25, unit)
    months_arr = local_times(w.time).month.to_numpy()
    jul = months_arr == 7
    thermal = (1 - fixed.pv_kw.sum() / pv_25.sum()) * 100 if pv_25.sum() > 0 else 0.0
    thermal_jul = (1 - fixed.pv_kw[jul].sum() / pv_25[jul].sum()) * 100 if pv_25[jul].sum() > 0 else 0.0
    t_summer_max = float(np.percentile(w.temp[(months_arr >= 6) & (months_arr <= 8)], 99)) \
        if ((months_arr >= 6) & (months_arr <= 8)).any() else float("nan")
    months = local_times(w.time).month.to_numpy() - 1
    lt_hour = local_times(w.time).hour.to_numpy()

    techniques = []
    techniques.append(_rate("Sabit güneş paneli (ekonomik)", y_fixed, 1500, 1250,
                            f"Optimum açıyla yılda ~{_tr(y_fixed)} kWh/kWp."))
    gain = (y_track / y_fixed - 1) * 100 if y_fixed > 0 else 0
    techniques.append({"name": "Güneş takipçili panel",
                       "status": "uygun" if gain >= 20 else "sınırlı",
                       "note": f"Sabite göre +%{gain:.0f} üretim; ek maliyetle karşılaştırılmalı."})
    techniques.append(_rate(f"Küçük rüzgâr türbini ({spec.hub_height_m:g} m)", v_mean, 5.0, 3.5,
                            f"Göbek yüksekliğinde ortalama {_tr(v_mean, 1)} m/s, kapasite faktörü %{cf:.0f}.",
                            unit_label="m/s"))
    hybrid_ok = comp["corr"] < 0.1 and comp["wind_share_no_sun_pct"] >= 35 and cf >= 8
    techniques.append({"name": "Güneş + rüzgâr hibrit",
                       "status": "uygun" if hybrid_ok else ("sınırlı" if cf >= 5 else "zayıf"),
                       "note": (f"Saatlik korelasyon {_tr(comp['corr'], 2)}; rüzgâr üretiminin "
                                f"%{comp['wind_share_no_sun_pct']:.0f}'i güneşin olmadığı saatlerde.")})
    techniques.append({"name": "Batarya depolama", "status": "uygun",
                       "note": "Güneş akşam düşer; akşam tüketim zirvesi için depolama gerekli."})

    return {
        "grid_lat": w.grid_lat, "grid_lon": w.grid_lon, "source": w.source,
        "ghi_kwh_m2": ghi_kwh,
        "opt_tilt": opt.tilt_deg, "opt_azimuth": opt.azimuth_deg,
        "yield_fixed": y_fixed, "yield_track": y_track, "yield_30_180": y_flat30,
        "tracker_gain_pct": gain,
        "wind_mean_hub": v_mean, "wind_mean_100": float(w.ws100.mean()), "wind_cf_pct": cf,
        "wind_prevailing": prevailing, "wind_prevailing_2": second, "wind_fixed_facing": opt.wind_facing_deg,
        # kW anma gücü başına yıllık üretim (takipçili/sabit panel satırlarının rüzgâr karşılığı)
        "yield_wind_fixed": wind_fixed * wscale, "yield_wind_auto": wind_auto * wscale,
        "wind_auto_gain_pct": (wind_auto / wind_fixed - 1) * 100 if wind_fixed > 0 else None,
        "corr": comp["corr"], "wind_share_no_sun_pct": comp["wind_share_no_sun_pct"],
        "thermal_loss_pct": thermal, "thermal_loss_jul_pct": thermal_jul,
        "summer_temp_p99": t_summer_max,
        "techniques": techniques,
        "monthly_pv_fixed": _monthly(fixed.pv_kw, months),
        "monthly_pv_track": _monthly(track.pv_kw, months),
        "monthly_wind": _monthly(fixed.wind_kw * wscale, months),
        "hour_month_wind": _hour_month(fixed.wind_kw * wscale, months, lt_hour),
        "hour_month_pv": _hour_month(fixed.pv_kw, months, lt_hour),
        "rose": wind.wind_rose(fixed.hub_ws, fixed.hub_wd),
        "orientation": opt,
    }


def _hour_month(x: np.ndarray, months: np.ndarray, hours: np.ndarray) -> list[list[float]]:
    """12 ay × 24 saat ortalama (ısı haritası)."""
    grid = np.zeros((12, 24))
    cnt = np.zeros((12, 24))
    np.add.at(grid, (months, hours), x)
    np.add.at(cnt, (months, hours), 1)
    return (grid / np.maximum(cnt, 1)).round(3).tolist()


def _rate(name: str, value: float, good: float, ok: float, note: str, unit_label: str = "") -> dict:
    status = "uygun" if value >= good else ("sınırlı" if value >= ok else "zayıf")
    return {"name": name, "status": status, "note": note}


def _tr(x: float, d: int = 0) -> str:
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")
