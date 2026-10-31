"""Sabitler: bölgeler, harita sınırları, maliyet ve emisyon varsayımları.

Buradaki sayıların hepsi VARSAYIMDIR ve Ayarlar > Gelişmiş bölümünden
değiştirilebilir. Kaynak/gerekçe docs/K4-uygulanabilirlik-fizibilite.md içinde.
"""
from __future__ import annotations

from dataclasses import dataclass

# Konum izni verilmezse kullanılan yedek nokta (Lefkoşa).
FALLBACK_LOCATION = {"name": "Lefkoşa (varsayılan)", "lat": 35.1856, "lon": 33.3823}

@dataclass(frozen=True)
class Region:
    name: str
    lat: float
    lon: float
    kind: str              # "ozet" | "ruzgar" | "gunes"
    place: str = ""        # konumun neyi temsil ettiği
    advantage: str = ""
    challenge: str = ""
    claimed_wind_ms: float | None = None  # metindeki ortalama rüzgâr iddiası (geçmiş yıl verisiyle kıyaslanır)


REGION_KINDS = {
    "ozet": "Proje özeti aday bölgesi",
    "ruzgar": "Rüzgâr santrali adayı",
    "gunes": "Toplu güneş (GES) adayı",
}

# Koordinatlar OpenStreetMap / Nominatim'den alındı (31.10.2026).
REGIONS: list[Region] = [
    # --- Proje özeti (kaynak/proje-ozeti.jpg)
    Region("Gazimağusa", 35.125, 33.940, "ozet", "Şehir merkezi"),
    Region("Dipkarpaz", 35.598, 34.381, "ozet", "Köy merkezi"),
    Region("Beşparmak", 35.300, 33.450, "ozet", "Beşparmak sıradağları (yaklaşık)"),
    # --- Rüzgâr santrali adayları
    Region("Kormacit hattı", 35.363, 32.981, "ruzgar",
           "Koruçam (35.343, 33.010) – Sadrazamköy (35.383, 32.953) hattının orta noktası",
           "Yerleşim seyrek; yıllık ortalama rüzgârın 7–8 m/s üzerinde olduğu belirtiliyor "
           "(ticari santral için ideal).",
           "İletim hatları zayıf; üretimi ana şebekeye taşımak için yeni yüksek gerilim hattı gerekir.",
           claimed_wind_ms=7.0),
    Region("Kantara", 35.406, 33.923, "ruzgar", "Kantara Kalesi çevresi",
           "Tüketim merkezlerine ve ana trafo hatlarına yarımada uçlarından çok daha yakın.",
           "Büyük kanatların dar, virajlı, dik dağ yollarından taşınması pahalı; orman arazisi ve "
           "askerî bölge kısıtları."),
    Region("Alevkayası", 35.285, 33.533, "ruzgar", "Alevkayası (Beşparmak dağları)",
           "Tüketim merkezlerine ve ana trafo hatlarına yarımada uçlarından çok daha yakın.",
           "Büyük kanatların dar, virajlı, dik dağ yollarından taşınması pahalı; orman arazisi ve "
           "askerî bölge kısıtları."),
    Region("Karpaz Yarımadası", 35.646, 34.485, "ruzgar",
           "Dipkarpaz – Zafer Burnu arasının orta noktası",
           "Geniş ve engebeli arazi; çoklu türbin tarlasına elverişli fiziksel alan.",
           "Özel Çevre Koruma Bölgesi (Milli Park); göçmen kuş rotası; şebekenin en uç noktası "
           "olduğu için ciddi voltaj düşümü."),
    # --- Toplu güneş (GES) adayları
    Region("Serhatköy", 35.188, 33.092, "gunes", "Serhatköy (mevcut GES ve trafo merkezi çevresi)",
           "KKTC'nin ilk büyük güneş santrali ve ana trafo merkezi burada; şebeke bağlantısı hazır. "
           "Çevrede tarıma elverişsiz geniş, kıraç hazine arazisi var.",
           "Trafo merkezi gündüz doygunluğa ulaşıyor; yeni santral için trafo büyütme ve batarya "
           "depolama şart."),
    Region("Geçitkale", 35.261, 33.732, "gunes", "Geçitkale ovası",
           "Arazi eğimi neredeyse sıfır, hafriyat ve konstrüksiyon maliyeti düşük; dağ gölgesi yok; "
           "güneş takipçili sistemlere çok uygun.",
           "Yazın 40–45 °C iç ova sıcaklığı ısıl verim kaybı yaratır; kurak topraktan kalkan toz, "
           "su tüketen düzenli yıkama gerektirir."),
    Region("Güzelyurt (Yüzer GES)", 35.195, 33.008, "gunes", "Güzelyurt Barajı",
           "Su üstü (yüzer) GES: su serinliği panel verimini %10–15 artırabilir ve buharlaşmayı "
           "önler. Tarım GES seçeneği.",
           "Duba, su altı çapalama ve neme dayanıklı kablo nedeniyle ilk yatırım karaya göre "
           "%20–30 pahalı; narenciye bahçeleri yüzünden karada boş arazi yok."),
    Region("Geçitköy (Yüzer GES)", 35.324, 33.076, "gunes", "Geçitköy Göleti",
           "Su üstü (yüzer) GES: su serinliği panel verimini %10–15 artırabilir ve buharlaşmayı "
           "önler.",
           "Duba, su altı çapalama ve neme dayanıklı kablo nedeniyle ilk yatırım karaya göre "
           "%20–30 pahalı."),
]
REGION_BY_NAME: dict[str, Region] = {r.name: r for r in REGIONS}

# Geriye uyumlu basit eşleme: ad -> (enlem, boylam)
CANDIDATE_REGIONS: dict[str, tuple[float, float]] = {r.name: (r.lat, r.lon) for r in REGIONS}


def nearest_region(lat: float, lon: float, max_km: float = 3.0) -> Region | None:
    """Tıklanan nokta bir örnek bölgeye max_km'den yakınsa o bölge."""
    best, best_d = None, max_km
    for r in REGIONS:
        dlat = (r.lat - lat) * 111.0
        dlon = (r.lon - lon) * 111.0 * 0.819  # cos(35°)
        d = (dlat ** 2 + dlon ** 2) ** 0.5
        if d <= best_d:
            best, best_d = r, d
    return best

# Saat dilimi (KKTC).
LOCAL_TZ = "Asia/Famagusta"

# Şebeke emisyon faktörü (kg CO2 / kWh). KKTC üretimi ağırlıkla fuel-oil
# santrallerinden; 0.70 muhafazakâr bir varsayımdır, resmi veriyle güncellenmeli.
GRID_EMISSION_KG_PER_KWH = 0.70

SYSTEM_LIFETIME_YEARS = 20
