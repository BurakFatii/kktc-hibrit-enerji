"""Reflex state'leri. Hesaplar services.py'de; burada yalnızca akış ve ekran durumu var."""
from __future__ import annotations

import asyncio
import json
from typing import Any

import plotly.graph_objects as go
import reflex as rx

from . import charts, services
from .core.config import (FALLBACK_LOCATION, REGION_BY_NAME, REGION_KINDS, REGIONS,
                          nearest_region)
from .core.spec import SystemSpec

GEO_JS = """
new Promise((resolve) => {
  if (!navigator.geolocation) { resolve({ok: false, error: "Tarayıcı konum desteklemiyor."}); return; }
  navigator.geolocation.getCurrentPosition(
    (p) => resolve({ok: true, lat: p.coords.latitude, lon: p.coords.longitude, acc: p.coords.accuracy}),
    (e) => resolve({ok: false, error: e.message || "Konum izni verilmedi."}),
    {enableHighAccuracy: true, timeout: 10000, maximumAge: 300000}
  );
})
"""


class AppState(rx.State):
    """Ayarlar (tarayıcıda saklanır) + anlık konum."""

    settings_json: str = rx.LocalStorage("", name="kktc_hibrit_ayarlar", sync=True)
    form: dict[str, str] = SystemSpec().to_form()
    form_rev: int = 0

    lat: float = FALLBACK_LOCATION["lat"]
    lon: float = FALLBACK_LOCATION["lon"]
    loc_status: str = "yok"  # yok | bekliyor | tamam | yedek
    loc_note: str = ""

    def _spec(self) -> SystemSpec:
        return SystemSpec.from_dict(self.form)

    def _apply_location(self, result: dict | None):
        if result and result.get("ok"):
            self.lat = float(result["lat"])
            self.lon = float(result["lon"])
            self.loc_status = "tamam"
            acc = result.get("acc")
            self.loc_note = f"±{acc:.0f} m" if isinstance(acc, (int, float)) else ""
        else:
            self.lat, self.lon = FALLBACK_LOCATION["lat"], FALLBACK_LOCATION["lon"]
            self.loc_status = "yedek"
            err = (result or {}).get("error", "")
            self.loc_note = f"Konum alınamadı ({err}). {FALLBACK_LOCATION['name']} gösteriliyor."

    @rx.var
    def loc_text(self) -> str:
        if self.loc_status == "bekliyor":
            return "Konum alınıyor…"
        if self.loc_status == "yok":
            return "Konum bekleniyor"
        return f"{self.lat:.4f}, {self.lon:.4f}"

    @rx.event
    def load_settings(self):
        try:
            data = json.loads(self.settings_json) if self.settings_json else {}
        except (ValueError, TypeError):
            data = {}
        self.form = SystemSpec.from_dict(data).to_form()
        self.form_rev += 1

    @rx.event
    def save_settings(self, data: dict):
        merged = {**self.form, **{k: str(v) for k, v in data.items()}}
        spec = SystemSpec.from_dict(merged)
        self.form = spec.to_form()
        self.settings_json = json.dumps(spec.to_dict())
        self.form_rev += 1
        return rx.toast.success("Ayarlar kaydedildi. Tüm sayfalar yeni değerlerle hesaplanacak.")

    @rx.event
    def reset_settings(self):
        self.form = SystemSpec().to_form()
        self.settings_json = ""
        self.form_rev += 1
        return rx.toast.info("Varsayılan değerlere dönüldü.")


async def _location(state: rx.State, force: bool, callback) -> object | None:
    """Konum yoksa tarayıcıdan iste; varsa None döndür (sayfa doğrudan hesaplar)."""
    app = await state.get_state(AppState)
    if not force and app.loc_status in ("tamam", "yedek"):
        return None
    app.loc_status = "bekliyor"
    return rx.call_script(GEO_JS, callback=callback)


SELECTED = "Seçili nokta"


async def _target(state: rx.State) -> tuple[float, float, str]:
    """Veriler hesaplarının hedefi: haritada seçili nokta; seçim yoksa cihaz konumu."""
    m = await state.get_state(MapState)
    if m.has_sel:
        label = m.region.get("name", "") if m.region else ""
        return m.sel_lat, m.sel_lon, label or f"{m.sel_lat:.4f}, {m.sel_lon:.4f}"
    app = await state.get_state(AppState)
    return app.lat, app.lon, "Konumunuz"


# ======================================================================= ANA SAYFA
class HomeState(rx.State):
    loading: bool = False
    error: str = ""
    data: dict[str, str] = {}
    flows: list[dict[str, str]] = []
    outlook: list[str] = []
    strip: list[dict[str, str]] = []

    @rx.event
    async def start(self):
        ev = await _location(self, False, HomeState.on_location)
        return ev or HomeState.refresh

    @rx.event
    async def relocate(self):
        return await _location(self, True, HomeState.on_location)

    @rx.event
    async def on_location(self, result: dict):
        app = await self.get_state(AppState)
        app._apply_location(result)
        return HomeState.refresh

    @rx.event
    async def refresh(self):
        self.loading, self.error = True, ""
        yield
        app = await self.get_state(AppState)
        spec, lat, lon = app._spec(), app.lat, app.lon
        try:
            d = await asyncio.to_thread(services.home_snapshot, spec, lat, lon)
        except Exception as e:  # ağ hatası vb.
            self.error = f"Veri alınamadı: {e}"
            self.loading = False
            return
        self.flows = d.pop("flows")
        self.outlook = d.pop("outlook")
        self.strip = d.pop("strip")
        self.data = {k: str(v) for k, v in d.items()}
        self.loading = False


# ======================================================================= HARİTA
class MapState(rx.State):
    markers: list[dict[str, Any]] = []
    kpi: dict[str, str] = {}
    restrict: dict[str, str] = {}
    restrict_codes: list[dict[str, str]] = []
    show_zones: bool = True
    region: dict[str, str] = {}
    claim_check: str = ""
    sel_lat: float = 0.0
    sel_lon: float = 0.0
    has_sel: bool = False
    loading: bool = False
    error: str = ""
    cell: str = ""
    live: str = ""
    solar_rows: list[dict[str, str]] = []
    wind_rows: list[dict[str, str]] = []
    hybrid_rows: list[dict[str, str]] = []
    techniques: list[dict[str, str]] = []
    advice: list[str] = []
    fig_monthly: go.Figure = charts.empty()
    fig_rose: go.Figure = charts.empty()
    fig_wind_heat: go.Figure = charts.empty()

    @rx.event
    async def start(self):
        ev = await _location(self, False, MapState.on_location)
        if ev:
            return ev
        await self._redraw()

    @rx.event
    async def on_location(self, result: dict):
        app = await self.get_state(AppState)
        app._apply_location(result)
        await self._redraw()

    @rx.var
    def sel_label(self) -> str:
        """Veriler sayfasındaki tüm hesapların hedefi olan nokta."""
        if not self.has_sel:
            return ""
        if self.region:
            return self.region.get("name", "")
        return f"{self.sel_lat:.4f}, {self.sel_lon:.4f}"

    @rx.event
    def toggle_zones(self, value: bool):
        self.show_zones = value

    @rx.event
    async def start_summary(self):
        """Veriler sayfası: seçim yoksa konumu seçip özeti doldur."""
        ev = await _location(self, False, MapState.on_location_summary)
        if ev:
            return ev
        await self._redraw()
        # Seçim varsa güncel ayarlarla yeniden hesapla (analiz -> üretim -> senaryolar zinciri)
        return MapState.analyze if self.has_sel else MapState.use_my_location

    @rx.event
    async def on_location_summary(self, result: dict):
        app = await self.get_state(AppState)
        app._apply_location(result)
        await self._redraw()
        return MapState.analyze if self.has_sel else MapState.use_my_location

    async def _redraw(self):
        app = await self.get_state(AppState)
        m = [{"center": [r.lat, r.lon], "name": r.name, "color": charts.KIND_COLORS[r.kind], "radius": 6}
             for r in REGIONS]
        if app.loc_status == "tamam":
            m.append({"center": [app.lat, app.lon], "name": "Konumum", "color": "#000000",
                      "stroke": "#ffffff", "radius": 7, "z": 5})
        if self.has_sel:
            m.append({"center": [self.sel_lat, self.sel_lon], "name": "Seçili nokta",
                      "color": "#ffffff", "stroke": charts.NEON, "radius": 11, "z": 10})
        self.markers = m

    @rx.event
    async def map_pick(self, lat: float, lng: float):
        self.sel_lat, self.sel_lon, self.has_sel = round(float(lat), 4), round(float(lng), 4), True
        r = nearest_region(self.sel_lat, self.sel_lon)
        self._set_region(r.name if r else None)
        await self._redraw()
        return MapState.analyze

    @rx.event
    async def use_my_location(self):
        app = await self.get_state(AppState)
        self.sel_lat, self.sel_lon, self.has_sel = round(app.lat, 4), round(app.lon, 4), True
        self._set_region(None)
        await self._redraw()
        return MapState.analyze

    @rx.event
    async def pick_region(self, name: str):
        r = REGION_BY_NAME[name]
        self.sel_lat, self.sel_lon, self.has_sel = r.lat, r.lon, True
        self._set_region(name)
        await self._redraw()
        return MapState.analyze

    def _set_region(self, name: str | None):
        r = REGION_BY_NAME.get(name) if name else None
        self.claim_check = ""
        self.region = {} if r is None else {
            "name": r.name, "kind": REGION_KINDS[r.kind], "kind_key": r.kind, "place": r.place,
            "advantage": r.advantage, "challenge": r.challenge,
            "claim": "" if r.claimed_wind_ms is None else f"{r.claimed_wind_ms:g}",
        }

    @rx.event
    async def analyze(self):
        self.loading, self.error = True, ""
        yield
        app = await self.get_state(AppState)
        try:
            d = await asyncio.to_thread(services.site_report, app._spec(), self.sel_lat, self.sel_lon)
        except Exception as e:
            self.error = f"Analiz yapılamadı: {e}"
            self.loading = False
            return
        for k in ("kpi", "restrict", "restrict_codes", "cell", "live", "solar_rows", "wind_rows", "hybrid_rows", "advice",
                  "fig_monthly", "fig_rose", "fig_wind_heat"):
            setattr(self, k, d[k])
        self.techniques = [{k: str(v) for k, v in t.items()} for t in d["techniques"]]
        claim = self.region.get("claim", "") if self.region else ""
        if claim:
            v100 = d["wind_mean_100_val"]
            self.claim_check = (
                f"Metinde ortalama rüzgârın {claim}–8 m/s üzerinde olduğu belirtiliyor. Geçmiş yılın "
                f"saatlik verisi bu noktada 100 m'de ortalama {f'{v100:.1f}'.replace('.', ',')} m/s gösteriyor"
                + (". Fark büyük: bölgesel hava modelleri sırt ve burun etkisini tam yansıtmaz; "
                   "ölçüm direği veya yüksek çözünürlüklü rüzgâr atlası ile doğrulanmalı."
                   if v100 < float(claim) - 1 else ". Veri iddiayı destekliyor."))
        self.loading = False
        # Haritadaki seçim, Üretim ve Senaryolar'ın da hedefidir
        yield AnalysisState.refresh
        yield ScenarioState.run_selected


# ======================================================================= ANALİZ
class AnalysisState(rx.State):
    loading: bool = False
    error: str = ""
    month: str = "1"
    fig_forecast: go.Figure = charts.empty()
    fig_daily: go.Figure = charts.empty()
    fig_wind_series: go.Figure = charts.empty()
    fig_wind_heat: go.Figure = charts.empty()
    fig_rose: go.Figure = charts.empty()
    fig_pv_heat: go.Figure = charts.empty()
    fig_monthly: go.Figure = charts.empty()
    table: list[list[str]] = []
    kpi: dict[str, str] = {}
    hist_note: str = ""
    place: str = ""
    city: dict[str, str] = {}

    @rx.event
    async def start(self):
        ev = await _location(self, False, AnalysisState.on_location)
        return ev or AnalysisState.refresh

    @rx.event
    async def on_location(self, result: dict):
        app = await self.get_state(AppState)
        app._apply_location(result)
        return AnalysisState.refresh

    @rx.event
    def set_month(self, value: str):
        self.month = value
        return AnalysisState.refresh

    @rx.event
    async def refresh(self):
        self.loading, self.error = True, ""
        yield
        app = await self.get_state(AppState)
        lat, lon, self.place = await _target(self)
        try:
            d = await asyncio.to_thread(services.analysis_bundle, app._spec(), lat, lon, int(self.month))
        except Exception as e:
            self.error = f"Veri alınamadı: {e}"
            self.loading = False
            return
        for k, v in d.items():
            setattr(self, k, v)
        self.loading = False


# ======================================================================= SENARYOLAR
class ScenarioState(rx.State):
    region: str = SELECTED
    place: str = ""
    loading: bool = False
    error: str = ""
    compare: list[dict[str, str]] = []
    rows: list[dict[str, str]] = []
    sweep: list[dict[str, str]] = []
    conclusion: list[str] = []
    smart: dict[str, str] = {}
    note: str = ""
    fig_monthly: go.Figure = charts.empty()

    @rx.event
    async def start(self):
        ev = await _location(self, False, ScenarioState.on_location)
        return ev or ScenarioState.run

    @rx.event
    async def on_location(self, result: dict):
        app = await self.get_state(AppState)
        app._apply_location(result)
        return ScenarioState.run

    @rx.event
    def set_region(self, value: str):
        self.region = value
        return ScenarioState.run

    @rx.event
    def run_selected(self):
        """Haritadan gelen seçim: ayrıntı bölgesi = seçili nokta."""
        self.region = SELECTED
        return ScenarioState.run

    @rx.event
    async def run(self):
        self.loading, self.error = True, ""
        yield
        app = await self.get_state(AppState)
        lat, lon, self.place = await _target(self)
        if self.region != SELECTED:
            self.place = self.region
        try:
            d = await asyncio.to_thread(services.scenario_bundle, app._spec(), self.region, lat, lon)
        except Exception as e:
            self.error = f"Simülasyon yapılamadı: {e}"
            self.loading = False
            return
        for k, v in d.items():
            setattr(self, k, v)
        self.loading = False
