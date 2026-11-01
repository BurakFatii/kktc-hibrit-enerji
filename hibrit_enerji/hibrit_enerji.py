"""KKTC Hibrit Enerji — Reflex uygulaması."""

import reflex as rx

from .pages.analiz import analiz
from .pages.ayarlar import ayarlar
from .pages.harita import harita
from .pages.home import home
from .pages.mimari import mimari
from .pages.senaryolar import senaryolar
from .pages.sistem import sistem
from .pages.veriler import veriler
from .state import AnalysisState, AppState, HomeState, MapState, ScenarioState

app = rx.App(
    theme=rx.theme(
        accent_color="green",
        gray_color="gray",
        radius="small",
        panel_background="solid",
    ),
    stylesheets=["/theme.css"],
    html_lang="tr",  # büyük harf dönüşümü Türkçe kurallarla (i -> İ)
)

TITLE = "CYNGERGY"
app.add_page(
    home, route="/", title=TITLE, on_load=[AppState.load_settings, HomeState.start]
)
app.add_page(
    sistem,
    route="/sistem",
    title=f"Sistem ayrıntıları · {TITLE}",
    on_load=[AppState.load_settings, HomeState.start],
)
app.add_page(
    veriler,
    route="/veriler",
    title=f"Veriler · {TITLE}",
    on_load=[AppState.load_settings, MapState.start_summary],
)
app.add_page(
    harita,
    route="/veriler/harita",
    title=f"Harita · {TITLE}",
    on_load=[AppState.load_settings, MapState.start],
)
app.add_page(
    analiz,
    route="/veriler/analiz",
    title=f"Üretim · {TITLE}",
    on_load=[AppState.load_settings, AnalysisState.start],
)
app.add_page(
    senaryolar,
    route="/veriler/senaryolar",
    title=f"Senaryolar · {TITLE}",
    on_load=[AppState.load_settings, ScenarioState.start],
)
app.add_page(
    ayarlar,
    route="/ayarlar",
    title=f"Ayarlar · {TITLE}",
    on_load=AppState.load_settings,
)
app.add_page(mimari, route="/nasil-calisir", title=f"Nasıl Çalışır · {TITLE}")

# Eski adresler -> yeni yerleri
for old, new in [
    ("/harita", "/veriler/harita"),
    ("/analiz", "/veriler/analiz"),
    ("/senaryolar", "/veriler/senaryolar"),
]:
    app.add_page(rx.fragment, route=old, on_load=rx.redirect(new))
