"""Sayfaların ihtiyaç duyduğu hesap paketleri.

Burada yalnızca core/ çağrılır ve sonuçlar ekrana hazır metin/figüre çevrilir.
Reflex state'i bu fonksiyonları thread içinde çağırır (arayüz donmaz).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import charts
from .core import city, meteo, restrictions, solar
from .core.analysis import _hour_month, optimum_orientation, site_analysis
from .core.config import CANDIDATE_REGIONS, LOCAL_TZ
from .core.ems import MODES, simulate
from .core.load import load_kw, local_times
from .core.production import Orientation, compute, user_orientation
from .core.spec import SystemSpec
from .core.wind import compass, misalignment_speed, power_kw

_opt_cache: dict[tuple, Orientation] = {}


def _n(x: float, d: int = 0) -> str:
    """Türkçe sayı biçimi: 12.345,6"""
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def optimum_for(spec: SystemSpec, lat: float, lon: float) -> Orientation | None:
    key = (*meteo.snap_key(lat, lon), round(lat, 2), spec.hub_height_m, spec.temp_coeff_pct)
    if key in _opt_cache:
        return _opt_cache[key]
    try:
        w = meteo.fetch_history_year(lat, lon)
    except Exception:
        return None
    o = optimum_orientation(w, spec, lat, lon)
    _opt_cache[key] = o
    return o


def _strategy(spec: SystemSpec) -> str:
    return "akilli" if spec.battery_usable_kwh > 0 else "yok"


# =================================================================== ANA SAYFA
def daily_energy(w, p, load, r) -> list[dict]:
    """Yerel takvim günü bazında: tüketim nereden karşılandı, ne kadar üretildi."""
    lt = local_times(w.time) - pd.Timedelta(hours=1)  # saat sonu damgası -> ait olduğu gün
    days = lt.normalize().tz_localize(None)
    out = []
    for d in sorted(set(days)):
        m = np.asarray(days == d)
        if m.sum() < 20:  # yarım günleri atla
            continue
        ld, pv, wd = load[m].sum(), p.pv_kw[m].sum(), p.wind_kw[m].sum()
        imp, dis, exp = r.grid_import[m].sum(), r.discharge[m].sum(), r.export[m].sum()
        direct = max(ld - imp - dis, 0.0)
        share_pv = pv / (pv + wd) if pv + wd > 0 else 1.0
        out.append({"date": d, "load": ld, "pv": pv, "wind": wd, "imp": imp, "exp": exp, "dis": dis,
                    "pv_used": direct * share_pv, "wind_used": direct * (1 - share_pv)})
    return out


def home_snapshot(spec: SystemSpec, lat: float, lon: float) -> dict:
    w = meteo.fetch_forecast(lat, lon)
    opt = optimum_for(spec, lat, lon)
    orient = user_orientation(spec, lat, opt)
    p = compute(w, spec, lat, lon, orient)
    load = load_kw(w.time, spec)
    r = simulate(p.total_kw, load, spec, strategy=_strategy(spec), with_modes=True)
    i = meteo.current_index(w)
    lt = local_times(w.time)
    title, text = MODES[r.modes[i]]

    flows = [
        {"label": "Tesis tüketimi (tahmini)", "value": f"{_n(load[i], 2)} kW"},
    ]
    if r.charge[i] > 0.01:
        flows.append({"label": "Bataryaya giden", "value": f"+{_n(r.charge[i], 2)} kW"})
    if r.discharge[i] > 0.01:
        flows.append({"label": "Bataryadan gelen", "value": f"{_n(r.discharge[i], 2)} kW"})
    if r.export[i] > 0.01:
        flows.append({"label": "Şebekeye verilen", "value": f"{_n(r.export[i], 2)} kW"})
    if r.grid_import[i] > 0.01:
        flows.append({"label": "Şebekeden çekilen", "value": f"{_n(r.grid_import[i], 2)} kW"})
    if r.curtail[i] > 0.01:
        flows.append({"label": "Kısılan üretim", "value": f"{_n(r.curtail[i], 2)} kW"})

    # Önümüzdeki 24 saat
    j = slice(i + 1, min(i + 25, len(w)))
    outlook = [f"Üretim ~{_n(p.total_kw[j].sum(), 1)} kWh (güneş {_n(p.pv_kw[j].sum(), 1)}, "
               f"rüzgâr {_n(p.wind_kw[j].sum(), 1)}); tüketim ~{_n(load[j].sum(), 1)} kWh."]
    if r.usable_kwh > 0:
        soc = r.soc_pct()[j]
        full = np.where(soc >= 99)[0]
        if r.soc_pct()[i] >= 99:
            outlook.append("Batarya şu an dolu.")
        elif full.size:
            # Zaman damgası saat SONU; dolma o saatin içinde gerçekleşir.
            outlook.append(f"Batarya {lt[i + 1 + full[0]]:%H}:00'e kadar dolacak.")
        outlook.append(f"Batarya en düşük %{soc.min():.0f} seviyesine inecek.")
    if r.export[j].sum() > 0.05:
        outlook.append(f"Şebekeye ~{_n(r.export[j].sum(), 1)} kWh verilecek "
                       f"(limit {_n(spec.export_limit_kw, 1)} kW).")
    if r.grid_import[j].sum() > 0.05:
        outlook.append(f"Şebekeden ~{_n(r.grid_import[j].sum(), 1)} kWh çekilmesi gerekecek.")
    if r.curtail[j].sum() > 0.05:
        outlook.append(f"~{_n(r.curtail[j].sum(), 1)} kWh üretim kısılacak (depo ve limit dolu).")

    # Kurulum yönü (anlık)
    zen, saz = p.sun_zen[i], p.sun_az[i]
    if spec.pv_mount == "takipci":
        pv_dir = (f"Takipçi şu an {compass(saz)} ({saz:.0f}°) yönüne, {90 - zen:.0f}° yüksekliğe dönük."
                  if zen < 90 else "Gece: takipçi sabah için doğuya park etti.")
    else:
        src = {"optimize": "geçmiş yıl verisiyle bu konum için optimize edildi",
               "yaklaşık": "yaklaşık değer (geçmiş veri alınamadı)",
               "kullanıcı": "Ayarlar'da sizin girdiğiniz değer"}[orient.source]
        pv_dir = (f"Paneller {compass(orient.azimuth_deg)} ({orient.azimuth_deg:.0f}°) yönüne, "
                  f"{orient.tilt_deg:.0f}° eğimle sabit — {src}.")
        if orient.source == "kullanıcı" and opt and (abs(opt.tilt_deg - orient.tilt_deg) > 5
                                                    or abs(opt.azimuth_deg - orient.azimuth_deg) > 10):
            pv_dir += f" Önerilen: {compass(opt.azimuth_deg)} {opt.tilt_deg:.0f}°."
    v, wd = p.hub_ws[i], p.hub_wd[i]
    if spec.wind_rated_kw <= 0:
        wind_dir = "Rüzgâr türbini tanımlı değil (Ayarlar)."
    elif spec.wind_yaw == "otomatik":
        wind_dir = (f"Rüzgâr {compass(wd)} ({wd:.0f}°) yönünden {_n(v, 1)} m/s esiyor; "
                    f"rotor otomatik olarak rüzgâra dönük.")
    else:
        rho = np.array([p.hub_rho[i]])
        full_p = float(power_kw(np.array([v]), rho, spec)[0])
        fixed_p = float(power_kw(misalignment_speed(np.array([v]), np.array([wd]),
                                                    orient.wind_facing_deg), rho, spec)[0])
        loss = (1 - fixed_p / full_p) * 100 if full_p > 0 else 0
        diff = abs((wd - orient.wind_facing_deg + 180) % 360 - 180)
        wind_dir = (f"Rotor {compass(orient.wind_facing_deg)} ({orient.wind_facing_deg:.0f}°) yönüne sabit; "
                    f"rüzgâr {compass(wd)} yönünden geliyor (açı {diff:.0f}°), anlık kayıp ~%{loss:.0f}.")

    # ---- görsel göstergeler için sayılar (hepsi metin; UI'da % / derece olarak kullanılır)
    def pct(x: float) -> str:
        return f"{max(0.0, min(100.0, float(x))):.1f}"

    eps = 0.02
    soc_i = float(r.soc_pct()[i]) if r.usable_kwh > 0 else 0.0
    pv_cap = max(spec.pv_kwp * spec.inverter_eff_pct / 100, 1e-6)
    j24 = slice(i + 1, min(i + 25, len(w)))
    load_peak = max(float(load[j24].max()) if load[j24].size else 0.0, float(load[i]), 1e-6)
    elev = 90.0 - float(zen)
    theta = np.radians(np.clip((float(saz) - 90.0) / 180.0, 0, 1) * 180.0)
    sun_x = 100 - 90 * np.cos(theta)
    sun_y = 100 - 88 * np.sin(np.radians(max(elev, 0.0)))
    if r.export[i] > eps:
        grid_text = f"→ {_n(r.export[i], 2)} kW"
    elif r.grid_import[i] > eps:
        grid_text = f"← {_n(r.grid_import[i], 2)} kW"
    else:
        grid_text = "0 kW"
    if r.charge[i] > eps:
        batt_text = f"%{soc_i:.0f} ↑"
    elif r.discharge[i] > eps:
        batt_text = f"%{soc_i:.0f} ↓"
    else:
        batt_text = f"%{soc_i:.0f}" if r.usable_kwh > 0 else "—"
    short = {"sarj": "DEPOLA", "sarj_ver": "DEPOLA + VER", "ver": "VER", "ev_sarj": "ARAÇ",
             "kisit": "KISIT", "besle": "BATARYA", "v2h": "V2H", "cek": "ŞEBEKE", "denge": "DENGE"}
    cat = {"sarj": "gain", "sarj_ver": "gain", "ver": "gain", "ev_sarj": "gain", "denge": "gain",
           "besle": "use", "v2h": "use", "cek": "grid", "kisit": "curt"}
    peak = max(float(p.total_kw[j24].max()) if p.total_kw[j24].size else 0.0, 1e-6)
    strip = []
    for k in range(j24.start, j24.stop):
        hh = lt[k] - pd.Timedelta(hours=1)  # saat sonu damgası -> saat başı etiketi
        strip.append({
            "h": pct(p.total_kw[k] / peak * 100), "soc": pct(r.soc_pct()[k]) if r.usable_kwh > 0 else "0",
            "cat": cat[r.modes[k]], "lbl": f"{hh:%H}" if hh.hour % 6 == 0 else "",
            "tip": f"{hh:%H}:00 · üretim {_n(p.total_kw[k], 1)} kW · {MODES[r.modes[k]][0].lower()}",
        })
    tilt_now = orient.tilt_deg if spec.pv_mount != "takipci" else float(np.clip(zen, 0, 80)) if zen < 90 else 0.0
    facing = float(wd) if spec.wind_yaw == "otomatik" else orient.wind_facing_deg
    visual = {
        "pv_pct": pct(p.pv_kw[i] / pv_cap * 100),
        "wind_pct": pct(p.wind_kw[i] / spec.wind_rated_kw * 100) if spec.wind_rated_kw > 0 else "0",
        "load_pct": pct(load[i] / load_peak * 100),
        "soc_pct": pct(soc_i), "soc_low": "1" if soc_i < 20 else "0",
        "on_pv": "1" if p.pv_kw[i] > eps else "0", "on_wind": "1" if p.wind_kw[i] > eps else "0",
        "on_load": "1" if load[i] > eps else "0",
        "on_chg": "1" if r.charge[i] > eps else "0", "on_dis": "1" if r.discharge[i] > eps else "0",
        "on_exp": "1" if r.export[i] > eps else "0", "on_imp": "1" if r.grid_import[i] > eps else "0",
        "grid_text": grid_text, "batt_text": batt_text, "mode_short": short[r.modes[i]],
        "mount": spec.pv_mount, "tilt": f"{tilt_now:.0f}",
        "tilt_label": f"{tilt_now:.0f}° · {compass(orient.azimuth_deg if spec.pv_mount != 'takipci' else saz)}",
        "sun_up": "1" if elev > 0 else "0", "sun_x": f"{sun_x:.1f}", "sun_y": f"{sun_y:.1f}",
        "sun_label": (f"güneş yüksekliği {elev:.0f}° · {compass(saz)}" if elev > 0 else "güneş ufkun altında"),
        "wind_deg": f"{float(wd):.0f}", "wind_ms": _n(v, 1),
        "facing_deg": f"{facing:.0f}", "wind_on": "1" if spec.wind_rated_kw > 0 else "0",
        "yaw": spec.wind_yaw,
        "prod24": _n(p.total_kw[j24].sum(), 1), "load24": _n(load[j24].sum(), 1),
        "cover24": pct(min(p.total_kw[j24].sum() / max(load[j24].sum(), 1e-6), 1) * 100),
    }

    # ---- bugün: tüketim nereden karşılandı (yığılı bar) + günlük kazanç
    today = pd.Timestamp(lt[i] - pd.Timedelta(hours=1)).normalize().tz_localize(None)
    td = next((d for d in daily_energy(w, p, load, r) if d["date"] == today), None)
    if td and td["load"] > 0:
        L = td["load"]
        seg = {"t_pv": td["pv_used"], "t_wind": td["wind_used"], "t_batt": td["dis"], "t_grid": td["imp"]}
        visual.update({k + "_pct": pct(v / L * 100) for k, v in seg.items()})
        visual.update({k: _n(v, 1) for k, v in seg.items()})
        visual.update({
            "t_load": _n(L, 1), "t_pv_gen": _n(td["pv"], 1), "t_wind_gen": _n(td["wind"], 1),
            "t_exp": _n(td["exp"], 1),
            "t_green_pct": pct((L - td["imp"]) / L * 100),
            "t_green": f"%{(L - td['imp']) / L * 100:.0f}",
        })
    else:
        visual.update({k: "0" for k in ("t_pv_pct", "t_wind_pct", "t_batt_pct", "t_grid_pct", "t_green_pct")})
        visual.update({k: "—" for k in ("t_pv", "t_wind", "t_batt", "t_grid", "t_load", "t_pv_gen",
                                         "t_wind_gen", "t_exp", "t_green")})

    return {
        **visual, "strip": strip,
        "pv_now": _n(p.pv_kw[i], 2), "wind_now": _n(p.wind_kw[i], 2),
        "load_now": _n(load[i], 2),
        "soc_now": f"%{r.soc_pct()[i]:.0f}" if r.usable_kwh > 0 else "—",
        "mode_title": title, "mode_text": text, "flows": flows, "outlook": outlook,
        "pv_dir": pv_dir, "wind_dir": wind_dir,
        "weather": (f"{_n(w.temp[i], 1)}°C · güneş ışınımı {_n(w.ghi[i])} W/m² · "
                    f"rüzgâr {_n(w.ws10[i], 1)} m/s (10 m)"),
        "updated": pd.Timestamp.now(tz=LOCAL_TZ).strftime("%d.%m.%Y %H:%M"),
    }


# =================================================================== HARİTA
def site_report(spec: SystemSpec, lat: float, lon: float) -> dict:
    w = meteo.fetch_history_year(lat, lon)
    s = site_analysis(w, spec, lat, lon)
    try:
        f = meteo.fetch_forecast(lat, lon)
        k = meteo.current_index(f)
        live = (f"Şu an: {_n(f.temp[k], 1)}°C · ışınım {_n(f.ghi[k])} W/m² · rüzgâr "
                f"{_n(f.ws100[k], 1)} m/s (100 m), {compass(f.wd100[k])} yönünden")
    except Exception:
        live = "Anlık tahmin alınamadı."

    solar_rows = [
        {"k": "Yıllık güneş ışınımı (yatay)", "v": f"{_n(s['ghi_kwh_m2'])} kWh/m²"},
        {"k": "Sabit panel için en iyi eğim", "v": f"{s['opt_tilt']:.0f}°"},
        {"k": "Sabit panel için en iyi yön", "v": f"{compass(s['opt_azimuth'])} ({s['opt_azimuth']:.0f}°)"},
        {"k": "Sabit panel üretimi", "v": f"{_n(s['yield_fixed'])} kWh/kWp/yıl"},
        {"k": "Takipçili panel üretimi", "v": f"{_n(s['yield_track'])} kWh/kWp/yıl (+%{s['tracker_gain_pct']:.0f})"},
        {"k": "Isıl kayıp: yıllık / Temmuz", "v": f"%{_n(s['thermal_loss_pct'], 1)} / %{_n(s['thermal_loss_jul_pct'], 1)}"},
        {"k": "Yaz sıcaklığı (en sıcak %1 saat)", "v": f"≥{_n(s['summer_temp_p99'], 0)} °C"},
    ]
    wind_rows = [
        {"k": f"Ortalama hız ({spec.hub_height_m:g} m göbek)", "v": f"{_n(s['wind_mean_hub'], 1)} m/s"},
        {"k": "Ortalama hız (100 m)", "v": f"{_n(s['wind_mean_100'], 1)} m/s"},
        {"k": "Kapasite faktörü (türbininiz)", "v": f"%{_n(s['wind_cf_pct'], 1)}"},
        {"k": "Enerji taşıyan hakim yön",
         "v": (f"{compass(s['wind_prevailing'])} ve {compass(s['wind_prevailing_2'])} (iki yönlü)"
               if s["wind_prevailing_2"] is not None
               else f"{compass(s['wind_prevailing'])} ({s['wind_prevailing']:.0f}°)")},
        {"k": "Sabit türbin için en iyi yön", "v": f"{compass(s['wind_fixed_facing'])} ({s['wind_fixed_facing']:.0f}°)"},
        {"k": "Sabit yönlü türbin üretimi", "v": f"{_n(s['yield_wind_fixed'])} kWh/kW/yıl"},
        {"k": "Otomatik yönlenen türbin üretimi",
         "v": f"{_n(s['yield_wind_auto'])} kWh/kW/yıl"
              + (f" (+%{s['wind_auto_gain_pct']:.0f})" if s["wind_auto_gain_pct"] is not None else "")},
    ]
    hybrid_rows = [
        {"k": "Saatlik güneş–rüzgâr korelasyonu", "v": ("+" if s['corr'] >= 0 else "−") + _n(abs(s['corr']), 2)},
        {"k": "Rüzgâr enerjisinin güneşsiz saatlerdeki payı", "v": f"%{s['wind_share_no_sun_pct']:.0f}"},
    ]

    extra_kwh = s["yield_track"] - s["yield_fixed"]
    extra_cost = spec.cost_tracker_usd_per_wp * 1000
    pb = extra_cost / (extra_kwh * spec.price_import_usd_kwh) if extra_kwh > 0 else float("inf")
    advice = [
        (f"Ekonomik paket: panelleri {compass(s['opt_azimuth'])} ({s['opt_azimuth']:.0f}°) yönüne "
         f"{s['opt_tilt']:.0f}° eğimle sabitleyin."),
        (f"Takipçili paket: bu noktada kWp başına yılda +{_n(extra_kwh)} kWh; takipçinin ek maliyeti "
         f"(~{_n(extra_cost)} $/kWp) yaklaşık {_n(pb, 1)} yılda kendini öder."),
    ]
    if spec.wind_rated_kw > 0:
        advice.append(f"Sabit türbin kullanılacaksa rotoru {compass(s['wind_fixed_facing'])} "
                      f"({s['wind_fixed_facing']:.0f}°) yönüne bakacak şekilde sabitleyin; otomatik "
                      + (f"yönlenen türbin bu noktada %{s['wind_auto_gain_pct']:.0f} daha fazla üretir. "
                         if s["wind_auto_gain_pct"] is not None else "yönlenen türbin çok daha fazla üretir. ")
                      + "Yön ayarı istemeyen düşük bütçeli alternatif: dikey eksenli (VAWT) türbin.")
    def pct(x: float) -> str:
        return f"{max(0.0, min(100.0, float(x))):.1f}"

    rc = restrictions.check(lat, lon)
    techniques = []
    for t in s["techniques"]:
        t = dict(t)
        name = t["name"].lower()
        is_wind = "rüzgâr" in name or "hibrit" in name
        is_solar = "güneş" in name or "panel" in name
        if (is_wind and not rc["wind_ok"]) or (is_solar and not rc["solar_ok"]):
            t["status"] = "yasak"
            t["note"] = ("Kısıt: " + ", ".join(f"{c['code']} {c['short']}" for c in rc["codes"]) + ". "
                         + t["note"])
        techniques.append(t)
    restrict = {"cls": rc["cls"], "label": rc["label"], "color": restrictions.COLOR[rc["cls"]],
                "wind_ok": "1" if rc["wind_ok"] else "0", "solar_ok": "1" if rc["solar_ok"] else "0"}
    restrict_codes = [{"code": c["code"], "short": c["short"], "name": c["name"], "detail": c["detail"]}
                      for c in rc["codes"]]

    corr = float(s["corr"])
    yf, yt = float(s["yield_fixed"]), float(s["yield_track"])
    wf, wa = float(s["yield_wind_fixed"]), float(s["yield_wind_auto"])
    kpi = {
        # güneş
        "ghi": _n(s["ghi_kwh_m2"]), "yf": _n(yf), "yt": _n(yt),
        "yf_pct": pct(yf / yt * 100 if yt > 0 else 0), "yt_pct": "100",
        "track_gain": f"+%{s['tracker_gain_pct']:.0f}",
        "tilt": f"{s['opt_tilt']:.0f}", "az": f"{s['opt_azimuth']:.0f}",
        "tilt_label": f"{s['opt_tilt']:.0f}° · {compass(s['opt_azimuth'])}",
        "thermal": f"%{_n(s['thermal_loss_pct'], 1)}", "thermal_pct": pct(s["thermal_loss_pct"]),
        "thermal_jul": f"%{_n(s['thermal_loss_jul_pct'], 1)}", "thermal_jul_pct": pct(s["thermal_loss_jul_pct"]),
        # rüzgâr
        "v100": _n(s["wind_mean_100"], 1), "vhub": _n(s["wind_mean_hub"], 1),
        "v100_pct": pct(s["wind_mean_100"] / 10 * 100), "vhub_pct": pct(s["wind_mean_hub"] / 10 * 100),
        "cf": f"%{_n(s['wind_cf_pct'], 1)}", "cf_pct": pct(s["wind_cf_pct"]),
        "yf_rel": pct(yf / max(yf, wa, 1e-9) * 100), "wa_rel": pct(wa / max(yf, wa, 1e-9) * 100),
        "wf": _n(wf), "wa": _n(wa), "wf_pct": pct(wf / wa * 100 if wa > 0 else 0), "wa_pct": "100" if wa > 0 else "0",
        "auto_gain": f"+%{s['wind_auto_gain_pct']:.0f}" if s["wind_auto_gain_pct"] is not None else "—",
        "prev_deg": f"{s['wind_prevailing']:.0f}", "prev_label": compass(s["wind_prevailing"]),
        "face_deg": f"{s['wind_fixed_facing']:.0f}", "face_label": compass(s["wind_fixed_facing"]),
        # hibrit
        "corr": ("+" if corr >= 0 else "−") + _n(abs(corr), 2),
        "corr_left": pct(50 if corr >= 0 else 50 + corr * 50), "corr_w": pct(abs(corr) * 50),
        "night": f"%{s['wind_share_no_sun_pct']:.0f}", "night_pct": pct(s["wind_share_no_sun_pct"]),
    }
    return {
        "kpi": kpi, "restrict": restrict, "restrict_codes": restrict_codes,
        "wind_mean_100_val": float(s["wind_mean_100"]), "wind_mean_hub_val": float(s["wind_mean_hub"]),
        "cell": f"Veri noktası {w.grid_lat:.2f}, {w.grid_lon:.2f} · {w.source}",
        "live": live, "solar_rows": solar_rows, "wind_rows": wind_rows, "hybrid_rows": hybrid_rows,
        "techniques": techniques, "advice": advice,
        "fig_monthly": charts.monthly_bars(
            {"Sabit (optimum açı)": (s["monthly_pv_fixed"], charts.SUN),
             "Takipçili": (s["monthly_pv_track"], charts.DEEP),
             "Rüzgâr (1 kW türbin)": (s["monthly_wind"], charts.GRAY)},
            "Aylık üretim (1 kWp panel / 1 kW türbin başına)", "kWh"),
        "fig_rose": charts.rose(s["rose"]),
        "fig_wind_heat": charts.heat(s["hour_month_wind"], "Rüzgâr: ay × saat ortalama güç (1 kW türbin)",
                                     "kW", "Blues"),
    }


# =================================================================== ANALİZ
def analysis_bundle(spec: SystemSpec, lat: float, lon: float, month: int) -> dict:
    """Üretim (ayrıntı): seçili noktanın ilçe ihtiyacı ve o noktaya göre boyutlanmış santral (MW ölçeği)."""
    c = city_context(spec, lat, lon)
    d, orient, ilce = c["design"], c["opt"], c["di"]["ilce"]
    if d is not None:
        cs = city.city_spec(spec, d.pv_kwp, d.wind_kw, d.batt_kwh, d.batt_kw)
        plant = "santral"
    else:  # konum ikisine de uygun değil: yalnızca potansiyeli göstermek için 1 MW + 1 MW
        cs = city.city_spec(spec, 1000.0, 1000.0, 0.0, 0.0)
        plant = "1 MWp + 1 MW örnek (konum uygun değil)"
    strat = "akilli" if cs.battery_kwh > 0 else "yok"
    MW = 1000.0

    # 48 saat tahmin
    w = meteo.fetch_forecast(lat, lon, past_days=1, days=3)
    p = compute(w, cs, lat, lon, orient)
    load = city.city_load_kw(w.time, ilce)
    r = simulate(p.total_kw, load, cs, strategy=strat, with_modes=True,
                 export_limit=city.rest_of_country_kw(w.time, ilce))
    i = meteo.current_index(w)
    j = slice(i, min(i + 48, len(w)))
    lt = local_times(w.time)
    times = [t.strftime("%Y-%m-%d %H:%M") for t in lt[j]]
    fig_fc = charts.forecast(times, (p.pv_kw[j] / MW).round(2).tolist(), (p.wind_kw[j] / MW).round(2).tolist(),
                             (load[j] / MW).round(2).tolist(), r.soc_pct()[j].round(1).tolist(), unit="MW")
    table = []
    for k in range(j.start, j.stop):
        table.append([f"{lt[k]:%d.%m %H:00}", _n(p.pv_kw[k] / MW, 1), _n(p.wind_kw[k] / MW, 1),
                      _n(p.hub_ws[k], 1), compass(p.hub_wd[k]), _n(load[k] / MW, 1),
                      f"%{r.soc_pct()[k]:.0f}" if r.usable_kwh > 0 else "—", MODES[r.modes[k]][0]])

    days = daily_energy(w, p, load, r)
    fig_daily = charts.daily_energy(
        [f"{x['date']:%d.%m}" for x in days],
        [round(x["pv_used"] / MW, 1) for x in days], [round(x["wind_used"] / MW, 1) for x in days],
        [round(x["dis"] / MW, 1) for x in days], [round(x["imp"] / MW, 1) for x in days],
        [round((x["pv"] + x["wind"]) / MW, 1) for x in days], unit="MWh")

    # Geçmiş yıl
    we = c["w"]
    pe = compute(we, cs, lat, lon, orient)
    lte = local_times(we.time)
    months = lte.month.to_numpy() - 1
    hours = lte.hour.to_numpy()
    year = int(np.bincount(lte.year.to_numpy()).argmax())
    m = (months == (month - 1)) & (lte.year.to_numpy() == year)
    fig_ws = charts.wind_series([t.strftime("%Y-%m-%d %H:%M") for t in lte[m]],
                                pe.hub_ws[m].round(2).tolist(), pe.hub_wd[m].round(0).tolist(),
                                (pe.wind_kw[m] / MW).round(2).tolist(), unit="MW")
    from .core.wind import wind_rose
    mon_pv = (np.bincount(months, weights=pe.pv_kw, minlength=12) / 1e6).tolist()
    mon_w = (np.bincount(months, weights=pe.wind_kw, minlength=12) / 1e6).tolist()
    mon_need = (np.bincount(months, weights=c["load"], minlength=12) / 1e6).tolist()
    tot = max(pe.total_kw.sum(), 1e-9)
    cover = min(p.total_kw[j].sum() / max(load[j].sum(), 1e-9), 1) * 100
    return {
        "city": city_block(spec, lat, lon, c),
        "fig_forecast": fig_fc, "fig_daily": fig_daily, "table": table,
        "fig_wind_series": fig_ws,
        "fig_wind_heat": charts.heat(_hour_month(pe.wind_kw / MW, months, hours),
                                     f"Rüzgâr ({plant}): ay × saat ortalama güç (geçmiş yıl)", "MW", "Blues"),
        "fig_rose": charts.rose(wind_rose(pe.hub_ws, pe.hub_wd)),
        "fig_pv_heat": charts.heat(_hour_month(pe.pv_kw / MW, months, hours),
                                   f"Güneş ({plant}): ay × saat ortalama güç (geçmiş yıl)", "MW", "YlOrBr"),
        "fig_monthly": charts.monthly_bars({"Güneş": (mon_pv, charts.SUN), "Rüzgâr": (mon_w, charts.WIND),
                                            "İlçe ihtiyacı": (mon_need, charts.GRAY)},
                                           f"Aylık üretim ve {c['di']['label']} ihtiyacı (geçmiş yıl)", "GWh"),
        "kpi": {
            "pv_year": _en(pe.pv_kw.sum()), "wind_year": _en(pe.wind_kw.sum()),
            "wind_share": f"%{pe.wind_kw.sum() / tot * 100:.0f}",
            "wind_share_pct": f"{pe.wind_kw.sum() / tot * 100:.1f}",
            "fc_prod": _en(p.total_kw[j].sum()), "fc_load": _en(load[j].sum()),
            "fc_cover_pct": f"{cover:.1f}", "fc_cover": f"%{cover:.0f}",
        },
        "hist_note": (f"{we.source} · veri noktası {we.grid_lat:.2f}, {we.grid_lon:.2f} · {c['di']['label']} ilçesi "
                      f"ihtiyacı {_en(c['need']['annual_kwh'])}/yıl · santral yıllık üretimi {_en(pe.total_kw.sum())}"),
    }


# =================================================================== ŞEHİR ÖLÇEĞİ
def _pw(kw: float) -> str:
    """Güç: kW / MW (0 ise —)."""
    if abs(kw) < 1e-6:
        return "—"
    return f"{_n(kw / 1000, 1)} MW" if abs(kw) >= 1000 else f"{_n(kw, 1)} kW"


def _en(kwh: float) -> str:
    """Enerji: kWh / MWh / GWh."""
    if abs(kwh) >= 1e6:
        return f"{_n(kwh / 1e6, 1)} GWh"
    if abs(kwh) >= 1e3:
        return f"{_n(kwh / 1e3, 1)} MWh"
    return f"{_n(kwh)} kWh"


def city_context(spec: SystemSpec, lat: float, lon: float) -> dict:
    """Seçili noktanın ilçesi, ihtiyacı, uygunluğu ve o noktaya göre boyutlanmış santral."""
    w = meteo.fetch_history_year(lat, lon)
    opt = optimum_for(spec, lat, lon) or Orientation(solar.rule_of_thumb_tilt(lat), 180.0, 0.0, "yaklaşık")
    di = city.district_of(lat, lon)
    nd = city.need(di["ilce"])
    rc = restrictions.check(lat, lon)
    pv1, w1 = city.unit_series(w, spec, lat, lon, opt)
    load = city.city_load_kw(w.time, di["ilce"])
    limit = city.rest_of_country_kw(w.time, di["ilce"])
    d = city.design(load, pv1, w1, rc["wind_ok"], rc["solar_ok"])
    return {"w": w, "opt": opt, "di": di, "need": nd, "rc": rc, "pv1": pv1, "w1": w1, "load": load,
            "limit": limit, "design": d}


def city_block(spec: SystemSpec, lat: float, lon: float, c: dict | None = None) -> dict:
    """Veriler › Üretim: şehrin ihtiyacını bu noktadaki santral karşılayabilir mi?"""
    c = c or city_context(spec, lat, lon)
    d, nd, di, rc = c["design"], c["need"], c["di"], c["rc"]
    avg_kw = nd["annual_kwh"] / 8760
    out = {"ilce": di["label"], "pop": _n(nd["pop"]), "need_year": _en(nd["annual_kwh"]),
           "need_avg": _pw(avg_kw), "fit": rc["label"], "fit_color": restrictions.COLOR[rc["cls"]],
           "ok": "1" if d else "0", "sources": city.SOURCES}
    if d is None:
        out["msg"] = "Bu nokta güneşe de rüzgâra da uygun değil; burada santral önerilmez."
        return out
    runs = city.city_scenarios(c["w"], spec, d, c["pv1"], c["w1"], c["load"], c["limit"])
    s4 = runs[4].summary
    # Önümüzdeki 48 saat: aynı santral, tahmin verisiyle
    wf = meteo.fetch_forecast(lat, lon, past_days=1, days=3)
    pv1f, w1f = city.unit_series(wf, spec, lat, lon, c["opt"])
    i = meteo.current_index(wf)
    j = slice(i, min(i + 48, len(wf)))
    loadf = city.city_load_kw(wf.time, di["ilce"])[j]
    prodf = (pv1f * d.pv_kwp + w1f * d.wind_kw)[j]
    cover48 = float(np.minimum(prodf, loadf).sum() / max(loadf.sum(), 1e-9) * 100)
    installed = d.pv_kwp + d.wind_kw
    n_turb = int(np.ceil(d.wind_kw / city.CITY_TURBINE_KW)) if d.wind_kw > 0 else 0
    parts = []
    if d.pv_kwp > 0:
        parts.append(f"{_pw(d.pv_kwp)}p güneş")
    if d.wind_kw > 0:
        parts.append(f"{_pw(d.wind_kw)} rüzgâr ({n_turb} × E-82)")
    out.update({
        "plant": " + ".join(parts), "batt": f"{_en(d.batt_kwh)} / {_pw(d.batt_kw)}",
        "wind_share": f"%{d.wind_share * 100:.0f}",
        "direct": f"%{d.direct_cover * 100:.0f}", "direct_pct": f"{d.direct_cover * 100:.1f}",
        "with_batt": f"%{s4['self_sufficiency_pct']:.0f}", "with_batt_pct": f"{s4['self_sufficiency_pct']:.1f}",
        "cover48": f"%{cover48:.0f}", "cover48_pct": f"{min(cover48, 100):.1f}",
        "ratio": f"{_n(installed / avg_kw, 1)}×",
        "msg": d.note,
        "prod48": _en(prodf.sum()), "load48": _en(loadf.sum()),
    })
    return out


# =================================================================== SENARYOLAR
def scenario_bundle(spec: SystemSpec, region: str, my_lat: float, my_lon: float) -> dict:
    """Şehir ölçeği: her bölge kendi ilçesinin ihtiyacına ve kendi uygunluğuna göre boyutlanır."""
    places = {"Seçili nokta": (my_lat, my_lon), **CANDIDATE_REGIONS}  # seçili nokta listenin başında
    compare, detail = [], None
    for name, (lat, lon) in places.items():
        c = city_context(spec, lat, lon)
        d = c["design"]
        row = {"bolge": name, "kisit": c["rc"]["label"] + " · " + c["di"]["label"] + " ilçesi"}
        if d is None:
            row.update({"s1": "—", "s3": "—", "s4": "—", "s1v": "0", "s3v": "0", "s4v": "0", "kisilan": "—"})
            runs = None
        else:
            runs = city.city_scenarios(c["w"], spec, d, c["pv1"], c["w1"], c["load"], c["limit"])
            by = {r.code: r.summary for r in runs}
            row["kisit"] += f" · bataryalı %{by['S4']['self_sufficiency_pct']:.0f}"
            row.update({
                "s1": f"%{by['S1']['self_sufficiency_pct']:.0f}", "s3": f"%{by['S3']['self_sufficiency_pct']:.0f}",
                "s4": f"%{by['S4']['self_sufficiency_pct']:.0f}",
                "s1v": f"{by['S1']['self_sufficiency_pct']:.1f}", "s3v": f"{by['S3']['self_sufficiency_pct']:.1f}",
                "s4v": f"{by['S4']['self_sufficiency_pct']:.1f}",
                "kisilan": f"{_en(by['S4a']['curtail_kwh'])} → {_en(by['S4']['curtail_kwh'])}",
            })
        compare.append(row)
        if name == region:
            detail = (c, runs)
    c, runs = detail
    w, d = c["w"], c["design"]
    base = {"compare": compare, "note": f"{w.source} · veri noktası {w.grid_lat:.2f}, {w.grid_lon:.2f} · "
                                        f"{c['di']['label']} ilçesi ihtiyacı {_en(c['need']['annual_kwh'])}/yıl"}
    if runs is None:
        msg = f"{region}: güneşe de rüzgâra da uygun değil; santral önerilmez."
        return {**base, "rows": [], "sweep": [], "conclusion": [msg], "smart": {}, "fig_monthly": charts.empty()}
    rows = []
    capmax = max(r.summary["capex_usd"] for r in runs) or 1.0
    co2max = max(r.summary["co2_t_per_year"] for r in runs) or 1.0
    for r in runs:
        s = r.summary
        rows.append({
            "acikp": f"{s['import_kwh'] / max(s['load_kwh'], 1e-9) * 100:.1f}",
            "acikt": f"%{s['import_kwh'] / max(s['load_kwh'], 1e-9) * 100:.0f} · {_en(s['import_kwh'])}",
            "yatp": f"{s['capex_usd'] / capmax * 100:.1f}", "yatt": f"{_n(s['capex_usd'] / 1e6, 1)} M$",
            "co2p": f"{s['co2_t_per_year'] / co2max * 100:.1f}", "co2t": f"{_n(s['co2_t_per_year'])} t/yıl",
            "kod": r.code, "ad": r.name, "uretim": _en(s["production_kwh"]),
            "acik": _en(s["import_kwh"]), "verilen": _en(s["export_kwh"]), "kisilan": _en(s["curtail_kwh"]),
            "oz": f"%{s['self_sufficiency_pct']:.0f}", "ozv": f"{s['self_sufficiency_pct']:.1f}",
            "dalga": _n(s["hourly_cv"], 2),
            "sifir": f"%{s['zero_hours_pct']:.0f}", "yatirim": f"{_n(s['capex_usd'] / 1e6, 1)} M$",
            "geri": "—" if s["payback_years"] == float("inf") else f"{_n(s['payback_years'], 1)} yıl",
            "co2": _n(s["co2_t_per_year"]),
        })
    sweep = city.city_sweep(w, spec, d, c["pv1"], c["w1"], c["load"], c["limit"])
    sweep_rows = [{
        "pv": _pw(x["pv_kwp"]) + ("p" if x["pv_kwp"] else ""), "wind": _pw(x["wind_kw"]),
        "batt": _en(x["battery_kwh"]) if x["battery_kwh"] else "—",
        "oz": f"%{x['self_sufficiency_pct']:.0f}", "kisilan": _en(x["curtail_kwh"]),
        "yatirim": f"{_n(x['capex_usd'] / 1e6, 1)} M$", "net": f"{_n(x['annual_net_cost_usd'] / 1e6, 2)} M$/yıl",
    } for x in sweep[:8]]
    best = sweep[0]
    s4, s4a = runs[4].summary, runs[3].summary
    label = region if region != "Seçili nokta" else c["di"]["label"]
    conclusion = [
        (f"{c['di']['label']} ilçesinin ihtiyacı ({_en(c['need']['annual_kwh'])}/yıl) için bu noktadaki en "
         f"düşük net maliyetli kurulum: güneş {_pw(best['pv_kwp'])}, rüzgâr {_pw(best['wind_kw'])}, "
         f"batarya {_en(best['battery_kwh']) if best['battery_kwh'] else '—'} "
         f"(karşılama %{best['self_sufficiency_pct']:.0f})."),
        (f"Akıllı yönetim, basit kurala göre kısılan enerjiyi {_en(s4a['curtail_kwh'])} → {_en(s4['curtail_kwh'])} "
         f"düşürür. Fazla üretim KKTC'nin diğer ilçelerine verilebildiği için kısıt düşüktür."),
    ]
    if d.note:
        conclusion.append(d.note)
    cmax = max(s4a["curtail_kwh"], s4["curtail_kwh"], 1e-9)
    smart = {
        "cut_basic": _en(s4a["curtail_kwh"]), "cut_smart": _en(s4["curtail_kwh"]),
        "cut_basic_pct": f"{s4a['curtail_kwh'] / cmax * 100:.1f}", "cut_smart_pct": f"{s4['curtail_kwh'] / cmax * 100:.1f}",
        "cut_drop": (f"−%{(1 - s4['curtail_kwh'] / s4a['curtail_kwh']) * 100:.0f}" if s4a["curtail_kwh"] > 1 else "—"),
        "best": " + ".join(x for x in (
            f"{_pw(best['pv_kwp'])}p güneş" if best["pv_kwp"] else "",
            f"{_pw(best['wind_kw'])} rüzgâr" if best["wind_kw"] else "",
            f"{_en(best['battery_kwh'])} batarya" if best["battery_kwh"] else "") if x),
        "best_oz": f"%{best['self_sufficiency_pct']:.0f}", "best_oz_pct": f"{best['self_sufficiency_pct']:.1f}",
        "label": label,
    }
    return {**base, "rows": rows, "sweep": sweep_rows, "conclusion": conclusion, "smart": smart,
            "fig_monthly": charts.scenario_monthly(runs)}
