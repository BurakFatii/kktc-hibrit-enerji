"""Minimal hibrit enerji paneli: güneş (takipçi) + rüzgar + batarya + EV."""
from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.express as px

from src.config import LOCATIONS, DEFAULTS
from src.meteo import fetch_open_meteo, current_values
from src.energy import solar_power_kw, wind_power_kw, total_power_kw
from src.battery import soc_percent
from src.modes import suggest_mode

st.set_page_config(page_title="KKTC Hibrit Enerji", layout="wide")
st.title("KKTC Hibrit Enerji — Güneş + Rüzgar")

with st.sidebar:
    st.header("Kurulum")
    place = st.selectbox("Konum", list(LOCATIONS.keys()), index=0)
    pv = st.number_input("Güneş (kWp)", 1.0, 50.0, DEFAULTS["pv_kwp"], step=0.5)
    wind_rated = st.number_input("Rüzgar (kW)", 0.0, 20.0, DEFAULTS["wind_kw"], step=0.5)
    batt_cap = st.number_input("Ev bataryası (kWh)", 2.0, 50.0, DEFAULTS["battery_kwh"])
    batt_soc = st.number_input("Batarya doluluk (kWh)", 0.0, batt_cap, batt_cap * 0.6)
    load = st.number_input("Anlık tüketim (kW)", 0.0, 20.0, 1.2, step=0.1)
    ev = st.checkbox("EV bağlı (V2H)", value=False)

lat, lon = LOCATIONS[place]["lat"], LOCATIONS[place]["lon"]

try:
    payload = fetch_open_meteo(lat, lon)
    live = current_values(payload)
    hourly = payload.get("hourly", {})
    source = "Canlı: Open-Meteo (ücretsiz, anahtarsız)"
except Exception as e:  # çevrimdışı önizleme
    live = {"ghi": 600.0, "wind_ms": 5.0, "temp_c": 24.0, "weathercode": 0}
    hourly = {}
    source = f"Çevrimdışı önizleme ({e})"

solar = solar_power_kw(live["ghi"], pv, DEFAULTS["tracking_gain"])
wind = wind_power_kw(live["wind_ms"], wind_rated)
total = total_power_kw(solar, wind)
soc = soc_percent(batt_soc, batt_cap)
mode, why = suggest_mode(total, load, soc, ev)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Güneş (kW)", f"{solar:.2f}", f"{live['ghi']:.0f} W/m²")
c2.metric("Rüzgar (kW)", f"{wind:.2f}", f"{live['wind_ms']:.1f} m/s")
c3.metric("Toplam (kW)", f"{total:.2f}", f"Tüketim {load:.1f} kW")
c4.metric("Batarya", f"%{soc}", f"{batt_soc:.1f}/{batt_cap:.0f} kWh")
st.caption(source + f" • {place} {live['temp_c']:.1f}°C")

st.subheader(f"Önerilen mod: {mode}")
st.info(why)

if hourly and "time" in hourly:
    df = pd.DataFrame({
        "zaman": pd.to_datetime(hourly["time"][:48]),
        "güneş_kW": [solar_power_kw(g, pv, DEFAULTS["tracking_gain"])
                     for g in hourly.get("shortwave_radiation", [])[:48]],
        "rüzgar_kW": [wind_power_kw(w, wind_rated)
                      for w in hourly.get("wind_speed_10m", [])[:48]],
    })
    df["toplam_kW"] = df["güneş_kW"] + df["rüzgar_kW"]
    df["gün"] = df["zaman"].dt.date.astype(str)
    daily = df.groupby("gün")[["güneş_kW", "rüzgar_kW", "toplam_kW"]].mean().reset_index()

    t1, t2 = st.tabs(["48 saatlik tahmin", "Günlük ortalama"])
    with t1:
        st.plotly_chart(px.line(df, x="zaman", y=["güneş_kW", "rüzgar_kW", "toplam_kW"],
                                labels={"value": "kW", "variable": "kaynak"}),
                        use_container_width=True)
    with t2:
        st.plotly_chart(px.bar(daily, x="gün", y=["güneş_kW", "rüzgar_kW"],
                               labels={"value": "ort. kW", "variable": "kaynak"}),
                        use_container_width=True)
else:
    st.warning("Tahmin grafiği için internet gerekli (Open-Meteo).")
