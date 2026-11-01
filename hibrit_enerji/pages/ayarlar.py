"""Ayarlar: cihaz etiketinden okunabilen değerler. Algoritma bunları modele çevirir."""
import reflex as rx

from ..components import page
from ..core.spec import LOAD_PROFILES, PV_MOUNTS, WIND_YAW
from ..state import AppState
from ..viz import eyebrow, panel

YES_NO = {"evet": "Evet", "hayır": "Hayır"}

# (alan, etiket, nerede bulunur / ne demek, tür)  tür: "num" ya da seçenek sözlüğü
SECTIONS = [
    ("Güneş paneli", "sun", [
        ("pv_mount", "Kurulum tipi", "Takipçili sistem daha çok üretir, sabit sistem daha ucuzdur.", PV_MOUNTS),
        ("panel_wp", "Panel gücü (W)", "Panel etiketinde 'Pmax' veya 'Maximum Power'.", "num"),
        ("panel_count", "Panel adedi", "Çatıdaki toplam panel sayısı.", "num"),
        ("inverter_eff_pct", "İnverter verimi (%)", "İnverter etiketinde 'Max. efficiency'.", "num"),
        ("auto_orient", "Açıyı uygulama belirlesin", "Sabit panelde en iyi eğim ve yön konuma göre hesaplanır.", YES_NO),
    ]),
    ("Rüzgâr türbini", "wind", [
        ("wind_rated_kw", "Türbin gücü (kW)", "Etikette 'Rated power'. Türbin yoksa 0 yazın.", "num"),
        ("hub_height_m", "Kule yüksekliği (m)", "Rotor merkezinin yerden yüksekliği.", "num"),
        ("wind_yaw", "Yönlenme", "Otomatik dönen türbin rüzgârı takip eder; sabit türbin ucuzdur.", WIND_YAW),
        ("auto_wind_dir", "Sabit yönü uygulama belirlesin", "Sabit türbinin en iyi yönü konuma göre hesaplanır.", YES_NO),
    ]),
    ("Batarya", "battery", [
        ("battery_kwh", "Kapasite (kWh)", "Batarya etiketinde 'Energy' veya 'Capacity'. Yoksa 0.", "num"),
        ("battery_power_kw", "Şarj/deşarj gücü (kW)", "Etikette 'Max. continuous power'.", "num"),
    ]),
    ("Tüketim ve şebeke", "house", [
        ("monthly_kwh", "Aylık tüketim (kWh)", "Tesisin elektrik faturasındaki aylık tüketim.", "num"),
        ("load_profile", "Tesis tipi", "Kamu/yerleşke akşam, ticari/sanayi tesisi gündüz daha çok tüketir.", LOAD_PROFILES),
        ("export_limit_kw", "Şebekeye verme sınırı (kW)", "Dağıtım şirketinin izin verdiği en yüksek güç. 0 = vermez.", "num"),
    ]),
]

ADVANCED = [
    ("Panel ayrıntıları", [
        ("temp_coeff_pct", "Sıcaklık katsayısı Pmax (%/°C)", "Panel kataloğunda, genelde −0,30 ile −0,45.", "num"),
        ("noct_c", "NOCT (°C)", "Panel kataloğunda, genelde 42–46.", "num"),
        ("fixed_tilt_deg", "Elle eğim (°)", "Yalnızca 'açıyı uygulama belirlesin' = Hayır ise.", "num"),
        ("fixed_azimuth_deg", "Elle yön (°, 180 = güney)", "Yalnızca 'açıyı uygulama belirlesin' = Hayır ise.", "num"),
    ]),
    ("Türbin ayrıntıları", [
        ("wind_cut_in_ms", "Devreye girme hızı (m/s)", "Katalogda 'Cut-in wind speed'.", "num"),
        ("wind_rated_ms", "Anma hızı (m/s)", "Katalogda 'Rated wind speed'.", "num"),
        ("wind_cut_out_ms", "Durma hızı (m/s)", "Katalogda 'Cut-out wind speed'.", "num"),
        ("wind_power_curve", "Güç eğrisi tablosu (isteğe bağlı)",
         "Katalogdaki tablo, 'hız:güç(W)' çiftleri: 3:0, 5:400, 8:1500, 11:3000. Boşsa yukarıdaki hızlardan üretilir.",
         "text"),
        ("wind_fixed_dir_deg", "Elle türbin yönü (°)", "Sabit türbin rüzgârın geldiği bu yöne bakar.", "num"),
    ]),
    ("Batarya ayrıntıları", [
        ("battery_dod_pct", "Kullanılabilir derinlik (%)", "Katalogda 'DoD'. LiFePO4 için ~90.", "num"),
        ("battery_rt_eff_pct", "Gidiş-dönüş verimi (%)", "Katalogda 'Round-trip efficiency'.", "num"),
    ]),
    ("Maliyet varsayımları (USD)", [
        ("cost_pv_usd_per_wp", "Panel + inverter + montaj ($/W)", "Yerel tekliflerle güncelleyin.", "num"),
        ("cost_tracker_usd_per_wp", "Takipçi ek maliyeti ($/W)", "", "num"),
        ("cost_wind_usd_per_kw", "Küçük türbin kurulu ($/kW)", "", "num"),
        ("cost_battery_usd_per_kwh", "Batarya kurulu ($/kWh)", "", "num"),
        ("price_import_usd_kwh", "Elektrik alış fiyatı ($/kWh)", "", "num"),
        ("price_export_usd_kwh", "Şebekeye satış fiyatı ($/kWh)", "", "num"),
        ("cost_pv_utility_usd_per_wp", "Santral ölçeği güneş ($/W)", "Veriler sayfasındaki şehir hesabında.", "num"),
        ("cost_wind_utility_usd_per_kw", "Santral ölçeği rüzgâr ($/kW)", "MW sınıfı türbin, kurulu.", "num"),
        ("cost_battery_utility_usd_per_kwh", "Santral ölçeği batarya ($/kWh)", "", "num"),
    ]),
]


def field(name: str, label: str, help_text: str, kind) -> rx.Component:
    if kind in ("num", "text"):
        control = rx.input(name=name, default_value=AppState.form[name], type="text",
                           input_mode="decimal" if kind == "num" else "text", width="100%")
    else:
        control = rx.select.root(
            rx.select.trigger(width="100%"),
            rx.select.content(*[rx.select.item(v, value=k) for k, v in kind.items()]),
            name=name, default_value=AppState.form[name],
        )
    return rx.vstack(
        rx.text(label, size="2", weight="medium"),
        control,
        rx.text(help_text, size="1", class_name="muted") if help_text else rx.fragment(),
        spacing="1", width="100%",
    )


def section(title: str, icon: str, fields) -> rx.Component:
    return panel(
        rx.vstack(
            rx.hstack(rx.icon(icon, size=16, color="var(--neon)"), eyebrow(title), align="center"),
            rx.grid(*[field(*f) for f in fields], columns=rx.breakpoints(initial="1", sm="2"),
                    spacing="4", width="100%"),
            spacing="3", width="100%",
        ),
    )


def ayarlar() -> rx.Component:
    return page(
        rx.form(
            rx.vstack(
                *[section(t, i, f) for t, i, f in SECTIONS],
                # <details> içerik kapalıyken de DOM'da kalır; form değerleri kaybolmaz.
                rx.el.details(
                    rx.el.summary(rx.text("Gelişmiş: katalog ayrıntıları ve maliyet varsayımları",
                                          as_="span", weight="medium"), cursor="pointer"),
                    rx.vstack(*[section(t, "settings-2", f) for t, f in ADVANCED],
                              spacing="3", padding_top="0.75rem", width="100%"),
                    width="100%",
                ),
                rx.hstack(
                    rx.button(rx.icon("save", size=16), "Kaydet", type="submit", size="3"),
                    rx.button("Varsayılana dön", type="button", variant="soft", color_scheme="gray",
                              size="3", on_click=AppState.reset_settings),
                ),
                spacing="4", width="100%",
            ),
            on_submit=AppState.save_settings, reset_on_submit=False,
            key=AppState.form_rev.to_string(), width="100%",
        ),
        nav="/ayarlar",
        title="Ayarlar",
    )
