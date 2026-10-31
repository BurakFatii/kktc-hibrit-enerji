# KKTC Hibrit Enerji — çalışma kuralları

## Amaç
Hackathon projesi. Jüri 5 kriterle puanlıyor (`kaynak/juri-kriterleri.pdf`, her biri %20).
Her değişiklik bu kriterlerden en az birini güçlendirmeli. Proje özeti: `kaynak/proje-ozeti.jpg`.

## Belgeler her değişiklikte güncellenir (zorunlu)
- `docs/` altında YALNIZCA 5 dosya var: K1–K5. Yeni belge dosyası açma; ilgili K dosyasına ekle.
- Sonucu etkileyen her kod değişikliğinden sonra: `.venv/bin/python scripts/rapor.py` çalıştır,
  K1/K2/K4/K5'teki "Güncel sonuçlar" tablolarını güncelle, "Son güncelleme" tarihini değiştir.
- Yeni sayfa / özellik / test → K3'teki tabloları güncelle.
- Kullanıcı belgeleri elle düzenleyebilir; üzerine yazmadan önce oku, onun metnini koru.

## Ürün kararları (kullanıcıdan)
- Arayüz: Reflex (Streamlit arşivde, geri dönülmez). Harita: OpenLayers (Leaflet değil).
- Güneş: pvlib. Rüzgâr: windpowerlib. Kendi fizik formülü yazma; olgun kütüphane kullan.
- Konum: yalnızca tarayıcının anlık konumu (konum seçici yok). İzin yoksa Lefkoşa yedeği.
- Ana sayfada grafik yok; yalnızca anlık bilgi, görsel göstergelerle.
- Sayfalar: Ana Sayfa · Veriler (harita + üretim + senaryolar tek sayfada, "Tümünü göster" → /veriler/*) · Ayarlar · Nasıl Çalışır.
- Tasarım: neon (#00FF41) + temaya göre siyah/beyaz; GÖLGE YOK, düz panel (`viz.panel`, 1px çizgi). Renkler `assets/theme.css` değişkenlerinden.
- Görselleştirme kuralı: zaman içinde değişen veri → grafik (`charts.py`); tek oran/durum/yön → gösterge (`viz.py`: meter, battery, compass, tilt_view, sun_arc, power_flow, day_strip, level3, diverge, bar_list).
- Harita altlığı: OSM karoları + CSS filtresi `div.ol-base` üzerinde (CARTO anahtar istiyor, kullanma).
- Uygunluk katmanı (kullanıcı kararı, renk UYGUNLUĞU gösterir): kırmızı = ikisine de uygun değil,
  SARI = yalnızca güneşe uygun, MAVİ = yalnızca rüzgâra uygun. Neden: kısa kod (A01–A04, R01–R03, G01; `core/restrictions.CODES`).
  "Uygun değil" yazısı yerine ✓/✗ ikon (`viz.ok_icon`). Renkler temaya göre (`--zone-*`, açıkta koyu, koyuda parlak).
  Veri `scripts/kisit_bolgeleri.py` ile OSM'den üretilir → `assets/kisit_bolgeleri.geojson` (harita) +
  `hibrit_enerji/data/kisit_kaynak.geojson` (nokta kontrolü, `core/restrictions.py`). Overpass yavaş: ~5–10 dk.
- Ayarlar son kullanıcı dilinde: cihaz etiketi/katalog değerleri istenir, model parametresi değil.
- Hedef kitle kamu + şirket: "ev/hane" değil "tesis" de. Elektrikli araç (V2H) projeden çıkarıldı; arayüze ekleme.
- **Sabit değer yok** (kullanıcı kararı): Veriler'deki her sayı seçili noktadan ve o noktanın ilçesinin ihtiyacından türetilir (`core/city.py`). Tek sabitler resmî kaynak verileri (ilçe nüfusu 2011, toplam 2021 tahmini, 2011 tüketimi) ve ekipman tipi (E-82/2300). Santral, batarya, şebeke sınırı, kapasite taraması türetilir.
- Veriler sayfasında hedef = haritada seçili nokta (`state._target`); harita analizi bitince Üretim ve Senaryolar zincirle yeniden hesaplanır. Ana Sayfa cihaz (tesis) konumunu kullanır.
- Özet sayfalarda (Ana Sayfa, Veriler) sade dil; teknik değerler yalnızca ayrıntı sayfalarında (/veriler/*).
- Şebekeye verme bir HEDEF; yalnızca `export_limit_kw` ile sınırlanır, karşıtı bir mantık kurma.
- Bütçe kademeleri: sabit ↔ takipçili panel, otomatik ↔ sabit türbin. Ucuz sürümde açı/yön uygulama hesaplar.
- Güneş-rüzgâr tamamlayıcılığı varsayılmaz; saatlik veriyle test edilir.
- Geçmiş yıl verisi: ECMWF IFS (~9 km, `meteo.HISTORY_MODEL`). ERA5 bölgeleri ayırt edemediği için bırakıldı.
  **Arayüzde model adı (IFS/ERA5) yazılmaz**; "geçmiş yıl" / "geçmiş yılın saatlik verisi" denir. Belgelerde (docs/) adı geçebilir.
- Örnek bölgeler `core/config.py` REGIONS'ta (koordinatlar OSM/Nominatim). Yeni bölge oraya eklenir.

## Teknik
- Python 3.13 venv: `.venv`. Bağımlılıklar `requirements.txt`'te sabit (numpy 2.2, pandas 2.3 — pvlib uyumu).
- Test: `.venv/bin/python -W error::DeprecationWarning -m pytest -q`
- Çalıştır: `.venv/bin/reflex run` → http://localhost:3000
- Hesaplar `core/`'da (Reflex'ten bağımsız). `services.py` ekrana hazır paket üretir; state yalnızca akış.
- Türkçe sayı biçimi: `services._n` (1.234,5).
