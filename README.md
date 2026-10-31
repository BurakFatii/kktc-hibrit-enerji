# KKTC Hibrit Enerji

Kuzey Kıbrıs'ta kamu kurumları ve şirketler için **güneş + rüzgâr + batarya + akıllı enerji yönetimi**.
Hangi bölgede, hangi kapasitede ve hangi kontrol stratejisiyle verimli çalışacağını saatlik meteoroloji verisiyle gösterir.

Proje özeti: [`kaynak/proje-ozeti.jpg`](kaynak/proje-ozeti.jpg) · Jüri kriterleri: [`kaynak/juri-kriterleri.pdf`](kaynak/juri-kriterleri.pdf)

## Jüri kriterleri belgeleri (takım için)

| Kriter | Belge |
|---|---|
| K1 · Problem tanımı ve çözüm uyumu | [docs/K1-problem-ve-cozum-uyumu.md](docs/K1-problem-ve-cozum-uyumu.md) |
| K2 · Yenilikçilik, özgünlük, katma değer | [docs/K2-yenilikcilik-ozgunluk-katma-deger.md](docs/K2-yenilikcilik-ozgunluk-katma-deger.md) |
| K3 · Somut prototip ve teknik doğrulama | [docs/K3-prototip-ve-teknik-dogrulama.md](docs/K3-prototip-ve-teknik-dogrulama.md) |
| K4 · Uygulanabilirlik ve fizibilite | [docs/K4-uygulanabilirlik-ve-fizibilite.md](docs/K4-uygulanabilirlik-ve-fizibilite.md) |
| K5 · Sürdürülebilirlik ve etki | [docs/K5-surdurulebilirlik-ve-etki.md](docs/K5-surdurulebilirlik-ve-etki.md) |

Belgelerdeki sayılar `scripts/rapor.py` ile üretilir. Uygulama değiştikçe bu betik yeniden çalıştırılır ve tablolar güncellenir.

## Çalıştırma

```bash
cd kktc-hibrit-enerji
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/reflex run          # http://localhost:3000
```

```bash
.venv/bin/python -m pytest -q        # hesap çekirdeği testleri
.venv/bin/python scripts/rapor.py    # belgelerdeki sonuç tabloları
```

Konum, tarayıcıdan alınır; izin verilmezse Lefkoşa gösterilir. Geçmiş yıl verisi Open-Meteo arşivinden ECMWF IFS (~9 km) modelidir; ilk sorgu ~1–3 saniye sürer, sonra `.cache/` kullanılır.

## Sayfalar

| Sayfa | İçerik |
|---|---|
| Ana Sayfa | Güç akış şeması, "Bugün" paneli (tüketim nereden karşılandı), pil göstergesi, doluluk barları, panel eğimi / güneş yayı, rüzgâr pusulası, 24 saat şeridi |
| Veriler | Uygunluk katmanlı harita (kırmızı / sarı / mavi + kısıt kodları), üretim ve senaryoların tek sayfalık özeti; "Tümünü göster" → `/veriler/harita`, `/veriler/analiz`, `/veriler/senaryolar` |
| Ayarlar | Panel, türbin ve batarya etiket değerleri; tüketim; şebekeye verme sınırı; maliyetler |
| Nasıl Çalışır | Akış şeması, elektrik mimarisi, karar ağacı, basit ↔ akıllı yönetim karşılaştırması |

## Yapı

```
hibrit_enerji/
  core/            hesap çekirdeği (Reflex'ten bağımsız, test edilir)
    solar.py         pvlib: güneş konumu, Perez ışınımı, PVWatts
    wind.py          windpowerlib: göbek hızı, hava yoğunluğu, güç eğrisi; yön analizi
    ems.py           enerji yönetimi: yok / basit / akıllı (tahmine dayalı)
    analysis.py      optimum açı/yön, senaryolar, kapasite taraması, konum analizi
    meteo.py         Open-Meteo tahmin + geçmiş yıl arşivi (ECMWF IFS, disk önbelleği)
    load.py spec.py production.py config.py
  services.py      hesapları ekrana hazır pakete çevirir
  state.py         Reflex durumları
  pages/           arayüz
  olmap.py         OpenLayers bileşeni
  charts.py        Plotly grafikleri (yalnızca zamana bağlı veriler)
  viz.py           görsel göstergeler: bar, pil, pusula, eğim, güneş yayı, güç akışı, 24 saat şeridi
assets/theme.css   tema: neon + siyah/beyaz, gölgesiz
docs/              5 jüri kriteri belgesi
scripts/rapor.py   belge sayıları
tests/             doğrulama testleri
kaynak/            jüri kriterleri PDF, proje özeti
archive/streamlit-poc/   ilk kavram doğrulama (arşiv)
```
