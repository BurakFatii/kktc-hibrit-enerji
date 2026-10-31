"""Veriler: harita, üretim ve senaryoların toplu özeti; ayrıntı için 'Tümünü göster'."""
import reflex as rx

from ..components import error_box, loading_line, page, section
from ..state import AnalysisState, MapState, ScenarioState
from ..viz import bar_list, city_panel, eyebrow, meter, panel
from .harita import kktc_map, restriction_card, zones_legend

K = MapState.kpi
A = AnalysisState.kpi
S = ScenarioState.smart


def map_section() -> rx.Component:
    summary = panel(
        rx.cond(
            K.length() > 0,
            rx.vstack(
                rx.text(MapState.sel_label, size="4", weight="bold"),
                restriction_card(compact=True),
                eyebrow("Bir yılda ne üretir?"),
                meter("1 kW güneş paneli", K["yf"] + " kWh", K["yf_rel"]),
                meter("1 kW rüzgâr türbini", K["wa"] + " kWh", K["wa_rel"]),
                spacing="3", width="100%",
            ),
            rx.vstack(loading_line(MapState.loading, "Nokta analiz ediliyor…"),
                      rx.text("Haritada bir noktaya tıklayın.", size="2", class_name="muted")),
        ),
    )
    return section(
        "Konum", "01 · Haritada seçilen nokta tüm sayfayı belirler",
        rx.grid(
            rx.box(rx.box(kktc_map("420px"), class_name="panel", padding="0", overflow="hidden"),
                   grid_column=rx.breakpoints(initial="span 1", md="span 2")),
            summary,
            columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%",
        ),
        zones_legend(),
        error_box(MapState.error),
        href="/veriler/harita",
    )


def production_section() -> rx.Component:
    return section(
        "Üretim", "02 · " + AnalysisState.place,
        error_box(AnalysisState.error),
        rx.grid(
            rx.box(panel(eyebrow("Önümüzdeki 48 saat (MW)"), rx.plotly(data=AnalysisState.fig_forecast, width="100%")),
                   grid_column=rx.breakpoints(initial="span 1", md="span 2")),
            panel(city_panel(AnalysisState.city, compact=True)),
            columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%",
        ),
        loading_line(AnalysisState.loading),
        href="/veriler/analiz",
    )


def scenario_section() -> rx.Component:
    return section(
        "Senaryolar", "03 · " + ScenarioState.place,
        error_box(ScenarioState.error),
        loading_line(ScenarioState.loading, "Bölgeler simüle ediliyor…"),
        rx.cond(
            ScenarioState.rows.length() > 0,
            rx.grid(
                panel(rx.vstack(
                    eyebrow("İlçenin ihtiyacının karşılanan kısmı"),
                    bar_list(ScenarioState.rows, "ad", "ozv", "oz"),
                    spacing="3", width="100%")),
                panel(rx.vstack(
                    eyebrow("En ekonomik kurulum"),
                    rx.text(S["best"], size="4", weight="bold", class_name="mono"),
                    meter("İhtiyacın karşılanan kısmı", S["best_oz"], S["best_oz_pct"]),
                    spacing="3", width="100%")),
                columns=rx.breakpoints(initial="1", md="2"), spacing="3", width="100%",
            ),
            rx.cond(ScenarioState.conclusion.length() > 0,
                    rx.text(ScenarioState.conclusion[0], size="2", style={"color": "var(--bad)"})),
        ),
        href="/veriler/senaryolar",
    )


def veriler() -> rx.Component:
    return page(
        map_section(),
        rx.divider(),
        production_section(),
        rx.divider(),
        scenario_section(),
        nav="/veriler",
        title="Veriler",
        subtitle="Haritada bir nokta seçin; o nokta ve ilçesi için özet. Ayrıntı: 'Tümünü göster'.",
    )
