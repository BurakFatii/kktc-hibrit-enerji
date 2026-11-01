"""Üretim analizi: grafikler ve tablo (ana sayfadan ayrı)."""
import reflex as rx

from ..components import error_box, loading_line, page
from ..core.analysis import MONTHS_TR
from ..state import AnalysisState
from ..viz import city_panel, panel

COLS = ["Saat", "Güneş MW", "Rüzgâr MW", "Rüzgâr m/s", "Yön", "İhtiyaç MW", "Batarya", "Mod"]


def chart(fig) -> rx.Component:
    return panel(rx.plotly(data=fig, width="100%"))


def table() -> rx.Component:
    return rx.box(
        rx.table.root(
            rx.table.header(rx.table.row(*[rx.table.column_header_cell(c) for c in COLS])),
            rx.table.body(rx.foreach(AnalysisState.table, lambda row: rx.table.row(
                rx.foreach(row, lambda cell: rx.table.cell(cell))))),
            size="1", variant="ghost", width="100%",
        ),
        overflow_x="auto", width="100%",
    )


def analiz() -> rx.Component:
    return page(
        error_box(AnalysisState.error),
        loading_line(AnalysisState.loading),
        panel(city_panel(AnalysisState.city)),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("48 saat tahmin", value="tahmin"),
                rx.tabs.trigger("Rüzgâr (geçmiş yıl)", value="ruzgar"),
                rx.tabs.trigger("Güneş (geçmiş yıl)", value="gunes"),
                rx.tabs.trigger("Saatlik tablo", value="tablo"),
            ),
            rx.tabs.content(rx.vstack(chart(AnalysisState.fig_forecast), chart(AnalysisState.fig_daily),
                                      padding_y="1rem", width="100%"), value="tahmin"),
            rx.tabs.content(
                rx.vstack(
                    rx.hstack(
                        rx.text("Ay:", size="2"),
                        rx.select.root(
                            rx.select.trigger(),
                            rx.select.content(*[rx.select.item(m, value=str(i + 1))
                                                for i, m in enumerate(MONTHS_TR)]),
                            value=AnalysisState.month, on_change=AnalysisState.set_month, size="1",
                        ),
                        align="center",
                    ),
                    chart(AnalysisState.fig_wind_series),
                    rx.grid(chart(AnalysisState.fig_wind_heat), chart(AnalysisState.fig_rose),
                            columns=rx.breakpoints(initial="1", md="2"), spacing="3", width="100%"),
                    rx.text(AnalysisState.hist_note, size="1", color_scheme="gray"),
                    padding_y="1rem", width="100%",
                ),
                value="ruzgar",
            ),
            rx.tabs.content(
                rx.vstack(chart(AnalysisState.fig_pv_heat), chart(AnalysisState.fig_monthly),
                          padding_y="1rem", width="100%"),
                value="gunes",
            ),
            rx.tabs.content(rx.vstack(table(), padding_y="1rem", width="100%"), value="tablo"),
            default_value="tahmin", width="100%",
        ),
        title="Üretim",
        back=("Veriler", "/veriler"),
    )
