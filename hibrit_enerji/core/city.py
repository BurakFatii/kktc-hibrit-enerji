"""Şehir (ilçe) ölçeği: seçilen noktanın bulunduğu ilçenin elektrik ihtiyacı ve onu
karşılayacak santralin o noktaya göre boyutlandırılması.

Sabit girdiler yalnızca resmî kaynak verileridir; geri kalan her şey konumdan türetilir:
  - İlçe nüfusu: 2011 KKTC Genel Nüfus ve Konut Sayımı (citypopulation.de)
  - KKTC toplam nüfus tahmini 2021: 390.745 (citypopulation.de)
  - KKTC yıllık elektrik tüketimi 2011: 1.254 GWh (EMO)  ->  kişi başı = 1.254 GWh / 286.257 kişi
  - Türbin: windpowerlib veritabanından Enercon E-82/2300 (yaygın 2,3 MW sınıfı)
Türetilenler: ilçe nüfusu (2011 payı × 2021 toplam), ilçe yıllık ihtiyacı, güneş/rüzgâr karışımı,
santral gücü, batarya enerjisi ve gücü, şebekeye verilebilecek güç (KKTC'nin geri kalanının yükü).
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from shapely import STRtree
from shapely.geometry import Point, shape

from . import load as loadmod
from .analysis import SCENARIOS, ScenarioRun, _monthly, capex_usd, summarize
from .ems import simulate
from .load import local_times
from .meteo import Weather
from .production import Orientation, compute
from .spec import SystemSpec

DATA = Path(__file__).resolve().parents[1] / "data" / "ilceler.geojson"

POP_2011 = {"Lefkoşa": 94_824, "Gazimağusa": 69_741, "Girne": 69_163,
            "Güzelyurt": 30_037, "İskele": 22_492}            # Güzelyurt = Lefke dahil (2011 sınırları)
TOTAL_POP_2011 = 286_257
TOTAL_POP_2021_EST = 390_745
CONSUMPTION_2011_KWH = 1_254e6
PER_CAPITA_KWH = CONSUMPTION_2011_KWH / TOTAL_POP_2011        # ≈ 4.381 kWh/kişi/yıl
CITY_TURBINE = "E-82/2300"
CITY_TURBINE_KW = 2300.0
CITY_HUB_M = 78.0
SOURCES = ("Nüfus: 2011 KKTC sayımı ve 2021 tahmini (citypopulation.de); tüketim: 2011 KKTC 1.254 GWh (EMO); "
           "türbin: Enercon E-82/2300 (windpowerlib).")


# ------------------------------------------------------------------ ilçe ve ihtiyaç
@lru_cache(maxsize=1)
def _districts():
    feats = json.loads(DATA.read_text())["features"]
    geoms = [shape(f["geometry"]) for f in feats]
    return STRtree(geoms), geoms, [f["properties"] for f in feats]


def district_of(lat: float, lon: float) -> dict:
    """Noktanın ilçesi; ilçe dışında (deniz vb.) ise en yakın ilçe."""
    tree, geoms, props = _districts()
    pt = Point(lon, lat)
    for i in tree.query(pt):
        if geoms[int(i)].contains(pt):
            return props[int(i)]
    return props[int(tree.nearest(pt))]


def need(ilce: str) -> dict:
    share = POP_2011[ilce] / TOTAL_POP_2011
    pop = share * TOTAL_POP_2021_EST
    return {"pop": pop, "annual_kwh": pop * PER_CAPITA_KWH, "share": share}


def _profile_load(times_utc: np.ndarray, annual_kwh: float) -> np.ndarray:
    """Şehir yükü: konut (akşam yoğun) ve ticari (gündüz yoğun) profillerinin ortalaması."""
    s = SystemSpec(monthly_kwh=annual_kwh / 12)
    a = loadmod.load_kw(times_utc, SystemSpec(**{**s.to_dict(), "load_profile": "ev"}))
    b = loadmod.load_kw(times_utc, SystemSpec(**{**s.to_dict(), "load_profile": "isletme"}))
    return (a + b) / 2


def city_load_kw(times_utc: np.ndarray, ilce: str) -> np.ndarray:
    return _profile_load(times_utc, need(ilce)["annual_kwh"])


def rest_of_country_kw(times_utc: np.ndarray, ilce: str) -> np.ndarray:
    """Şehrin fazlası şebeke üzerinden diğer ilçelere gider: sınır = KKTC'nin geri kalanının yükü."""
    total = _profile_load(times_utc, TOTAL_POP_2021_EST * PER_CAPITA_KWH)
    return np.clip(total - city_load_kw(times_utc, ilce), 0, None)


# ------------------------------------------------------------------ birim üretim
def city_spec(base: SystemSpec, pv_kwp: float = 1.0, wind_kw: float = 1.0, batt_kwh: float = 0.0,
              batt_kw: float = 0.0) -> SystemSpec:
    s = copy.copy(base)
    s.pv_mount = "sabit"
    s.panel_wp, s.panel_count = pv_kwp * 1000.0, 1 if pv_kwp > 0 else 0
    s.wind_rated_kw, s.wind_turbine_type, s.hub_height_m, s.wind_yaw = wind_kw, CITY_TURBINE, CITY_HUB_M, "otomatik"
    s.battery_kwh, s.battery_power_kw = batt_kwh, batt_kw
    s.battery_dod_pct = 100.0  # santral bataryası: kullanılabilir enerji olarak boyutlandırılır
    s.cost_pv_usd_per_wp = base.cost_pv_utility_usd_per_wp
    s.cost_wind_usd_per_kw = base.cost_wind_utility_usd_per_kw
    s.cost_battery_usd_per_kwh = base.cost_battery_utility_usd_per_kwh
    return s


def unit_series(w: Weather, base: SystemSpec, lat: float, lon: float, orient: Orientation):
    """O noktada 1 kWp sabit güneş (en iyi açı) ve 1 kW rüzgâr (E-82 filosu) saatlik üretimi."""
    p = compute(w, city_spec(base), lat, lon, orient)
    return p.pv_kw, p.wind_kw


# ------------------------------------------------------------------ tasarım
@dataclass
class Design:
    pv_kwp: float
    wind_kw: float
    batt_kwh: float
    batt_kw: float
    wind_share: float          # yıllık enerjide rüzgâr payı
    direct_cover: float        # bataryasız saatlik karşılama oranı
    solar_only_kwp: float | None
    wind_only_kw: float | None
    note: str


def design(load: np.ndarray, pv1: np.ndarray, w1: np.ndarray, wind_ok: bool, solar_ok: bool) -> Design | None:
    """Yıllık enerjide ihtiyacın %100'ünü üretecek santral; güneş/rüzgâr oranı saatlik açığı
    en aza indirecek şekilde seçilir. Konum bir kaynağa uygun değilse o kaynak kullanılmaz."""
    annual = load.sum()
    e_pv, e_w = pv1.sum(), w1.sum()
    can_pv = solar_ok and e_pv > 0
    can_w = wind_ok and e_w > 0
    if not (can_pv or can_w):
        return None
    shares = np.linspace(0, 1, 21)
    if not can_w:
        shares = np.array([0.0])
    elif not can_pv:
        shares = np.array([1.0])
    best = None
    for sh in shares:
        kwp = (1 - sh) * annual / e_pv if can_pv else 0.0
        kw = sh * annual / e_w if can_w else 0.0
        prod = pv1 * kwp + w1 * kw
        cover = np.minimum(prod, load).sum() / annual
        if best is None or cover > best[0] + 1e-9:
            best = (cover, sh, kwp, kw, prod)
    cover, sh, kwp, kw, prod = best
    # Batarya: tipik (medyan) günde fazlanın geceye taşınabilecek kısmı; güç: saatlik açığın %95'lik dilimi
    days = local_times_days(len(load))
    surplus = np.bincount(days, weights=np.clip(prod - load, 0, None))
    deficit = np.bincount(days, weights=np.clip(load - prod, 0, None))
    batt_kwh = float(np.median(np.minimum(surplus, deficit)))
    batt_kw = float(np.percentile(np.clip(load - prod, 0, None), 95))
    note = ("Rüzgâr bu noktada uygun değil; yalnızca güneş." if not can_w and wind_ok is False else
            "Güneş bu noktada uygun değil; yalnızca rüzgâr." if not can_pv and solar_ok is False else "")
    return Design(pv_kwp=kwp, wind_kw=kw, batt_kwh=batt_kwh, batt_kw=batt_kw, wind_share=sh, direct_cover=cover,
                  solar_only_kwp=annual / e_pv if can_pv else None,
                  wind_only_kw=annual / e_w if can_w else None, note=note)


def local_times_days(n: int) -> np.ndarray:
    return np.arange(n) // 24


# ------------------------------------------------------------------ senaryolar (şehir ölçeği)
def city_scenarios(w: Weather, base: SystemSpec, d: Design, pv1, w1, load, limit) -> list[ScenarioRun]:
    """S1 güneş, S2 rüzgâr: her biri tek başına ihtiyaca göre boyutlu. S3 hibrit (en iyi karışım),
    S4a/S4 hibrit + batarya (boyut tasarımdan)."""
    months = local_times(w.time).month.to_numpy() - 1
    plans = {
        "S1": (d.solar_only_kwp or 0.0, 0.0, 0.0, 0.0),
        "S2": (0.0, d.wind_only_kw or 0.0, 0.0, 0.0),
        "S3": (d.pv_kwp, d.wind_kw, 0.0, 0.0),
        "S4a": (d.pv_kwp, d.wind_kw, d.batt_kwh, d.batt_kw),
        "S4": (d.pv_kwp, d.wind_kw, d.batt_kwh, d.batt_kw),
    }
    out = []
    for code, name, *_rest, strat in SCENARIOS:
        kwp, kw, bk, bp = plans[code]
        s = city_spec(base, kwp, kw, bk, bp)
        prod = pv1 * kwp + w1 * kw
        r = simulate(prod, load, s, strategy=strat if bk > 0 else "yok", export_limit=limit)
        summ = summarize(r, s, w.time, capex_usd(s, kwp > 0, kw > 0, bk > 0))
        out.append(ScenarioRun(code, name, summ, _monthly(prod, months),
                               _monthly(r.grid_import, months), _monthly(r.curtail, months)))
    return out


def city_sweep(w: Weather, base: SystemSpec, d: Design, pv1, w1, load, limit) -> list[dict]:
    """'Hangi kapasitede?': tasarımın katları (yalnızca konumun uygun olduğu kaynaklar)."""
    pv_f = [0.5, 0.75, 1.0, 1.25, 1.5] if d.pv_kwp > 0 else [0.0]
    w_f = [0.0, 0.5, 1.0, 1.5] if d.wind_kw > 0 else [0.0]
    b_f = [0.0, 0.5, 1.0, 2.0]
    rows = []
    for fp in pv_f:
        for fw in w_f:
            for fb in b_f:
                kwp, kw = d.pv_kwp * fp, d.wind_kw * fw
                if kwp == 0 and kw == 0:
                    continue
                bk, bp = d.batt_kwh * fb, d.batt_kw * fb
                s = city_spec(base, kwp, kw, bk, bp)
                r = simulate(pv1 * kwp + w1 * kw, load, s, strategy="akilli" if bk > 0 else "yok",
                             export_limit=limit)
                m = summarize(r, s, w.time, capex_usd(s, kwp > 0, kw > 0, bk > 0))
                rows.append({"pv_kwp": kwp, "wind_kw": kw, "battery_kwh": bk, **m})
    rows.sort(key=lambda r: r["annual_net_cost_usd"])
    return rows
