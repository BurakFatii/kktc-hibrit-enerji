# K3 · Somut Prototip ve Teknik Doğrulama (%20)

> **Jüri sorusu:** Takım, hackathon süresince fikrini somut ve gösterilebilir bir çıktıya dönüştürebilmiş mi?

**Son güncelleme:** 31.10.2026 · **Durum:** ✅ çalışan prototip

---

## Sunumda söylenecek kısa cevap

Çalışan bir web uygulamamız var. Tarayıcı konumunuzu alıp o anki üretimi ve sistemin verdiği kararı gösteriyor. Haritada tıkladığınız her nokta için güneş ve rüzgâr potansiyelini, en iyi panel açısını ve türbin yönünü hesaplıyor. Dört senaryoyu (güneş, rüzgâr, hibrit, hibrit + batarya + akıllı yönetim) aday bölgelerde bir yıllık saatlik veriyle simüle ediyor. Hesap çekirdeği otomatik testlerle doğrulanıyor.

## Değerlendirme ölçütleri

| Ölçüt | Cevabımız | Kanıt | Durum |
|---|---|---|---|
| Çalışan prototip, demo, veri modeli veya simülasyon var mı? | Reflex (Python) web uygulaması, 6 sayfa; 8760 saatlik simülasyon | `reflex run` → http://localhost:3000 | ✅ |
| Teknik mimari ve işleyiş anlaşılır mı? | Mimari şeması + "Nasıl Çalışır" sayfası | Aşağıda; uygulamada `/nasil-calisir` | ✅ |
| Temel işlevleri ve uygulanabilirliği gösteriyor mu? | Anlık karar, nokta analizi, senaryo karşılaştırması, kapasite taraması | Demo akışı (aşağıda) | ✅ |

## Uygulama sayfaları

Tasarım: düz, gölgesiz; Matrix neon yeşili + temaya göre siyah/beyaz. Özet sayfalarda sade dil, teknik değerler (korelasyon, kapasite faktörü, kWh/kWp) yalnızca ayrıntı sayfalarında. Kural: zaman içindeki değişimi önemli olan veri grafikte; tek bir oran, durum ya da yön görsel göstergede (dolgulu bar, pil, pusula, eğim çizimi, güneş yayı, güç akışı, 24 saat şeridi).

| Sayfa | Ne gösterir |
|---|---|
| **Ana Sayfa** (`/`) | Sistemin kararı + **akan güç şeması** (güneş/rüzgâr → inverter → tesis/batarya/şebeke); **"Bugün" paneli**: toplam tüketim, güneş ve rüzgârdan üretilen, şebekeden alınan ve verilen + tüketimin nereden karşılandığını gösteren yığılı bar; **pil göstergesi**; güneş, rüzgâr, tüketim doluluk barları; panel **eğim çizimi** ve **güneş yayı**; rüzgâr **pusulası**; önümüzdeki 24 saatin **mod şeridi**. Konum tarayıcıdan. |
| **Veriler** (`/veriler`) | **Haritada seçilen nokta tüm sayfayı belirler**: tıklanan nokta ya da seçilen bölge için üretim (tahmin + geçmiş yıl) ve senaryolar otomatik yeniden hesaplanır; seçim yoksa cihaz konumu kullanılır. Tek sayfada toplu özet: harita + seçili nokta göstergeleri, 48 saat tahmin + yıllık özet, bölgelerin hibrit öz yeterlilik barları + akıllı yönetimin kısılan enerjiye etkisi. Her bölümde **"Tümünü göster"**. |
| Veriler › Harita (`/veriler/harita`) | **Uygunluk katmanı** (kırmızı: ikisine de uygun değil, sarı: yalnızca güneşe uygun, mavi: yalnızca rüzgâra uygun, boyasız: ikisine de uygun; KKTC kara sınırı; OSM verisi) ve tıklanan noktanın kartı: rüzgâr ✓/✗, güneş ✓/✗ ve kısa kısıt kodları (A01 ara bölge, A02 askerî, A03 koruma alanı, A04 havalimanı, R01 havalimanına yakın, R02 yerleşime yakın, R03 su yüzeyi, G01 orman); 11 örnek bölge (avantaj/zorluk kartı), tıklanan noktada eğim çizimi, hakim yön ve sabit türbin yönü pusulaları, sabit ↔ takipçili ve sabit ↔ otomatik türbin barları, korelasyon barı, teknik uygunluk seviyeleri, aylık üretim, rüzgâr gülü, ısı haritası, tüm değer tabloları |
| Veriler › Üretim (`/veriler/analiz`) | **Şehir ölçeği**: seçili noktanın ilçesi, nüfusu ve yıllık ihtiyacı; o noktanın verimine ve uygunluğuna göre boyutlanan santral (MWp güneş, MW rüzgâr — E-82), batarya; 48 saat / yıllık bataryasız / bataryalı karşılama oranları. MW cinsinden 48 saat tahmin grafiği; **günlük enerji grafiği** (dün/bugün/yarın: tüketim güneşten, rüzgârdan, bataryadan, şebekeden);  geçmiş yıl saatlik rüzgâr hızı, yönü ve enerjisi; ay × saat ısı haritaları; saatlik tablo |
| Veriler › Senaryolar (`/veriler/senaryolar`) | 11 bölge + mevcut konum × 5 senaryo; senaryo öz yeterlilik barları; aylık enerji açığı; en uygun 8 kapasite |
| **Ayarlar** (`/ayarlar`) | Panel, türbin ve batarya **etiket değerleri**, tesis tipi ve aylık tüketim, şebekeye verme sınırı, maliyet varsayımları |
| **Nasıl Çalışır** (`/nasil-calisir`) | Veriden karara akış şeması, akan çizgili elektrik mimarisi, akıllı yönetimin karar ağacı, basit kural ↔ akıllı yönetim batarya şeridi karşılaştırması, kütüphaneler, bilinen sınırlar |

## Teknik mimari

```
 ┌────────────── VERİ ──────────────┐
 │ Open-Meteo tahmin (3 gün, saatlik)│   Tarayıcı konumu   Ayarlar (etiket değerleri)
 │ Geçmiş yıl arşivi (8760 saat)     │   Harita tıklaması  → tarayıcıda saklanır
 └───────────────┬───────────────────┘
                 ▼
 ┌──────── FİZİK MODELİ (core/) ──────────────────────────────────────┐
 │ solar.py  pvlib: NREL SPA güneş konumu → Perez eğik yüzey ışınımı  │
 │           → ASHRAE geliş açısı kaybı → Ross/NOCT hücre sıcaklığı   │
 │           → PVWatts DC + sistem kayıpları → PVWatts inverter       │
 │           sabit (optimum açı) / çift eksen takipçi                 │
 │ wind.py   windpowerlib: 10 m + 100 m'den logaritmik göbek hızı,    │
 │           barometrik hava yoğunluğu, yoğunluk düzeltmeli güç eğrisi│
 │           (katalog tablosu veya etiket hızları); sabit türbin yön  │
 │           kaybı ve rüzgâr gülü (proje kodu)                        │
 │ load.py   aylık fatura → saatlik tüketim profili                   │
 └───────────────┬────────────────────────────────────────────────────┘
                 ▼
 ┌──────── ENERJİ YÖNETİMİ (core/ems.py) ────────┐
 │ yok / basit / akıllı (tahmine dayalı)          │
 │ batarya · şebekeye verme (limitli) · kısıt     │
 │ · kısıtlama                                    │
 └───────────────┬────────────────────────────────┘
                 ▼
 ┌──────── ANALİZ (core/analysis.py) ─────────────────────────────┐
 │ optimum açı/yön · tamamlayıcılık · 5 senaryo · kapasite taraması│
 └───────────────┬─────────────────────────────────────────────────┘
                 ▼
   services.py (ekrana hazır paket) → state.py (Reflex) → pages/
```

**Elektrik mimarisi (sahadaki sistem):**

```
[PV (sabit/takipçili)] ─DC─► [MPPT] ─┐
[Rüzgâr türbini] ─► [Şarj kontrolcüsü] ─► [DC bara] ◄──► [LiFePO4 + BMS]
                                          │
                              [Hibrit inverter + ATS] ──► [Tesis panosu] ──► Yükler
                                   │  ▲                       └──► [Akıllı sayaç]
                     sınırlı ihracat │  │ çekiş
                                   ▼  │
                                 [Şebeke]
[EMS yazılımı] ← tahmin + sayaç + BMS → şarj / deşarj / ihracat kararı
```

Sahada aynı EMS mantığının gömülü cihazda (Rust) çalışması planlanıyor. Bu uygulama izleme ve planlama paneli olarak kalacak.

## Saha yön bulucu (donanım + API)

Kurulum ekibi paneli ve türbini sahada doğru yöne baksın diye: M5Stack StickS3'e
takılan cihaz, Reflex'le aynı bilgisayarda koşan yerli API'den anlık hedefi çeker
(`hibrit_enerji/orientation_api.py`, `:8001` → `GET /api/yonlendirme?lat=..&lon=..`).
Ön buton (A) **GÜNEŞ ↔ RÜZGAR** arayüzünü değiştirir (kulak ikonu: güneş tek tiz,
rüzgâr çift kalın bip); yan buton (B) kısa basışta sesi DÜŞÜK → ORTA → YÜKSEK döndürür,
uzun basışta cihaz kuzeydeyken yaw'ı sıfırlar. Hedefe yaklaştıkça bip sıklaşır ve
tizleşir ("Bul" uygulamasındaki gibi; yaw kalın, eğim ince perdelidir);
`<4°` yaw + `<3°` eğimde yeşil **KİLİTLENDİ** ekranı ve 3 notalı fanfar gelir.
Hesaplar `core/`'dan gelir (pvlib güneş konumu + windpowerlib göbek rüzgârı);
cihazda ve API'de yeni fizik formülü yoktur. Kurulum: [arduino/README.md](../arduino/README.md),
aygıt yazılımı: [sticks3-yonlendirme](../arduino/sticks3-yonlendirme/sticks3-yonlendirme.ino).
Bilinen sınır: StickS3'te pusula yoktur, yaw gyro tümleviyle bulunur ve dakikalar
içinde birkaç derece kayabilir (B ile tazelenir).

## Kullanılan kütüphaneler (neden bunlar?)

| Alan | Kütüphane | Neden |
|---|---|---|
| Güneş | **pvlib 0.16.1** | Sandia ve NREL kökenli, PV modellemede sektör standardı; akademik olarak doğrulanmış modeller (SPA, Perez, PVWatts) |
| Rüzgâr | **windpowerlib 0.2.2** | oemof ekosisteminden; göbek yüksekliği, hava yoğunluğu ve güç eğrisi zinciri. Hazır türbin veritabanı MW ölçekli olduğu için küçük türbinin eğrisi katalogdan veya etiket hızlarından üretilir |
| Harita | **OpenLayers 10.4** | Açık kaynak, OSM altlık, her noktaya tıklanabilir |
| Kısıt bölgeleri | **shapely 2.2** + OpenStreetMap (Overpass) | Poligon birleştirme, metre cinsinden tampon, nokta-içinde-mi kontrolü (STRtree, 100 sorgu ~1 ms) |
| Arayüz | **Reflex 0.8.28** | Tamamen Python; hesap çekirdeğiyle aynı dil |
| Veri | **Open-Meteo**: tahmin + geçmiş yıl arşivi (**ECMWF IFS, ~9 km**) | Ücretsiz, anahtarsız, tüm dünya, saatlik. ERA5 (~25 km) denendi; KKTC'deki aday bölgeleri ayırt edemediği için IFS'e geçildi. Arayüzde model adı yazmaz, "geçmiş yıl" der |

`numpy 2.2` ve `pandas 2.3`, pvlib ve windpowerlib'in test edildiği aralığa sabitlendi. Testler "kullanımdan kalkma uyarısı = hata" modunda da temiz geçiyor.

## Teknik doğrulama

| Test | Neyi kanıtlar |
|---|---|
| `test_sun_noon_equinox_lefkosa` | Güneş konumu algoritması (ekinoksta öğle zenit ≈ enlem) |
| `test_tracker_beats_fixed_and_fixed_beats_flat` | Işınım modeli fiziksel olarak tutarlı |
| `test_pv_power_respects_label` | Etiket değerinden güç hesabı (pvlib zinciri) |
| `test_hot_panel_produces_less` | Sıcaklık kaybı (Kıbrıs yazı için kritik) |
| `test_power_curve_limits` | Türbin devreye girme / anma / durma hızları |
| `test_catalog_power_curve_is_used` | Katalogdaki güç eğrisi tablosunun kullanılması |
| `test_thin_air_produces_less_wind_power` | Hava yoğunluğu düzeltmesi |
| `test_hub_speed_between_10m_and_100m` | Göbek yüksekliği hızı ve yoğunluğu makul aralıkta |
| `test_fixed_yaw_loses_energy_off_axis` | Sabit türbin yön kaybı |
| `test_ems_energy_balance` (3 strateji) | Her saatte enerji korunumu, batarya enerji dengesi, ihracat limiti |
| `test_smart_curtails_less_without_hurting_self_sufficiency` | Akıllı yönetimin katkısı |
| `test_spec_from_form_tolerates_bad_input` | Kullanıcı girdisi sağlamlığı |
| `test_city_district_and_need` | İlçe tespiti; ilçe ihtiyaçları toplamı KKTC toplamına eşit; kişi başı tüketim resmî veriden türetiliyor |
| `test_city_design_meets_annual_need_and_respects_suitability` | Santral yıllık ihtiyacı tam karşılar; tamamlayıcı kaynakta karışım seçilir; uygun olmayan kaynak kullanılmaz |
| `test_restriction_zones_classify_known_places` | Uygunluk: Ercan ve Karpaz kırmızı, Alevkayası ormanı mavi (yalnız rüzgâr, G01), Gazimağusa yerleşimi sarı (yalnız güneş, R02), deniz uygun |
| `test_paket_yapisi_ve_araliklar` | Yönlendirme API paketi: gündüz hedef aralıkları, rüzgâr yönü/hızı |
| `test_gece_gunes_asagi` | Gece bayrağı ve park hedefi |

Çalıştırma: `.venv/bin/python -m pytest -q` → **19 test geçiyor**.

## Demo akışı (3 dakika)

1. **Ana Sayfa:** Güç akış şemasında enerjinin nereye aktığını, pil göstergesini ve 24 saat şeridini göster. (30 sn)
2. **Ayarlar:** Kurulum tipini "Sabit" → "Takipçili" yap, kaydet; ana sayfadaki kurulum yönü metninin değiştiğini göster. (30 sn)
3. **Veriler:** Haritada Karpaz'a, sonra Gazimağusa'ya tıkla; rüzgârın farkını, tamamlayıcılık testini ve açı/yön önerisini göster. (60 sn)
4. **Veriler › Senaryolar:** bölge barları → akıllı yönetimle kısılan enerjinin düşüşü → "en uygun tasarım". Kapanışta **Nasıl Çalışır**'daki karar ağacı. (60 sn)

## Bilinen sınırlar (dürüstçe)

- Geçmiş yıl verisi ~9 km çözünürlükte. Dağ sırtları ve burunlar yine de düzleşir; birbirine çok yakın örnek bölgeler aynı veri noktasını paylaşır (K4). Yerel ölçümle doğrulanmalı.
- Tüketim, gerçek sayaç bağlanana kadar fatura değerinden profillenir; batarya doluluğu simülasyondur.
- Simülasyondaki akıllı yönetim kusursuz tahmin varsayar.
- Katalog güç eğrisi girilmezse eğri, etiket hızlarından kübik yaklaşımla üretilir.

## Açık işler

- [ ] Ekran görüntülerini `kaynak/` klasörüne ekle (sunum için)
- [ ] Tahmin hatalı simülasyon testi
- [ ] Gerçek bir inverter, sayaç veya BMS verisiyle (Modbus/MQTT) canlı bağlantı denemesi
