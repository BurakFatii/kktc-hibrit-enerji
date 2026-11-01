"""Harita (ayrıntı): seçilen noktanın tüm verileri + kurulum önerileri."""
import reflex as rx

from ..components import error_box, kv_table, loading_line, page, status_badge
from ..core.config import REGION_KINDS, REGIONS
from ..olmap import ol_map
from ..state import MapState
from ..viz import compass, diverge, eyebrow, live_dot, meter, ok_icon, panel, tilt_view

K = MapState.kpi


def kktc_map(height: str = "480px") -> rx.Component:
    return ol_map(markers=MapState.markers, center=[35.25, 33.55], zoom=9, map_height=height,
                  tile_style=rx.color_mode_cond(light="light", dark="dark"),
                  zones_url="/kisit_bolgeleri.geojson", show_zones=MapState.show_zones,
                  solar=MapState.solar_field, show_solar=MapState.show_solar,
                  wind=MapState.wind_field, show_wind=MapState.show_wind,
                  on_pick=MapState.map_pick)


def zones_legend() -> rx.Component:
    """Uygunluk katmanı aç/kapa (renk lejantı kullanıcı kararıyla gösterilmez)."""
    return rx.hstack(
        rx.hstack(rx.switch(checked=MapState.show_zones, on_change=MapState.toggle_zones, size="1"),
                  rx.text("Uygunluk katmanı", size="1", weight="medium"), align="center", spacing="2"),
        spacing="4", wrap="wrap", align="center", width="100%",
    )


def layer_switch(checked, on_change, label: str, live: bool = False) -> rx.Component:
    return rx.hstack(rx.switch(checked=checked, on_change=on_change, size="1"),
                     rx.text(label, size="1", weight="medium"),
                     live_dot() if live else rx.fragment(), align="center", spacing="2")


def weather_layers() -> rx.Component:
    """Güneş ısı haritası ve rüzgâr akımı katmanları (başta kapalı)."""
    return rx.vstack(
        rx.flex(
            layer_switch(MapState.show_solar, MapState.toggle_solar, "Güneş ışınımı (yıllık)"),
            layer_switch(MapState.show_wind, MapState.toggle_wind, "Rüzgâr akımı (100 m)", live=True),
            wrap="wrap", align="center", width="100%", style={"gap": "8px 20px"},
        ),
        loading_line(MapState.layer_loading, "Katman verisi yükleniyor…"),
        rx.cond(MapState.layer_error != "", rx.text(MapState.layer_error, size="1", class_name="muted")),
        spacing="2", width="100%",
    )


def restriction_card(compact: bool = False) -> rx.Component:
    """Seçili nokta: rüzgâr ✓/✗, güneş ✓/✗ ve kısa kodlar (A03 Koruma alanı …)."""
    R = MapState.restrict
    code_row = lambda c: rx.hstack(  # noqa: E731
        rx.text(c["code"], size="1", weight="bold", class_name="mono",
                style={"color": R["color"], "minWidth": "2.6rem"}),
        rx.text(c["short"], size="1"),
        rx.cond(c["name"] != "", rx.text("· " + c["name"], size="1", class_name="muted")),
        spacing="1", align="center", custom_attrs={"title": c["detail"]})
    return rx.cond(
        R.length() > 0,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.box(width="10px", height="10px", style={"background": R["color"]}),
                    rx.text(R["label"], size="2", weight="bold"),
                    rx.spacer(),
                    ok_icon("wind", "Rüzgâr", R["wind_ok"]),
                    ok_icon("sun", "Güneş", R["solar_ok"]),
                    align="center", spacing="3", width="100%", wrap="wrap",
                ),
                rx.cond(MapState.restrict_codes.length() > 0,
                        rx.vstack(rx.foreach(MapState.restrict_codes, code_row), spacing="1", width="100%")),
                rx.fragment() if compact else rx.text(
                    "Kod üzerine gelince ayrıntı görünür. A: ikisine de kısıt · R: rüzgâr kısıtı · G: güneş kısıtı. "
                    "Kaynak OpenStreetMap; mesafeler yaklaşık planlama değeridir.", size="1", class_name="muted"),
                spacing="2", width="100%",
            ),
            class_name="panel", style={"borderLeft": "3px solid " + R["color"], "padding": "10px 12px"},
        ),
    )


KIND_ICON = {"ozet": "map-pin", "ruzgar": "wind", "gunes": "sun"}
KIND_DOT = {"ozet": "var(--muted)", "ruzgar": "#00A82D", "gunes": "var(--neon)"}


def region_buttons(kind: str) -> rx.Component:
    return rx.hstack(
        rx.hstack(rx.box(width="8px", height="8px", border_radius="50%", background=KIND_DOT[kind]),
                  rx.text(REGION_KINDS[kind], size="1", class_name="muted"),
                  align="center", spacing="2", min_width="12rem"),
        *[rx.button(rx.icon(KIND_ICON[kind], size=12), r.name, size="1", variant="outline",
                    on_click=MapState.pick_region(r.name)) for r in REGIONS if r.kind == kind],
        wrap="wrap", spacing="2", align="center",
    )


def region_card() -> rx.Component:
    R = MapState.region
    return rx.cond(
        R.length() > 0,
        panel(
            rx.vstack(
                rx.hstack(rx.heading(R["name"], size="4"), rx.text(R["kind"], size="1", class_name="mono muted"),
                          align="baseline", wrap="wrap", spacing="3"),
                rx.text(R["place"], size="1", class_name="muted"),
                rx.grid(
                    rx.cond(R["advantage"] != "", rx.box(
                        eyebrow("Avantaj"), rx.text(R["advantage"], size="2"),
                        style={"borderLeft": "2px solid var(--neon)", "paddingLeft": "10px"})),
                    rx.cond(R["challenge"] != "", rx.box(
                        eyebrow("Zorluk"), rx.text(R["challenge"], size="2"),
                        style={"borderLeft": "2px solid var(--muted)", "paddingLeft": "10px"})),
                    columns=rx.breakpoints(initial="1", md="2"), spacing="4", width="100%",
                ),
                rx.cond(MapState.claim_check != "", rx.box(
                    rx.hstack(rx.icon("scale", size=14), rx.text(MapState.claim_check, size="1"), align="start",
                              spacing="2"),
                    class_name="panel", style={"padding": "10px 12px", "borderColor": "var(--neon)"})),
                spacing="3", width="100%",
            ),
        ),
    )


def visual_kpis() -> rx.Component:
    return rx.grid(
        panel(rx.vstack(
            eyebrow("Güneş"),
            tilt_view(K["tilt"], "en iyi sabit açı " + K["tilt_label"]),
            meter("Sabit panel · kWh/kWp/yıl", K["yf"], K["yf_pct"]),
            meter("Takipçili panel · " + K["track_gain"], K["yt"], K["yt_pct"]),
            meter("Isıl kayıp · yıllık", K["thermal"], K["thermal_pct"], dim=True),
            meter("Isıl kayıp · Temmuz", K["thermal_jul"], K["thermal_jul_pct"], dim=True),
            spacing="3", width="100%")),
        panel(rx.vstack(
            eyebrow("Rüzgâr"),
            rx.hstack(
                rx.vstack(compass(K["prev_deg"], K["prev_label"], "110px"),
                          rx.text("hakim yön", size="1", class_name="muted"), align="center", spacing="1"),
                rx.vstack(compass(K["face_deg"], K["face_label"], "110px"),
                          rx.text("sabit türbin yönü", size="1", class_name="muted"), align="center", spacing="1"),
                justify="center", spacing="5", width="100%",
            ),
            meter("Ortalama hız · 100 m (10 m/s ölçeği)", K["v100"] + " m/s", K["v100_pct"]),
            meter("Kapasite faktörü", K["cf"], K["cf_pct"]),
            meter("Sabit yönlü türbin · kWh/kW/yıl", K["wf"], K["wf_pct"]),
            meter("Otomatik yönlenen türbin · " + K["auto_gain"], K["wa"], K["wa_pct"]),
            spacing="3", width="100%")),
        panel(rx.vstack(
            eyebrow("Hibrit · tamamlayıcılık testi"),
            diverge("Saatlik güneş–rüzgâr korelasyonu", K["corr"], K["corr_left"], K["corr_w"]),
            meter("Rüzgâr enerjisinin güneşsiz saatlerdeki payı", K["night"], K["night_pct"]),
            rx.text("Korelasyon negatif ve güneşsiz pay yüksekse iki kaynak birbirini tamamlar.",
                    size="1", class_name="muted"),
            rx.divider(margin_y="6px"),
            eyebrow("Kurulum önerisi · aşama 2"),
            rx.foreach(MapState.advice, lambda a: rx.hstack(
                rx.box(width="6px", height="6px", background="var(--neon)", margin_top="7px", flex_shrink="0"),
                rx.text(a, size="2"), align="start", spacing="2")),
            spacing="3", width="100%")),
        columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%",
    )


def techniques() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Bu noktada kullanılabilecek üretim teknikleri"),
            rx.foreach(MapState.techniques, lambda t: rx.hstack(
                rx.vstack(rx.text(t["name"], size="2", weight="medium"),
                          rx.text(t["note"], size="1", class_name="muted"), spacing="0"),
                rx.spacer(),
                status_badge(t["status"]),
                width="100%", padding_y="0.4rem", border_bottom="1px solid var(--line)", align="center")),
            spacing="1", width="100%",
        ),
    )


def harita() -> rx.Component:
    return page(
        rx.vstack(
            rx.button(rx.icon("locate", size=14), "Konumumu analiz et", size="2", variant="outline",
                      on_click=MapState.use_my_location),
            *[region_buttons(k) for k in REGION_KINDS],
            spacing="2", width="100%",
        ),
        rx.box(kktc_map(), class_name="panel", padding="0", overflow="hidden"),
        zones_legend(),
        weather_layers(),
        rx.text("Haritada herhangi bir noktaya tıklayın. Siyah: konumunuz · beyaz: seçili nokta. Kısıt mesafeleri "
                "(havalimanı ~5 km, yerleşim 0,3–1,5 km) yaklaşık planlama değerleridir; kesin sınır için kurum izni gerekir.",
                size="1", class_name="muted"),
        error_box(MapState.error),
        region_card(),
        restriction_card(),
        loading_line(MapState.loading, "Geçmiş yılın saatlik verisi alınıyor ve analiz ediliyor…"),
        rx.cond(
            MapState.has_sel & (MapState.cell != ""),
            rx.vstack(
                rx.hstack(
                    rx.text(MapState.sel_lat.to_string() + ", " + MapState.sel_lon.to_string(), size="2",
                            weight="bold", class_name="mono"),
                    rx.text(MapState.cell, size="1", class_name="muted mono"),
                    wrap="wrap", align="center", spacing="3",
                ),
                rx.text(MapState.live, size="2", class_name="muted"),
                visual_kpis(),
                techniques(),
                rx.grid(
                    panel(rx.plotly(data=MapState.fig_monthly, width="100%")),
                    panel(eyebrow("Rüzgâr gülü · saat %"), rx.plotly(data=MapState.fig_rose, width="100%")),
                    columns=rx.breakpoints(initial="1", md="2"), spacing="3", width="100%",
                ),
                panel(rx.plotly(data=MapState.fig_wind_heat, width="100%")),
                rx.el.details(
                    rx.el.summary(rx.text("Tüm değerler (tablo)", as_="span", weight="medium"),
                                  style={"cursor": "pointer"}),
                    rx.grid(kv_table(MapState.solar_rows, "Güneş"), kv_table(MapState.wind_rows, "Rüzgâr"),
                            kv_table(MapState.hybrid_rows, "Hibrit"),
                            columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%",
                            padding_top="8px"),
                    width="100%",
                ),
                spacing="4", width="100%",
            ),
        ),
        title="Harita ve konum analizi",
        back=("Veriler", "/veriler"),
    )
