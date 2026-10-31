# K2 · Yenilikçilik, Özgünlük ve Katma Değer (%20)

> **Jüri sorusu:** Önerilen çözüm, mevcut yaklaşımlardan farklılaşan, yenilikçi ve özgün bir değer sunuyor mu?

**Son güncelleme:** 31.10.2026 · **Durum:** 🟡 rakip karşılaştırması genişletilecek

---

## Sunumda söylenecek kısa cevap

Piyasadaki çözümlerin çoğu ya yalnızca güneşe bakar ya da bataryayı "doldur, sonra boşalt" kuralıyla yönetir. Biz üç şeyi birlikte yapıyoruz:

1. Güneş ile rüzgârın birbirini tamamlayıp tamamlamadığını varsaymıyor, her nokta için saatlik veriyle **ölçüyoruz**.
2. Bataryayı **hava tahminine bakarak** yönetiyoruz. Gazimağusa'da boşa giden enerji yılda 340 kWh'ten 14 kWh'e iniyor.
3. Aynı sistemi **bütçeye göre kademeli** sunuyoruz. Ucuz sürümde panel açısını ve türbin yönünü uygulama hesaplıyor.

## Değerlendirme ölçütleri

| Ölçüt | Cevabımız | Kanıt | Durum |
|---|---|---|---|
| Mevcut çözümlerden hangi yönleriyle ayrışıyor? | Aşağıdaki karşılaştırma tablosu | — | 🟡 |
| Yaratıcı ve yenilikçi yaklaşım var mı? | Tahmine dayalı ihracat-öncelikli şarj; varsayımsız tamamlayıcılık testi; bütçe kademeli kurulum ve açı/yön önerisi | Senaryolar S4a ↔ S4; Harita | ✅ |
| Somut iyileştirme veya katma değer var mı? | Kısılan enerjide %58–100 azalma (11 bölge); hibritte üretimsiz saatlerde 29 puana kadar düşüş | "Somut katma değer" tablosu | ✅ |

## Mevcut yaklaşımlarla karşılaştırma

| Özellik | Tipik çatı güneş sistemi | Potansiyel araçları (ör. PVGIS) | İnverter izleme uygulamaları | **Bizim çözüm** |
|---|---|---|---|---|
| Güneş + rüzgâr birlikte | ✗ | Yalnızca güneş | ✗ | ✅ (pvlib + windpowerlib) |
| Tamamlayıcılık saatlik veriyle test edilir | ✗ | ✗ | ✗ | ✅ korelasyon + güneşsiz saat payı |
| Batarya yönetimi | Basit kural | — | Basit kural / zaman programı | ✅ tahmine dayalı (akıllı) |
| Şebekeye verme limitini akıllıca kullanma | ✗ | — | Kısmen | ✅ önce limit, sonra batarya; batarya akşama dolu |
| Bütçe kademeli kurulum (sabit ↔ takipçi, otomatik ↔ sabit türbin) | Tek seçenek | Açı hesabı var | ✗ | ✅ + sabit türbin için en iyi yön |
| Son kullanıcı girdisi | Kurulumcu yapar | Teknik parametreler | — | ✅ yalnızca etiket değerleri |
| Saha uygunluk katmanı (koruma, askerî, havalimanı, yerleşim, orman) ve kısıt kodları | ✗ | ✗ | ✗ | ✅ kırmızı / sarı / mavi |
| Harita üzerinden herhangi bir nokta | — | ✅ | ✗ | ✅ + rüzgâr ve uygunluk değerlendirmesi |
| Bölge × senaryo × kapasite karşılaştırması | ✗ | ✗ | ✗ | ✅ 4 senaryo, 76 kapasite kombinasyonu |

`[YAPILACAK: KKTC'de satılan 2–3 ticari paketi bu tabloya ekle]`

## Yeniliğin özü: tahmine dayalı akıllı yönetim

**Basit kural:** Fazla üretim önce bataryaya gider, sonra şebekeye, o da doluysa kısılır. Sonuç: batarya öğlene kadar dolar; öğleden sonra hem batarya dolu hem şebeke limiti dolu olur ve enerji boşa gider.

**Akıllı kural (bizim):** Sistem, içinde bulunulan "fazla üretim döneminin" geri kalanına tahminle bakar. Batarya akşama kadar zaten dolacaksa önce şebeke limitini kullanır, bataryaya yalnızca limitin üstündeki fazlayı yükler. Batarya yine akşama dolu girer (öz yeterlilik değişmez), ama öğlen boşa giden enerji neredeyse sıfırlanır ve şebekeye daha fazla temiz enerji verilir.

Kod: `hibrit_enerji/core/ems.py`. Test: `tests/test_core.py::test_smart_curtails_less_without_hurting_self_sufficiency`.

## Somut katma değer (güncel sonuçlar)

Kaynak: `scripts/rapor.py`, geçmiş yıl verisi (ECMWF IFS ~9 km, Open-Meteo arşivi, 2025), varsayılan sistem (5,5 kWp + 3 kW + 10 kWh, şebekeye verme sınırı 3 kW).

| Bölge | Kısılan kWh/yıl: basit → akıllı | Şebekeye verilen kWh/yıl: basit → akıllı | Öz yeterlilik (ikisinde de) |
|---|---|---|---|
| Gazimağusa | 340 → **14** (−%96) | 4.443 → 4.769 | %97 |
| Dipkarpaz | 405 → **68** (−%83) | 4.980 → 5.316 | %98 |
| Beşparmak | 281 → **1** (−%100) | 4.195 → 4.475 | %95 |
| Kormacit hattı | 654 → **117** (−%82) | 5.106 → 5.644 | %98 |
| Karpaz Yarımadası | 821 → **341** (−%58) | 6.730 → 7.211 | %99 |

| Bölge | Takipçinin sabit panele göre kazancı | Hibritin üretimsiz saati azaltması |
|---|---|---|
| Gazimağusa | +%38 | %51 → %43 |
| Dipkarpaz | +%38 | %51 → %33 |
| Beşparmak | +%39 | %51 → %49 |
| Karpaz Yarımadası | +%38 | %51 → **%20** |

> Not: Simülasyondaki akıllı yönetim kusursuz tahmin varsayar. Sahada tahmin hatası etkiyi azaltır (K3 "Bilinen sınırlar").

## Açık işler

- [ ] Tahmin hatası eklenmiş simülasyon (ör. ±%20 gürültü) ile akıllı yönetimin dayanıklılığını göster
- [ ] KKTC'deki ticari paketlerle karşılaştırmayı tamamla
- [ ] Zamana bağlı tarife gelirse, fiyat farkından kazanç sağlayan (arbitraj) modu ekle
