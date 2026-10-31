# K4 · Uygulanabilirlik ve Temel Fizibilite (%20)

> **Jüri sorusu:** Önerilen çözüm, Kıbrıs'ın yerel koşulları, mevcut kaynakları ve makul maliyetler çerçevesinde hayata geçirilebilir mi?

**Son güncelleme:** 31.10.2026 · **Durum:** 🟡 maliyetler yerel tekliflerle doğrulanacak

---

## Sunumda söylenecek kısa cevap

Sistem raftan alınabilen standart parçalardan oluşuyor: panel, hibrit inverter, LiFePO4 batarya ve küçük türbin. Yazılım ücretsiz ve açık veriyle çalışıyor. Varsayılan maliyetlerle 8 kWp güneş + 10 kWh batarya, üç bölgede de en düşük yıllık net maliyetli tasarım çıkıyor. Rüzgâr ancak Dipkarpaz gibi rüzgârlı noktalarda anlamlı katkı sağlıyor. Uygulama bunu her nokta için ayrı ayrı söylüyor, böylece gereksiz yatırım yapılmıyor.

## Değerlendirme ölçütleri

| Ölçüt | Cevabımız | Kanıt | Durum |
|---|---|---|---|
| Maliyet ve kaynaklar gerçekçi değerlendirilmiş mi? | Birim maliyet varsayımları, 76 kombinasyonluk kapasite taraması, geri ödeme süresi | Senaryolar sayfası; Ayarlar > Gelişmiş | 🟡 varsayımlar yerel teklifle güncellenecek |
| İnsan kaynağı ve altyapı yerelde karşılanabilir mi? | Standart bileşenler; yazılım küçük bir ekiple sürdürülebilir; veri ücretsiz | Aşağıda | 🟡 yerel kurulumcu teyidi |
| Uygulama ve devamlılık için gerçekçi yaklaşım var mı? | Aşamalı yol haritası + risk tablosu | Aşağıda | ✅ |

## Maliyet varsayımları (Ayarlar > Gelişmiş'ten değiştirilebilir)

| Kalem | Varsayılan | Not |
|---|---|---|
| Panel + inverter + montaj | 0,90 $/W | `[YEREL TEKLİF]` |
| Takipçi ek maliyeti | 0,35 $/W | `[YEREL TEKLİF]` |
| Küçük rüzgâr türbini (kurulu) | 3.500 $/kW | Küçük türbinler kW başına pahalıdır. Katalog güç eğrisi Ayarlar'dan girilebilir |
| LiFePO4 batarya (kurulu) | 350 $/kWh | |
| Elektrik alış fiyatı | 0,17 $/kWh | `[KIB-TEK tarifesi ile güncelle]` |
| Şebekeye satış fiyatı | 0,08 $/kWh | `[mevzuat netleşince güncelle]` |
| Sistem ömrü | 20 yıl | Yıllık net maliyet = yatırım / 20 + şebekeden alınan − şebekeye satılan |

## Güncel sonuçlar

Kaynak: `scripts/rapor.py`, geçmiş yıl verisi (ECMWF IFS ~9 km, Open-Meteo arşivi, 2025), aylık 450 kWh tüketim, şebekeye verme sınırı 3 kW.

**En düşük yıllık net maliyetli tasarım (76 kombinasyon):** 11 bölgenin **hepsinde** 8 kWp güneş + 10 kWh batarya, rüzgâr yok. Öz yeterlilik %96–97, yatırım 10.700 $, yıllık net maliyet −69 ile −91 $/yıl arası (kâr).

| Bölge | Güneş | Rüzgâr | Batarya | Öz yeterlilik | Yatırım | Yıllık net maliyet |
|---|---|---|---|---|---|---|
| Gazimağusa | 8 kWp | 0 kW | 10 kWh | %96 | 10.700 $ | −84 $/yıl |
| Dipkarpaz | 8 kWp | 0 kW | 10 kWh | %96 | 10.700 $ | −69 $/yıl |
| Beşparmak | 8 kWp | 0 kW | 10 kWh | %97 | 10.700 $ | −83 $/yıl |

**Ne anlama geliyor?**
- Bugünkü maliyetlerle **güneş + batarya** her yerde en ekonomik tasarım.
- **Rüzgâr** maliyet açısından tek başına kazanmıyor, ama rüzgârlı noktalarda gece üretimi sağlıyor ve dalgalanmayı azaltıyor: Karpaz'da bataryasız hibritte öz yeterlilik %43 → %64, üretimsiz saat %51 → %20.
- **Takipçi**, sabit panele göre +%38–39 üretiyor (Harita > Kurulum önerisi geri ödeme süresini verir).
- Sonuçlar maliyet varsayımlarına duyarlı. Yerel tekliflerle güncellenince uygulama ve `scripts/rapor.py` yeni sonucu otomatik verir.

## Saha adayları (örnek bölgeler)

Koordinatlar OpenStreetMap / Nominatim'den alındı. Avantaj ve zorluklar takım araştırmasından; sayılar `scripts/rapor.py` çıktısı. Uygulamada Harita sayfasından her bölge seçilebilir ve avantaj/zorluk kartı görünür.

**Rüzgâr santrali adayları** (türbin verimleri 3 kW küçük türbin, 12 m kule için; kW başına)

| Bölge | Konum | Avantaj | Zorluk | 100 m ort. | Sabit yönlü türbin (kWh/kW/yıl) | Otomatik yönlenen türbin (kWh/kW/yıl) | Bataryasız hibritte öz yeterlilik |
|---|---|---|---|---|---|---|---|
| Kormacit hattı | Koruçam–Sadrazamköy orta noktası (35.363, 32.981) | Seyrek yerleşim; 7–8 m/s üzeri rüzgâr olduğu belirtiliyor | Zayıf iletim hattı, yeni YG hattı gerekir | 5,1 m/s | 273 | 457 (+%67) | %53 |
| Kantara | Kantara Kalesi (35.406, 33.923) | Tüketim merkezi ve trafo hatlarına yakın | Dağ yolunda kanat lojistiği; orman ve askerî bölge | 4,1 m/s | 58 | 129 (+%122) | %46 |
| Alevkayası | (35.285, 33.533) | Aynı | Aynı | 3,3 m/s | 22 | 45 (+%104) | %44 |
| Karpaz Yarımadası | Dipkarpaz–Zafer Burnu orta noktası (35.646, 34.485) | Geniş arazi, çoklu türbin tarlası | Milli park, göçmen kuş rotası, şebeke ucu (voltaj düşümü) | **5,3 m/s** | 456 | **1.128 (+%148)** | **%64** |

**Toplu güneş (GES) adayları**

| Bölge | Konum | Avantaj | Zorluk | Sabit panel kWh/kWp | Takipçili kWh/kWp | Isıl kayıp yıl / Temmuz |
|---|---|---|---|---|---|---|
| Serhatköy | (35.188, 33.092) | Mevcut GES + trafo merkezi; kıraç hazine arazisi | Trafo gündüz doygun → trafo büyütme + batarya şart | 1.771 | 2.466 | %8,0 / %10,9 |
| Geçitkale | (35.261, 33.732) | Düz arazi, gölgesiz, takipçiye uygun | 40–45 °C ısıl kayıp; toz ve yıkama maliyeti | 1.757 | 2.431 | %8,0 / **%11,4** |
| Güzelyurt (Yüzer GES) | Güzelyurt Barajı (35.195, 33.008) | Su serinliği verimi %10–15 artırabilir; buharlaşmayı önler | İlk yatırım karaya göre %20–30 pahalı | 1.771 | 2.466 | %8,0 / %10,9 (kara modeli) |
| Geçitköy (Yüzer GES) | Geçitköy Göleti (35.324, 33.076) | Aynı | Aynı | 1.797 | 2.492 | %7,3 / %10,0 (kara modeli) |

**Veriden çıkan önemli bulgular**

1. **Kormacit iddiası kısmen destekleniyor.** Metindeki 7–8 m/s'ye karşı veri 100 m'de 5,1 m/s gösteriyor; kuzeybatı kıyısında en rüzgârlı ikinci nokta. Burun ve sırt etkisi ~9 km modelde de düzleşir; karar öncesi **ölçüm direği** şart.
2. **Rüzgârda en güçlü aday Karpaz.** Bataryasız hibritte öz yeterlilik %43'ten %64'e, üretimsiz saat %51'den %20'ye. Milli park ve kuş rotası büyük türbinleri zorlaştırır; küçük ölçekli veya dikey eksenli türbinler değerlendirilmeli.
3. **Dağlık iç noktalarda (Alevkayası, Beşparmak) ve Geçitkale'de rüzgâr zayıf** (100 m'de 3,3–3,4 m/s). Kantara ve Alevkayası için metindeki "yakınlık" avantajı rüzgâr kaynağıyla desteklenmiyor; zirve noktası için yerel ölçüm gerekir.
4. **Otomatik yönlenme belirleyici.** Sabit yönlü türbin bölgeye göre %30–62 daha az üretir (otomatik +%42–162). Ucuz sürümde yön gerektirmeyen dikey eksenli türbin (VAWT) değerlendirilmeli.
5. **Isıl kayıp gerçek ama sınırlı.** Yıllık %6–8, Temmuz'da %8–11; en yüksek Geçitkale (%11,4). Yüzer GES'in serinletme etkisi henüz modellenmedi; %10–15 iddiası doğrulanmadı.
6. **Veri noktası paylaşımı.** ~9 km çözünürlükte Kormacit–Geçitköy ve Serhatköy–Güzelyurt aynı veri noktasını kullanıyor. ERA5 (~25 km) ile 4 bölge tek hücreye düşüyordu; bu yüzden daha ince çözünürlüklü veriye geçildi.

## Şehir ölçeği: seçilen noktadaki santral ilçenin ihtiyacını karşılar mı?

Uygulamada Veriler sayfası ve ayrıntıları bu ölçekte çalışır. **Sabit değer yoktur**; her sayı seçilen noktadan ve oradaki ihtiyaçtan türetilir:

| Değer | Nasıl bulunur |
|---|---|
| İlçe | Noktanın düştüğü ilçe poligonu (OSM; Lefke, 2011 sınırlarıyla Güzelyurt'a dahil) |
| İlçe nüfusu | 2011 sayımındaki ilçe payı × 2021 tahmini toplam nüfus (390.745) |
| İlçe ihtiyacı | Nüfus × kişi başı tüketim (1.254 GWh / 286.257 kişi = **4.381 kWh/yıl**, 2011) |
| Saatlik ihtiyaç | Konut (akşam yoğun) + ticari (gündüz yoğun) profillerinin ortalaması, aylık mevsim katsayılarıyla |
| Santral | Yıllık üretim = yıllık ihtiyaç olacak şekilde; güneş/rüzgâr oranı saatlik açığı en aza indirecek biçimde aranır. **Nokta bir kaynağa uygun değilse o kaynak kullanılmaz.** Rüzgâr için MW sınıfı Enercon E-82/2300 (windpowerlib) |
| Batarya | Tipik (medyan) günde fazlanın geceye taşınabilecek kısmı; gücü saatlik açığın %95'lik dilimi |
| Şebekeye verme sınırı | O saatte KKTC'nin geri kalanının ihtiyacı (fazla üretim diğer ilçelere gider) |
| Kapasite taraması | Önerilen santralin katları (×0,5 … ×1,5; batarya ×0 … ×2) |

Kaynaklar: ilçe nüfusları ve 2021 tahmini [citypopulation.de](https://citypopulation.de/en/cyprus/cities/north/); 2011 tüketim [EMO](https://www.emo.org.tr/ekler/3665cbb005c1545_ek.pdf?dergi=905); 2011 toplam nüfus [Sözcü / KKTC İstatistik Kurumu](https://www.sozcu.com.tr/kktcnin-nufusu-aciklandi-wp7410908). Kaynak: `scripts/rapor.py --sehir`, geçmiş yıl verisi 2025.

| Bölge | İlçe | İlçe ihtiyacı | Uygunluk | Önerilen santral | Batarya | Bataryasız | Bataryalı | Kurulu / ort. ihtiyaç |
|---|---|---|---|---|---|---|---|---|
| Gazimağusa | Gazimağusa | 417,0 GWh | Yalnızca güneşe uygun | 236,1 MWp güneş | 504,8 MWh / 69,4 MW | %49 | %84 | 5,0× |
| Dipkarpaz | İskele | 134,5 GWh | Yalnızca güneşe uygun | 77,3 MWp güneş | 162,2 MWh / 22,4 MW | %49 | %83 | 5,0× |
| Beşparmak | Girne | 413,6 GWh | Yalnızca rüzgâra uygun | 1.210,9 MW rüzgâr (527 × E-82) | 92,2 MWh / 68,5 MW | %40 | %45 | 25,6× |
| Kormacit hattı | Girne | 413,6 GWh | İkisine de uygun değil | — (önerilmez) | — | — | — | — |
| Kantara | İskele | 134,5 GWh | Yalnızca rüzgâra uygun | 225,5 MW rüzgâr (99 × E-82) | 21,5 MWh / 22,2 MW | %43 | %46 | 14,7× |
| Alevkayası | Girne | 413,6 GWh | Yalnızca rüzgâra uygun | 1.280,0 MW rüzgâr (557 × E-82) | 73,7 MWh / 69,5 MW | %38 | %42 | 27,1× |
| Karpaz Yarımadası | İskele | 134,5 GWh | İkisine de uygun değil | — (önerilmez) | — | — | — | — |
| Serhatköy | Güzelyurt (Lefke dahil) | 179,6 GWh | Yalnızca güneşe uygun | 101,5 MWp güneş | 218,3 MWh / 29,9 MW | %49 | %83 | 4,9× |
| Geçitkale | Gazimağusa | 417,0 GWh | Yalnızca güneşe uygun | 237,6 MWp güneş | 507,2 MWh / 69,4 MW | %49 | %84 | 5,0× |
| Güzelyurt (Yüzer GES) | Güzelyurt (Lefke dahil) | 179,6 GWh | Yalnızca güneşe uygun | 101,5 MWp güneş | 218,4 MWh / 29,9 MW | %49 | %83 | 4,9× |
| Geçitköy (Yüzer GES) | Girne | 413,6 GWh | İkisine de uygun değil | — (önerilmez) | — | — | — | — |

**Ne anlama geliyor?**
- **11 örnek sahanın hiçbiri "ikisine de uygun" alanda değil**, bu yüzden hiçbirinde hibrit önerilmiyor. Hibrit için sahayı uygunluk katmanının boyasız alanlarından seçmek gerekiyor. Örneğin İskele kırsalında (35,33 K, 33,98 D) önerilen santral %45 rüzgâr içeren bir karışım; bataryasız karşılama %60 (yalnız güneşle %49), bataryalı %74.
- Güneş sahaları ilçe ihtiyacını bataryayla **%83–84** karşılıyor; kurulu güç ortalama ihtiyacın ~5 katı (5,0×).
- Dağlık rüzgâr noktalarında (Beşparmak, Alevkayası) kurulu güç ortalama ihtiyacın 25–27 katına çıkıyor: rüzgâr kaynağı zayıf, bu noktalar şehir ölçeği için verimsiz.
- Kormacit, Karpaz ve Geçitköy koruma alanında: santral önerilmiyor.
- Maliyetler Ayarlar › Gelişmiş'teki **santral ölçeği** varsayımlarıdır (güneş 0,65 $/W, rüzgâr 1.500 $/kW, batarya 300 $/kWh) `[yerel tekliflerle doğrulanacak]`.

## Saha uygunluk katmanı (kısıt bölgeleri)

OpenStreetMap'ten `scripts/kisit_bolgeleri.py` ile üretilir; uygulamada Harita'da renkli poligonlar ve KKTC kara sınırıyla gösterilir. Renkler **uygunluğu** gösterir:

| Renk | Anlam | Alan (KKTC karası 3.240 km²) |
|---|---|---|
| 🔴 Kırmızı | İkisine de uygun değil | 511 km² |
| 🟡 Sarı | Yalnızca güneşe uygun (rüzgâr kısıtlı) | 750 km² |
| 🔵 Mavi | Yalnızca rüzgâra uygun (güneş kısıtlı) | 436 km² |
| Boyasız | Bilinen kısıt yok, ikisine de uygun | kalan |

| Kod | Kısıt | Etkilediği kaynak | Kaynak / kural |
|---|---|---|---|
| A01 | BM ara bölgesi | ikisi | OSM ara bölge (KKTC sınırına 3 km yakın kısım) |
| A02 | Askerî alan | ikisi | OSM `landuse=military` |
| A03 | Koruma alanı (ÖÇKB, milli park, doğa koruma) | ikisi | OSM korunan alan |
| A04 | Havalimanı | ikisi | OSM `aeroway=aerodrome` |
| R01 | Havalimanına yakın (~5 km) | rüzgâr | Uçuş güvenliği / radar (yaklaşık) |
| R02 | Yerleşime yakın (konut alanı +300 m, köy 500 m, kasaba 1,5 km) | rüzgâr | Gürültü ve gölge titreşimi (yaklaşık) |
| R03 | Su yüzeyi | rüzgâr | Türbin kurulamaz; yüzer GES olabilir |
| G01 | Orman alanı | güneş | Ağaç kesimi ve gölge (rüzgâr için orman izni) |

**Örnek sahaların uygunluğu**

| Saha | Uygunluk | Kod |
|---|---|---|
| Kormacit hattı | 🔴 ikisine de uygun değil | A03 Akdeniz ÖÇKB |
| Karpaz Yarımadası | 🔴 ikisine de uygun değil | A03 Karpaz ÖÇKB |
| Geçitköy (Yüzer GES) | 🔴 ikisine de uygun değil | A03 Akdeniz ÖÇKB, R03 su yüzeyi |
| Kantara, Alevkayası, Beşparmak | 🔵 yalnızca rüzgâra uygun | G01 orman |
| Gazimağusa, Dipkarpaz, Serhatköy, Güzelyurt | 🟡 yalnızca güneşe uygun | R02 yerleşime yakın |
| Geçitkale | 🟡 yalnızca güneşe uygun | R01 havalimanına yakın, R02 |

**Önemli bulgu:** Metindeki en güçlü rüzgâr adayları (Kormacit, Karpaz) koruma alanı içinde kalıyor; rüzgâr santrali için koruma alanı dışında, yerleşime ve havalimanına uzak alanlar taranmalı. Uygulamada harita bu alanları boyasız gösterir.

Mesafeler yaklaşık planlama değerleridir; kesin sınır için ilgili kurumların (çevre, sivil havacılık, orman, askerî) izni gerekir. OSM eksik olabilir; boyasız alan "kısıt yok" garantisi değildir.

## Yerel kaynaklar

| İhtiyaç | Yerelde karşılanma | Durum |
|---|---|---|
| Panel ve inverter kurulumu | Güneş paneli kurulum firmaları | `[2–3 firmadan teklif al]` |
| Küçük türbin ve takipçi | İthalat gerekebilir | `[tedarikçi araştır]` |
| Elektrik tesisatı ve şebeke bağlantısı | Lisanslı elektrikçi + KIB-TEK onayı | `[bağlantı prosedürünü yaz]` |
| Yazılım | 2–3 kişilik ekip; açık kaynak araçlar | ✅ |
| Veri | Open-Meteo (tahmin + ECMWF IFS ~9 km arşiv): ücretsiz, anahtarsız | ✅ |
| Barındırma | Tek küçük sunucu veya ücretsiz katman | ✅ |

## Mevzuat

Şebekeye verme **hedeflerimizden biri**. Ancak mevzuat netleşene kadar varsayılan olarak **3 kW ile sınırlı** tutuluyor; 0 yapılırsa sistem hiç vermez. Uygulama her durumda çalışır: limit 0 iken akıllı yönetim basit kurala eşitlenir, kısılan enerji raporlanır. `[KKTC'de şebekeye verme / net ölçüm mevzuatını ekle]`

## Yol haritası

| Aşama | İçerik | Süre |
|---|---|---|
| 1 · Prototip (şimdi) | Panel, harita, senaryolar, akıllı EMS simülasyonu | Hackathon |
| 2 · Öneri motoru | Açı ve yön önerisinin sahada doğrulanması, maliyet verisi, PDF teklif çıktısı | 1–2 ay |
| 3 · Pilot | 1 kamu binası + 1 ticari tesis; gerçek sayaç ve BMS verisi; tahmin hatası ölçümü | 3–6 ay |
| 4 · Gömülü EMS | Rust ile cihaz içi kontrol; uygulama izleme paneli olur | 6–12 ay |

## Riskler

| Risk | Etki | Önlem |
|---|---|---|
| Bölgesel modelin yerel rüzgârı (sırt, burun) düşük göstermesi | Rüzgâr kararları yanlış olur | Pilot noktada ölçüm direği; daha yüksek çözünürlüklü kaynak |
| Mevzuatın şebekeye vermeyi kısıtlaması | Gelir azalır | Limit ayarlanabilir; akıllı EMS kısılan enerjiyi en aza indirir |
| Maliyetlerin değişmesi | Fizibilite değişir | Tüm maliyetler arayüzden güncellenebilir |
| Tahmin hatası | Akıllı yönetimin katkısı azalır | %10 güvenlik payı; pilotta ölçülecek |

## Açık işler

- [ ] 2–3 yerel kurulumcudan panel + batarya + türbin teklifi al; tabloyu güncelle
- [ ] KIB-TEK tarifesini ve şebekeye bağlantı prosedürünü ekle
- [ ] Kişi başı tüketimi güncel KIB-TEK satış verisiyle güncelle (2011 değeri kullanılıyor) ve ilçe bazında tüketim verisi bul
- [ ] Uygunluk katmanını resmi verilerle doğrula (ÖÇKB sınırları, askerî bölgeler, sivil havacılık engel yüzeyleri)
- [ ] Kormacit, Kantara ve Alevkayası zirveleri için rüzgâr atlası (~250 m) karşılaştırması veya ölçüm direği planı
- [ ] Yüzer GES için su üstü sıcaklık modeli (pvlib'de Faiman katsayılarıyla) ve maliyet farkı
