"""Plotly figürleri — yalnızca zaman içindeki değişimi önemli olan veriler için.

Palet: neon (#00FF41) + koyu yeşil + nötr gri. Arka plan şeffaf; açık/koyu tema
yazı rengini Reflex'in plotly şablonu verir. Gölge efekti yok.
"""
from __future__ import annotations

import plotly.graph_objects as go

from .core.analysis import MONTHS_TR
from .core.wind import COMPASS16

NEON = "#00FF41"
DEEP = "#00A82D"
GRAY = "#8a8a8a"
GRAY2 = "#5f6368"
SUN, WIND, LOAD, BATT = NEON, DEEP, GRAY, GRAY2
CURT = "#0a0a0a"
KIND_COLORS = {"ozet": GRAY, "ruzgar": DEEP, "gunes": NEON}
HEAT = [[0.0, "rgba(0,255,65,0.03)"], [1.0, NEON]]
GRID = "rgba(128,128,128,0.18)"


def _base(height: int = 320, title: str = "", **extra) -> dict:
    layout = dict(
        height=height, margin=dict(l=44, r=16, t=36 if title else 12, b=36),
        title=dict(text=title, font=dict(size=13), x=0, xanchor="left") if title else None,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", size=12),
        legend=dict(orientation="h", y=-0.2, x=0, bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        xaxis=dict(gridcolor=GRID, zeroline=False, showline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False, showline=False),
    )
    layout.update(extra)
    return layout


def empty(title: str = "") -> go.Figure:
    f = go.Figure()
    f.update_layout(**_base(160, title, xaxis=dict(visible=False), yaxis=dict(visible=False)))
    return f


def forecast(times, pv, wk, load, soc_pct, unit: str = "kW") -> go.Figure:
    f = go.Figure()
    f.add_trace(go.Scatter(x=times, y=pv, name=f"Güneş {unit}", line=dict(color=SUN, width=2),
                           fill="tozeroy", fillcolor="rgba(0,255,65,0.12)"))
    f.add_trace(go.Scatter(x=times, y=wk, name=f"Rüzgâr {unit}", line=dict(color=WIND, width=2)))
    f.add_trace(go.Scatter(x=times, y=load, name=f"İhtiyaç {unit}", line=dict(color=LOAD, width=1.5, dash="dash")))
    f.add_trace(go.Scatter(x=times, y=soc_pct, name="Batarya %", yaxis="y2",
                           line=dict(color=BATT, width=1.5, dash="dot")))
    f.update_layout(**_base(300, yaxis=dict(title=unit, gridcolor=GRID, zeroline=False),
                            yaxis2=dict(title="%", overlaying="y", side="right", range=[0, 105],
                                        showgrid=False, zeroline=False)))
    return f


def heat(z, title: str, unit: str, scale: str | None = None) -> go.Figure:
    f = go.Figure(go.Heatmap(z=z, x=[f"{h:02d}" for h in range(24)], y=MONTHS_TR, colorscale=HEAT,
                             xgap=1, ygap=1, colorbar=dict(title=unit, thickness=8, outlinewidth=0),
                             hovertemplate="%{y} %{x}:00 → %{z:.2f} " + unit + "<extra></extra>"))
    f.update_layout(**_base(340, title, hovermode="closest",
                            xaxis=dict(title="Saat (yerel)", showgrid=False),
                            yaxis=dict(autorange="reversed", showgrid=False)))
    return f


def rose(r: dict) -> go.Figure:
    f = go.Figure()
    for (label, vals), a in zip(r.items(), [0.15, 0.3, 0.5, 0.75, 1.0]):
        f.add_trace(go.Barpolar(r=vals, theta=COMPASS16, name=label,
                                marker=dict(color=f"rgba(0,255,65,{a})", line=dict(width=0))))
    f.update_layout(**_base(340, hovermode="closest", margin=dict(l=24, r=24, t=16, b=24)),
                    polar=dict(bgcolor="rgba(0,0,0,0)",
                               angularaxis=dict(direction="clockwise", rotation=90, gridcolor=GRID),
                               radialaxis=dict(gridcolor=GRID, showticklabels=False)))
    return f


def monthly_bars(series: dict[str, tuple[list[float], str]], title: str, unit: str) -> go.Figure:
    f = go.Figure()
    for name, (vals, color) in series.items():
        f.add_trace(go.Bar(x=MONTHS_TR, y=vals, name=name, marker=dict(color=color, line=dict(width=0))))
    f.update_layout(**_base(300, title, hovermode="x",
                            yaxis=dict(title=unit, gridcolor=GRID, zeroline=False)),
                    barmode="group", bargap=0.25)
    return f


def wind_series(times, speed, direction, power, unit: str = "kW") -> go.Figure:
    f = go.Figure()
    f.add_trace(go.Scatter(x=times, y=power, name=f"Türbin {unit}", line=dict(color=NEON, width=1.5),
                           fill="tozeroy", fillcolor="rgba(0,255,65,0.12)"))
    f.add_trace(go.Scatter(x=times, y=speed, name="Hız m/s", line=dict(color=DEEP, width=1.2)))
    f.add_trace(go.Scatter(x=times, y=direction, name="Yön (geldiği)", yaxis="y2", mode="markers",
                           marker=dict(size=3, color=GRAY)))
    f.update_layout(**_base(320, yaxis=dict(title=f"m/s · {unit}", gridcolor=GRID, zeroline=False),
                            yaxis2=dict(title="Yön", overlaying="y", side="right", range=[0, 360],
                                        tickvals=[0, 90, 180, 270, 360], ticktext=["K", "D", "G", "B", "K"],
                                        showgrid=False, zeroline=False)))
    return f


def scenario_monthly(runs) -> go.Figure:
    f = go.Figure()
    for r, c in zip(runs, [NEON, DEEP, GRAY, GRAY2, "#2b2b2b"]):
        f.add_trace(go.Bar(x=MONTHS_TR, y=r.monthly_import, name=r.code,
                           marker=dict(color=c, line=dict(width=0))))
    f.update_layout(**_base(300, "Aylık enerji açığı (şebekeden çekilen)", hovermode="x",
                            yaxis=dict(title="kWh", gridcolor=GRID, zeroline=False)),
                    barmode="group", bargap=0.2)
    return f


def daily_energy(days, pv_used, wind_used, batt, grid, produced, unit: str = "kWh") -> go.Figure:
    """Gün gün: tüketim nereden karşılandı (yığılı) + toplam üretim (çizgi)."""
    f = go.Figure()
    for name, vals, color in [("Güneşten", pv_used, NEON), ("Rüzgârdan", wind_used, DEEP),
                              ("Bataryadan", batt, GRAY), ("Şebekeden", grid, "#2b2b2b")]:
        f.add_trace(go.Bar(x=days, y=vals, name=name, marker=dict(color=color, line=dict(width=0))))
    f.add_trace(go.Scatter(x=days, y=produced, name="Toplam üretim", mode="lines+markers",
                           line=dict(color=NEON, width=1.5, dash="dot")))
    f.update_layout(**_base(300, "Günlük enerji: tüketim nereden karşılandı?", hovermode="x",
                            yaxis=dict(title=unit, gridcolor=GRID, zeroline=False)),
                    barmode="stack", bargap=0.45)
    return f
