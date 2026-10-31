"""Kullanıcının sistem tanımı (Ayarlar sayfası).

Alanlar son kullanıcının cihaz etiketinden / katalogdan (datasheet)
okuyabileceği değerlerdir. Algoritma bunları fizik modeline çevirir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields

PV_MOUNTS = {"sabit": "Sabit montaj (ekonomik)", "takipci": "Çift eksen güneş takipçili"}
WIND_YAW = {"otomatik": "Rüzgâra otomatik dönen", "sabit": "Sabit yönlü (ekonomik)"}
# Anahtarlar geriye uyumluluk için korunur: "ev" = akşamı yoğun profil, "isletme" = gündüzü yoğun profil
LOAD_PROFILES = {"ev": "Kamu / yerleşke (akşam yoğun)", "isletme": "Ticari / sanayi tesisi (gündüz yoğun)"}


@dataclass
class SystemSpec:
    # --- Güneş (panel etiketi) ---
    pv_mount: str = "sabit"
    panel_wp: float = 550.0          # Etiketteki "Pmax" (W)
    panel_count: int = 10
    temp_coeff_pct: float = -0.35    # "Pmax sıcaklık katsayısı" (%/°C)
    noct_c: float = 45.0             # "NOCT" (°C)
    inverter_eff_pct: float = 97.0   # İnverter etiketi "maks. verim"
    auto_orient: bool = True         # Sabit panelde en iyi açıyı uygulama hesaplasın
    fixed_tilt_deg: float = 30.0
    fixed_azimuth_deg: float = 180.0  # 180 = güney

    # --- Rüzgâr (türbin etiketi) ---
    wind_rated_kw: float = 3.0       # 0 = türbin yok
    wind_cut_in_ms: float = 3.0
    wind_rated_ms: float = 11.0
    wind_cut_out_ms: float = 25.0
    # Katalogdaki güç eğrisi tablosu, "hız:güç_W" çiftleri (ör. "3:0, 5:400, 8:1500").
    # Boşsa eğri devreye girme / anma / durma hızlarından üretilir.
    wind_power_curve: str = ""
    # windpowerlib türbin veritabanından tip (ör. "E-82/2300"). Doluysa eğri oradan alınır ve
    # wind_rated_kw'ye ölçeklenir (şehir ölçeği santral). Boşsa etiket hızları / katalog tablosu.
    wind_turbine_type: str = ""
    hub_height_m: float = 12.0
    wind_yaw: str = "otomatik"
    auto_wind_dir: bool = True
    wind_fixed_dir_deg: float = 315.0  # Sabit türbinin baktığı yön (rüzgârın geldiği yön)

    # --- Batarya ---
    battery_kwh: float = 10.0        # 0 = batarya yok
    battery_dod_pct: float = 90.0
    battery_rt_eff_pct: float = 92.0
    battery_power_kw: float = 5.0

    # --- Tüketim ---
    monthly_kwh: float = 450.0       # Elektrik faturasındaki aylık tüketim
    load_profile: str = "ev"

    # --- Şebeke ---
    export_limit_kw: float = 3.0     # Şebekeye verilebilecek en yüksek güç

    # --- Elektrikli araç (opsiyonel) ---
    ev_enabled: bool = False
    ev_kwh: float = 40.0
    ev_v2h: bool = True
    ev_reserve_pct: float = 60.0     # Yolculuk için ayrılan pay

    # --- Maliyet varsayımları (USD) ---
    cost_pv_usd_per_wp: float = 0.90
    cost_tracker_usd_per_wp: float = 0.35
    cost_wind_usd_per_kw: float = 3500.0
    cost_battery_usd_per_kwh: float = 350.0
    price_import_usd_kwh: float = 0.17
    price_export_usd_kwh: float = 0.08
    # Santral (şehir) ölçeği maliyetleri — MW sınıfı ekipman daha ucuzdur
    cost_pv_utility_usd_per_wp: float = 0.65
    cost_wind_utility_usd_per_kw: float = 1500.0
    cost_battery_utility_usd_per_kwh: float = 300.0

    @property
    def pv_kwp(self) -> float:
        return max(0.0, self.panel_wp) * max(0, self.panel_count) / 1000.0

    @property
    def battery_usable_kwh(self) -> float:
        return max(0.0, self.battery_kwh) * max(0.0, min(100.0, self.battery_dod_pct)) / 100.0

    def to_dict(self) -> dict:
        return asdict(self)

    def to_form(self) -> dict[str, str]:
        """UI formu için tüm değerleri metin olarak döndür."""
        out = {}
        for k, v in asdict(self).items():
            if isinstance(v, bool):
                out[k] = "evet" if v else "hayır"
            elif isinstance(v, float):
                out[k] = f"{v:g}"
            else:
                out[k] = str(v)
        return out

    @classmethod
    def from_dict(cls, data: dict | None) -> "SystemSpec":
        """Eksik/bozuk alanları varsayılana düşürerek oluştur."""
        base = cls()
        if not data:
            return base
        for f in fields(cls):
            if f.name not in data:
                continue
            raw = data[f.name]
            default = getattr(base, f.name)
            try:
                if isinstance(default, bool):
                    val = raw if isinstance(raw, bool) else str(raw).strip().lower() in (
                        "1", "true", "evet", "on", "yes")
                elif isinstance(default, int):
                    val = int(float(str(raw).replace(",", ".")))
                elif isinstance(default, float):
                    val = float(str(raw).replace(",", "."))
                else:
                    val = str(raw)
            except (TypeError, ValueError):
                continue
            setattr(base, f.name, val)
        if base.pv_mount not in PV_MOUNTS:
            base.pv_mount = "sabit"
        if base.wind_yaw not in WIND_YAW:
            base.wind_yaw = "otomatik"
        if base.load_profile not in LOAD_PROFILES:
            base.load_profile = "ev"
        return base
