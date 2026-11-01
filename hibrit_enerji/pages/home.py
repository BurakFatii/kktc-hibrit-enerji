"""Ana sayfa: tesisin ŞU AN durumu — yalnızca özet. Ayrıntılar: /sistem."""

import reflex as rx

from ..components import error_box, loading_line, page
from ..state import HomeState
from ..viz import battery, big_number, day_strip, eyebrow, panel, power_flow, stack_bar

D = HomeState.data


def now_panel() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Sistem şu an"),
            rx.heading(
                D["mode_title"],
                size="7",
                weight="bold",
                class_name="ink",
                style={"letterSpacing": ".02em"},
            ),
            power_flow(D),
            spacing="2",
            width="100%",
        ),
    )


def side_panel() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Batarya"),
            battery(D["soc_pct"], D["soc_now"], D["soc_low"] == "1"),
            rx.divider(margin_y="8px"),
            eyebrow("Bugün yenilenebilirden karşılanan"),
            big_number(D["t_green"], "", "8"),
            stack_bar(
                [
                    (D["t_pv_pct"], "var(--neon)", "Güneş", ""),
                    (D["t_wind_pct"], "#00A82D", "Rüzgâr", ""),
                    (D["t_batt_pct"], "var(--muted)", "Batarya", ""),
                    (D["t_grid_pct"], "var(--fg)", "Şebeke", ""),
                ],
                height="14px",
            ),
            spacing="2",
            width="100%",
        ),
    )


def home() -> rx.Component:
    return page(
        error_box(HomeState.error),
        loading_line(
            HomeState.loading & (D.length() == 0), "Konum ve hava verisi alınıyor…"
        ),
        rx.cond(
            D.length() > 0,
            rx.vstack(
                rx.grid(
                    rx.box(
                        now_panel(),
                        grid_column=rx.breakpoints(initial="span 1", md="span 2"),
                    ),
                    side_panel(),
                    columns=rx.breakpoints(initial="1", md="3"),
                    spacing="3",
                    width="100%",
                ),
                panel(eyebrow("Önümüzdeki 24 saat"), day_strip(HomeState.strip)),
                rx.hstack(
                    rx.link(
                        rx.button(
                            "Tümünü göster",
                            rx.icon("arrow-right", size=14),
                            variant="outline",
                            size="2",
                        ),
                        href="/sistem",
                        underline="none",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon("refresh-cw", size=14),
                        "Yenile",
                        size="1",
                        variant="ghost",
                        on_click=HomeState.refresh,
                        loading=HomeState.loading,
                    ),
                    width="100%",
                    align="center",
                ),
                spacing="3",
                width="100%",
            ),
        ),
        nav="/",
        title="",
    )
