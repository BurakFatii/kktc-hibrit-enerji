"""Çekirdek hesapların doğrulama testleri (internet gerektirmez)."""
import numpy as np
import pytest

from hibrit_enerji.core import solar, wind
from hibrit_enerji.core.ems import simulate
from hibrit_enerji.core.meteo import Weather
from hibrit_enerji.core.spec import SystemSpec


def _weather(times, ghi=800.0, dni=700.0, dhi=100.0, ws=6.0, wd=315.0):
    n = len(times)
    f = lambda v: np.full(n, float(v))  # noqa: E731
    return Weather(time=times, ghi=f(ghi), dni=f(dni), dhi=f(dhi), temp=f(25), ws10=f(ws),
                   ws100=f(ws * 1.3), wd10=f(wd), wd100=f(wd), pressure=f(1013.25),
                   grid_lat=35, grid_lon=33.5, source="test")


def test_sun_noon_equinox_lefkosa():
    # 20 Mart ~ ekinoks; Lefkoşa güneş öğlesi ≈ 09:52 UTC
    t = np.array(["2025-03-20T10:22"], dtype="datetime64[s]")  # -30 dk kaydırma ile 09:52
    zen, az = solar.sun_position(t, 35.19, 33.38)
    assert abs(zen[0] - 35.19) < 1.5
    assert abs(az[0] - 180) < 5


def test_tracker_beats_fixed_and_fixed_beats_flat():
    t = np.arange(np.datetime64("2025-06-21T04:00"), np.datetime64("2025-06-21T17:00"),
                  np.timedelta64(1, "h")).astype("datetime64[s]")
    w = _weather(t)
    zen, az = solar.sun_position(t, 35.2, 33.4)
    track = solar.poa_tracker(w, zen, az).sum()
    fixed = solar.poa_fixed(w, zen, az, 30, 180).sum()
    assert track > fixed > 0


def test_pv_power_respects_label():
    spec = SystemSpec(panel_wp=500, panel_count=4)
    # NOCT=45 iken 1000 W/m2'de hücre 25°C olsun diye hava 25 - 31.25 °C
    p = solar.pv_power_kw(np.array([1000.0, 0.0]), np.array([25.0 - 31.25, 20.0]), spec)
    expected = 2.0 * (1 - solar.SYSTEM_LOSSES_PCT / 100)  # inverter verimi ~etiket
    assert p[0] == pytest.approx(expected * 0.97, rel=0.03)
    assert p[1] == 0


def test_hot_panel_produces_less():
    spec = SystemSpec(panel_wp=500, panel_count=4)
    cool, hot = solar.pv_power_kw(np.array([900.0, 900.0]), np.array([10.0, 40.0]), spec)
    assert hot < cool


def test_power_curve_limits():
    spec = SystemSpec(wind_rated_kw=3, wind_cut_in_ms=3, wind_rated_ms=11, wind_cut_out_ms=25)
    p = wind.power_kw(np.array([2.0, 3.0, 7.0, 11.0, 20.0, 25.5]), None, spec)
    assert p[0] == 0 and p[1] == 0 and 0 < p[2] < 3
    assert p[3] == pytest.approx(3) and p[4] == pytest.approx(3) and p[5] == 0


def test_catalog_power_curve_is_used():
    spec = SystemSpec(wind_rated_kw=3, wind_power_curve="3:0, 6:800, 10:2500, 12:3000, 25:3000")
    p = wind.power_kw(np.array([6.0, 10.0]), None, spec)
    assert p[0] == pytest.approx(0.8) and p[1] == pytest.approx(2.5)


def test_thin_air_produces_less_wind_power():
    spec = SystemSpec(wind_rated_kw=3)
    v = np.array([7.0])
    dense = wind.power_kw(v, np.array([1.225]), spec)[0]
    thin = wind.power_kw(v, np.array([1.10]), spec)[0]
    assert thin < dense


def test_hub_speed_between_10m_and_100m():
    t = np.arange(np.datetime64("2025-01-01T00:00"), np.datetime64("2025-01-01T05:00"),
                  np.timedelta64(1, "h")).astype("datetime64[s]")
    w = _weather(t, ws=5.0)
    v, rho = wind.hub_conditions(w, SystemSpec(hub_height_m=30))
    assert ((v > 5.0) & (v < 6.5)).all()
    assert ((rho > 1.1) & (rho < 1.25)).all()


def test_fixed_yaw_loses_energy_off_axis():
    v = np.array([8.0, 8.0])
    d = np.array([0.0, 90.0])
    eff = wind.misalignment_speed(v, d, 0.0)
    assert eff[0] == pytest.approx(8.0) and eff[1] == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("strategy", ["yok", "basit", "akilli"])
def test_ems_energy_balance(strategy):
    rng = np.random.default_rng(1)
    hours = 24 * 30
    prod = np.clip(np.sin(np.linspace(0, 30 * 2 * np.pi, hours)) * 6, 0, None) + rng.random(hours)
    load = 0.8 + rng.random(hours)
    spec = SystemSpec(battery_kwh=10, export_limit_kw=2)
    r = simulate(prod, load, spec, strategy=strategy)
    eff = np.sqrt(spec.battery_rt_eff_pct / 100)
    soc0 = (spec.battery_usable_kwh * 0.5) if strategy != "yok" else 0
    lhs = prod + r.grid_import + r.discharge
    rhs = load + r.export + r.charge + r.curtail
    assert np.allclose(lhs, rhs, atol=1e-9)
    # Batarya enerji korunumu
    stored = soc0 + (r.charge * eff).sum() - (r.discharge / eff).sum()
    assert stored == pytest.approx(r.soc_kwh[-1], abs=1e-6)
    assert (r.export <= spec.export_limit_kw + 1e-9).all()


def test_smart_curtails_less_without_hurting_self_sufficiency():
    hours = 24 * 60
    h = np.arange(hours) % 24
    prod = np.clip(np.sin((h - 6) / 12 * np.pi), 0, None) * 8.0
    load = np.where((h >= 18) & (h <= 23), 2.0, 0.6)
    spec = SystemSpec(battery_kwh=10, export_limit_kw=2.5, battery_power_kw=5)
    basic = simulate(prod, load, spec, strategy="basit")
    smart = simulate(prod, load, spec, strategy="akilli")
    assert smart.curtail.sum() < basic.curtail.sum()
    assert smart.grid_import.sum() <= basic.grid_import.sum() * 1.02


def test_spec_from_form_tolerates_bad_input():
    s = SystemSpec.from_dict({"panel_wp": "450,5", "panel_count": "x", "pv_mount": "??",
                              "auto_orient": "hayır"})
    assert s.panel_wp == 450.5 and s.panel_count == 10
    assert s.pv_mount == "sabit" and s.auto_orient is False


def test_restriction_zones_classify_known_places():
    from hibrit_enerji.core.restrictions import check
    assert check(35.1517, 33.5106)["cls"] == "kirmizi"          # Ercan havalimanı
    karpaz = check(35.646, 34.485)                               # Karpaz ÖÇKB
    assert karpaz["cls"] == "kirmizi" and not karpaz["wind_ok"] and not karpaz["solar_ok"]
    alev = check(35.285, 33.533)                                 # Alevkayası ormanı -> yalnız rüzgâr
    assert alev["cls"] == "mavi" and alev["wind_ok"] and not alev["solar_ok"]
    assert any(c["code"] == "G01" for c in alev["codes"])
    gaz = check(35.125, 33.94)                                   # Gazimağusa yerleşimi -> yalnız güneş
    assert gaz["cls"] == "sari" and not gaz["wind_ok"] and gaz["solar_ok"]
    assert any(c["code"] == "R02" for c in gaz["codes"])
    assert check(35.0, 32.0)["cls"] == "uygun"                   # deniz, kısıt yok


def test_city_district_and_need():
    from hibrit_enerji.core import city
    assert city.district_of(35.125, 33.94)["ilce"] == "Gazimağusa"
    assert city.district_of(35.19, 33.36)["ilce"] == "Lefkoşa"
    total = sum(city.need(k)["annual_kwh"] for k in city.POP_2011)
    assert total == pytest.approx(city.TOTAL_POP_2021_EST * city.PER_CAPITA_KWH, rel=1e-6)
    assert city.PER_CAPITA_KWH == pytest.approx(1_254e6 / 286_257)


def test_city_design_meets_annual_need_and_respects_suitability():
    from hibrit_enerji.core import city
    n = 24 * 60
    h = np.arange(n) % 24
    load = np.full(n, 100.0)
    pv1 = np.clip(np.sin((h - 6) / 12 * np.pi), 0, None)          # 1 kWp güneş
    w1 = 0.3 + 0.2 * np.cos(h / 24 * 2 * np.pi)                    # 1 kW rüzgâr (gece güçlü)
    d = city.design(load, pv1, w1, wind_ok=True, solar_ok=True)
    prod = pv1 * d.pv_kwp + w1 * d.wind_kw
    assert prod.sum() == pytest.approx(load.sum(), rel=1e-6)       # yıllık enerji = ihtiyaç
    assert 0 < d.wind_share < 1                                    # tamamlayıcı -> karışım
    only_solar = city.design(load, pv1, w1, wind_ok=False, solar_ok=True)
    assert only_solar.wind_kw == 0 and only_solar.pv_kwp > 0
    assert city.design(load, pv1, w1, wind_ok=False, solar_ok=False) is None
