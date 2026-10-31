"""Yönlendirme API paketi testleri (internet gerektirmez)."""
import datetime as dt

import numpy as np

from hibrit_enerji.core.meteo import Weather
from hibrit_enerji.orientation_api import build_guidance


def _weather(n=4, wd=315.0, base="2026-06-21T08:00"):
    base = np.datetime64(base)
    t = (base + np.arange(n) * np.timedelta64(1, "h")).astype("datetime64[s]")
    f = lambda v: np.full(n, float(v))  # noqa: E731
    return Weather(time=t, ghi=f(800), dni=f(700), dhi=f(100), temp=f(25),
                   ws10=f(6), ws100=f(7.5), wd10=f(wd), wd100=f(wd),
                   pressure=f(1013.25), grid_lat=35.2, grid_lon=33.4, source="test")


def test_paket_yapisi_ve_araliklar():
    now = dt.datetime(2026, 6, 21, 9, 30, tzinfo=dt.timezone.utc)
    g = build_guidance(_weather(), 35.1856, 33.3823, now)
    assert set(g) == {"konum", "zaman_utc", "gunes", "ruzgar", "pusula"}
    assert 0 <= g["gunes"]["az_deg"] < 360
    assert 0 <= g["gunes"]["egim_deg"] <= 90
    assert g["gunes"]["gece"] is False  # haziran sabahı Lefkoşa'da gündüz
    assert g["ruzgar"]["gelis_yonu_deg"] == 315.0
    assert g["ruzgar"]["govbek_hizi_ms"] > 0


def test_gece_gunes_asagi():
    w = _weather(n=6, base="2026-06-20T22:00")
    now = dt.datetime(2026, 6, 21, 0, 30, tzinfo=dt.timezone.utc)  # gece (UTC 00:30 = 03:30 yerel)
    g = build_guidance(w, 35.1856, 33.3823, now)
    assert g["gunes"]["gece"] is True
    assert g["ruzgar"]["gelis_yonu_deg"] == 315.0
