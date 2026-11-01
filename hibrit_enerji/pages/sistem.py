"""Sistem ayrıntıları (Ana Sayfa › Tümünü göster): tesisin anlık ve günlük tüm verileri."""
import reflex as rx

from ..components import error_box, loading_line, page
from ..state import HomeState
from ..viz import (battery, big_number, compass, day_strip, eyebrow, meter, panel, stack_bar, sun_arc,
                   tilt_view)

D = HomeState.data


def meters_panel() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Şu an · kapasite kullanımı"),
            meter("Güneş panelleri şu an kapasitenin", D["pv_now"] + " kW", D["pv_pct"]),
            meter("Rüzgâr türbini şu an kapasitenin", D["wind_now"] + " kW", D["wind_pct"]),
            meter("Tesis tüketimi (günün en yükseğine göre)", D["load_now"] + " kW", D["load_pct"], dim=True),
            rx.divider(margin_y="6px"),
            meter("Önümüzdeki 24 saatte üretim tüketimi karşılıyor mu?", D["prod24"] + " / " + D["load24"] + " kWh",
                  D["cover24"]),
            spacing="3", width="100%",
        ),
    )


def today_panel() -> rx.Component:
    def num(label: str, value, unit: str = "kWh") -> rx.Component:
        return rx.vstack(rx.text(label, size="1", class_name="muted"), big_number(value, unit, "6"), spacing="0")

    return panel(
        rx.vstack(
            rx.hstack(eyebrow("Bugün"), rx.spacer(),
                      rx.text("00:00–24:00 · kalan saatler tahmin", size="1", class_name="muted mono"),
                      width="100%"),
            rx.grid(
                num("Toplam tüketim", D["t_load"]),
                num("Güneşten üretilen", D["t_pv_gen"]),
                num("Rüzgârdan üretilen", D["t_wind_gen"]),
                num("Şebekeden alınan", D["t_grid"]),
                num("Şebekeye verilen", D["t_exp"]),
                columns=rx.breakpoints(initial="2", md="5"), spacing="4", width="100%",
            ),
            rx.text("Tüketim nereden karşılandı?", size="2", weight="medium", padding_top="4px"),
            stack_bar([
                (D["t_pv_pct"], "var(--neon)", "Güneş", D["t_pv"] + " kWh"),
                (D["t_wind_pct"], "#00A82D", "Rüzgâr", D["t_wind"] + " kWh"),
                (D["t_batt_pct"], "var(--muted)", "Batarya", D["t_batt"] + " kWh"),
                (D["t_grid_pct"], "var(--fg)", "Şebeke", D["t_grid"] + " kWh"),
            ]),
            rx.text("Güneş, rüzgâr ve bataryadan karşılanan pay: ", rx.text.strong(D["t_green"], class_name="ink"),
                    size="2"),
            spacing="3", width="100%",
        ),
    )


def solar_panel() -> rx.Component:
    return panel(
        rx.vstack(
            rx.hstack(eyebrow("Güneş paneli"), rx.spacer(),
                      rx.text(rx.cond(D["mount"] == "takipci", "çift eksen takipçi", "sabit montaj"),
                              size="1", class_name="mono muted")),
            tilt_view(D["tilt"], D["tilt_label"]),
            sun_arc(D["sun_x"], D["sun_y"], D["sun_up"], D["sun_label"]),
            rx.text(D["pv_dir"], size="1", class_name="muted"),
            spacing="2", width="100%",
        ),
    )


def wind_panel() -> rx.Component:
    return panel(
        rx.vstack(
            rx.hstack(eyebrow("Rüzgâr türbini"), rx.spacer(),
                      rx.text(rx.cond(D["yaw"] == "otomatik", "otomatik yönlenen", "sabit yönlü"),
                              size="1", class_name="mono muted")),
            rx.center(compass(D["wind_deg"], D["wind_ms"] + " m/s", size="150px"), width="100%"),
            rx.text(D["wind_dir"], size="1", class_name="muted"),
            spacing="2", width="100%",
        ),
    )


def outlook_panel() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Önümüzdeki 24 saat"),
            day_strip(HomeState.strip),
            rx.vstack(
                rx.foreach(HomeState.outlook, lambda t: rx.hstack(
                    rx.box(width="6px", height="6px", background="var(--neon)", margin_top="7px", flex_shrink="0"),
                    rx.text(t, size="2"), align="start", spacing="2")),
                spacing="1", padding_top="6px", width="100%",
            ),
            spacing="2", width="100%",
        ),
    )


def flows_panel() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Anlık güç akışı · " + D["mode_title"]),
            rx.text(D["mode_text"], size="2", class_name="muted"),
            battery(D["soc_pct"], D["soc_now"], D["soc_low"] == "1"),
            rx.foreach(HomeState.flows, lambda f: rx.hstack(
                rx.text(f["label"], size="2", class_name="muted"), rx.spacer(),
                rx.text(f["value"], size="2", weight="bold", class_name="mono"),
                width="100%", border_bottom="1px solid var(--line)", padding_y="4px")),
            spacing="2", width="100%",
        ),
    )


def sistem() -> rx.Component:
    return page(
        error_box(HomeState.error),
        loading_line(HomeState.loading & (D.length() == 0), "Konum ve hava verisi alınıyor…"),
        rx.cond(
            D.length() > 0,
            rx.vstack(
                rx.grid(flows_panel(), meters_panel(), columns=rx.breakpoints(initial="1", md="2"),
                        spacing="3", width="100%"),
                today_panel(),
                rx.grid(solar_panel(), wind_panel(), outlook_panel(),
                        columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%"),
                rx.text(D["weather"], " · son güncelleme ", D["updated"],
                        " · tüketim ve batarya, sayaç/BMS bağlanana kadar fatura değerinden simüle edilir.",
                        size="1", class_name="muted"),
                spacing="3", width="100%",
            ),
        ),
        title="Sistem ayrıntıları",
        back=("Ana Sayfa", "/"),
    )
