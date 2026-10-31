"""Belgelerdeki sayıları üretir (varsayılan sistem, örnek bölgeler, son tam yıl, ECMWF IFS ~9 km).

Kullanım:  .venv/bin/python scripts/rapor.py
Çıktı Markdown'dır; docs/K*.md içindeki "Güncel sonuçlar" tablolarına yapıştırılır.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hibrit_enerji.core import meteo  # noqa: E402
from hibrit_enerji.core.analysis import (capacity_sweep, run_scenarios,  # noqa: E402
                                         site_analysis)
from hibrit_enerji.core.config import REGIONS  # noqa: E402
from hibrit_enerji.core.production import user_orientation  # noqa: E402
from hibrit_enerji.core.spec import SystemSpec  # noqa: E402
from hibrit_enerji.core.wind import compass  # noqa: E402


def n(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def main() -> None:
    spec = SystemSpec()
    print(f"Varsayılan sistem: {n(spec.pv_kwp, 1)} kWp güneş (sabit), {spec.wind_rated_kw:g} kW rüzgâr "
          f"({spec.hub_height_m:g} m), {spec.battery_kwh:g} kWh batarya, aylık {spec.monthly_kwh:g} kWh "
          f"tüketim, şebekeye verme sınırı {spec.export_limit_kw:g} kW. Veri: ECMWF IFS (~9 km, Open-Meteo arşivi) {meteo.last_full_year()}.\n")

    print("### Bölge potansiyeli\n")
    print("| Bölge | Tür | Yıllık güneş (kWh/m²) | Sabit panel (kWh/kWp) | Takipçi kazancı | Isıl kayıp yıl / Temmuz | "
          "Rüzgâr ort. (12 m / 100 m) | Türbin KF | Güneş–rüzgâr korelasyonu | Rüzgârın güneşsiz saat payı | "
          "Sabit türbin yönü |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    kind_tr = {"ozet": "Özet", "ruzgar": "Rüzgâr", "gunes": "GES"}
    results = {}
    for reg in REGIONS:
        name, lat, lon = reg.name, reg.lat, reg.lon
        w = meteo.fetch_history_year(lat, lon)
        s = site_analysis(w, spec, lat, lon)
        results[name] = (w, lat, lon, s)
        print(f"| {name} | {kind_tr[reg.kind]} | {n(s['ghi_kwh_m2'])} | {n(s['yield_fixed'])} | +%{s['tracker_gain_pct']:.0f} | "
              f"%{n(s['thermal_loss_pct'], 1)} / %{n(s['thermal_loss_jul_pct'], 1)} | "
              f"{n(s['wind_mean_hub'], 1)} / {n(s['wind_mean_100'], 1)} m/s | %{n(s['wind_cf_pct'], 1)} | "
              f"{n(s['corr'], 2)} | %{s['wind_share_no_sun_pct']:.0f} | "
              f"{compass(s['wind_fixed_facing'])} ({s['wind_fixed_facing']:.0f}°) |")

    print("\n### Dört senaryo (öz yeterlilik / enerji açığı kWh / kısılan kWh)\n")
    print("| Bölge | S1 güneş | S2 rüzgâr | S3 hibrit | S4a hibrit+batarya (basit) | S4 hibrit+batarya+akıllı |")
    print("|---|---|---|---|---|---|")
    best_rows = []
    for name, (w, lat, lon, s) in results.items():
        orient = user_orientation(spec, lat, s["orientation"])
        runs = run_scenarios(w, spec, lat, lon, orient)
        cells = [f"%{r.summary['self_sufficiency_pct']:.0f} / {n(r.summary['import_kwh'])} / "
                 f"{n(r.summary['curtail_kwh'])}" for r in runs]
        print(f"| {name} | " + " | ".join(cells) + " |")
        sw = capacity_sweep(w, spec, lat, lon, orient)
        b = sw[0]
        best_rows.append(f"| {name} | {b['pv_kwp']:g} kWp | {b['wind_kw']:g} kW | {b['battery_kwh']:g} kWh | "
                         f"%{b['self_sufficiency_pct']:.0f} | {n(b['capex_usd'])} $ | "
                         f"{n(b['annual_net_cost_usd'])} $/yıl |")
        s3, s1 = runs[2].summary, runs[0].summary
        best_rows_extra = (name, s1["hourly_cv"], s3["hourly_cv"], s1["zero_hours_pct"], s3["zero_hours_pct"],
                           runs[3].summary, runs[4].summary)
        results[name] = (*results[name], best_rows_extra)

    print("\n### Dalgalanma ve akıllı yönetimin katkısı\n")
    print("| Bölge | Saatlik dalgalanma (CV) S1 → S3 | Üretimsiz saat S1 → S3 | "
          "Kısılan kWh basit → akıllı | Şebekeye verilen kWh basit → akıllı | CO₂ (t/yıl, S4) |")
    print("|---|---|---|---|---|---|")
    for name, val in results.items():
        _, cv1, cv3, z1, z3, s4a, s4 = val[4]
        print(f"| {name} | {n(cv1, 2)} → {n(cv3, 2)} | %{z1:.0f} → %{z3:.0f} | "
              f"{n(s4a['curtail_kwh'])} → {n(s4['curtail_kwh'])} | {n(s4a['export_kwh'])} → {n(s4['export_kwh'])} | "
              f"{n(s4['co2_t_per_year'], 1)} |")

    print("\n### En düşük yıllık net maliyetli tasarım (kapasite taraması, 76 kombinasyon)\n")
    print("| Bölge | Güneş | Rüzgâr | Batarya | Öz yeterlilik | Yatırım | Yıllık net maliyet |")
    print("|---|---|---|---|---|---|---|")
    print("\n".join(best_rows))


if __name__ == "__main__":
    main()


def city_report() -> None:
    """Şehir (ilçe) ölçeği: her örnek bölge kendi ilçesinin ihtiyacına ve uygunluğuna göre boyutlanır."""
    import warnings
    warnings.simplefilter("ignore", FutureWarning)
    from hibrit_enerji import services
    from hibrit_enerji.core import city
    spec = SystemSpec()
    print("\n### Şehir ölçeği: ilçe ihtiyacı ve noktaya göre boyutlanan santral\n")
    print(f"Kişi başı tüketim {n(city.PER_CAPITA_KWH)} kWh/yıl (2011: 1.254 GWh / 286.257 kişi); "
          f"ilçe nüfusu = 2011 payı × 2021 tahmini toplam ({n(city.TOTAL_POP_2021_EST)}).\n")
    print("| Bölge | İlçe | İlçe ihtiyacı | Uygunluk | Önerilen santral | Batarya | Bataryasız | Bataryalı | Kurulu / ort. ihtiyaç |")
    print("|---|---|---|---|---|---|---|---|---|")
    for reg in REGIONS:
        b = services.city_block(spec, reg.lat, reg.lon)
        if b["ok"] == "1":
            print(f"| {reg.name} | {b['ilce']} | {b['need_year']} | {b['fit']} | {b['plant']} | {b['batt']} | "
                  f"{b['direct']} | {b['with_batt']} | {b['ratio']} |")
        else:
            print(f"| {reg.name} | {b['ilce']} | {b['need_year']} | {b['fit']} | — (önerilmez) | — | — | — | — |")


if __name__ == "__main__" and "--sehir" in sys.argv:
    city_report()
