# K5 · Sürdürülebilirlik ve Etki Potansiyeli (%20)

> **Jüri sorusu:** Proje, sürdürülebilir enerji, şehirler ve/veya turizm alanlarında anlamlı, ölçülebilir ve uzun vadeli bir çevresel veya toplumsal fayda yaratma potansiyeline sahip mi?

**Son güncelleme:** 31.10.2026 · **Durum:** 🟡 emisyon faktörü resmi veriyle güncellenecek

---

## Sunumda söylenecek kısa cevap

Tek bir tesiste (aylık 450 kWh örnek tüketim) sistem, tüketimin %95–99'unu yenilenebilirle karşılıyor ve yılda yaklaşık 7–9 ton CO₂ salımını önlüyor. Bu etkiyi uygulama içinde **ölçülebilir göstergelerle** raporluyoruz. Veri kaynağı tüm dünyayı kapsadığı için sistem KKTC'nin her noktasına ve başka bölgelere yaygınlaştırılabilir.

## Değerlendirme ölçütleri

| Ölçüt | Cevabımız | Kanıt | Durum |
|---|---|---|---|
| Çevresel ve toplumsal faydalar açık mı? | Fosil yakıt kullanımı ve CO₂ azalır; fatura düşer; kesintiye dayanıklılık artar; turizm tesislerinde temiz enerji | Aşağıda | ✅ |
| Etki somut göstergelerle ölçülebilir mi? | 7 gösterge, uygulamada otomatik hesaplanıyor | Senaryolar tablosu | ✅ |
| Uzun vadede sürdürülebilir ve yaygınlaştırılabilir mi? | Ücretsiz küresel veri, açık kod, harita ile her nokta, işletme profili | Aşağıda | ✅ |

## Ölçülebilir göstergeler

| Gösterge | Tanım | Uygulamada |
|---|---|---|
| Öz yeterlilik (%) | Tüketimin yenilenebilirle karşılanan payı | Senaryolar |
| Enerji açığı (kWh/yıl) | Şebekeden çekilen | Senaryolar |
| Kısılan enerji (kWh/yıl) | Üretilip kullanılamayan, boşa giden | Senaryolar |
| Şebekeye verilen (kWh/yıl) | Şebekeye aktarılan temiz enerji | Senaryolar |
| Dalgalanma (CV) ve üretimsiz saat (%) | Üretimin ne kadar istikrarlı olduğu | Senaryolar |
| Önlenen CO₂ (t/yıl) | (kendi tüketilen + şebekeye verilen) × 0,70 kg/kWh | Senaryolar |
| Geri ödeme (yıl) | Yatırım / yıllık tasarruf | Senaryolar |

## Güncel sonuçlar (tek tesis, aylık 450 kWh, S4: hibrit + batarya + akıllı)

Kaynak: `scripts/rapor.py`, geçmiş yıl verisi (ECMWF IFS ~9 km, Open-Meteo arşivi, 2025).

| Bölge | Öz yeterlilik | Şebekeye verilen kWh/yıl | Önlenen CO₂ t/yıl |
|---|---|---|---|
| Gazimağusa | %97 | 4.769 | 7,0 |
| Dipkarpaz | %98 | 5.316 | 7,4 |
| Beşparmak | %95 | 4.475 | 6,7 |
| Karpaz Yarımadası | %99 | 7.211 | 8,8 |

**Ölçek örneği:** 1.000 benzer tesis × ~7,0 t ≈ **7.000 t CO₂/yıl**; tüketim büyüdükçe (kamu yerleşkesi, otel, sanayi) etki doğrusal artar. `[Emisyon faktörü 0,70 kg/kWh bir varsayımdır; KIB-TEK verisiyle güncellenecek.]`

**Şehir ölçeği (K4):** Güneş sahalarında önerilen santral + batarya, bulunduğu ilçenin yıllık elektrik ihtiyacının **%83–84**'ünü saat saat karşılıyor (Gazimağusa ilçesi için 236 MWp güneş + 505 MWh batarya, ihtiyaç 417 GWh/yıl).

## Faydalar

**Çevresel:** Fosil yakıt tüketimi ve CO₂ azalır. Akıllı yönetim boşa giden yenilenebilir enerjiyi 11 bölgede %58–100 azaltır (K2).

**Toplumsal:** Fatura düşer. Kesintide tesis ada modunda çalışır. Düşük bütçeli sürüm (sabit panel, sabit veya dikey eksenli türbin) sayesinde farklı gelir gruplarına ulaşılır.

**Şehirler:** Fazla enerji, şebekeye limit dahilinde ve öngörülebilir biçimde verilir. Bu, şebekeye daha dengeli bir katkı demektir.

**Turizm:** Otel ve işletmeler için "İşletme" tüketim profili var. Turizm sezonu, güneşin en güçlü olduğu yaz aylarına denk geliyor.

## Yaygınlaştırma

- **Coğrafi:** Open-Meteo verileri tüm dünyayı kapsar. Haritada herhangi bir nokta analiz edilebilir.
- **Kitle:** Kamu kurumları, belediyeler, şirketler ve enerji yatırımcıları. Uygunluk katmanı ve bölge karşılaştırması saha planlamasında kullanılır.
- **Teknik:** Açık kod, ücretsiz veri, standart donanım. Lisans maliyeti yok.
- **Uzun vade:** Gerçek sayaç ve BMS verisi bağlandıkça tahminler kalibre edilir. EMS, gömülü cihaza (Rust) taşınır.

## Açık işler

- [ ] KKTC şebeke emisyon faktörünü resmi kaynakla güncelle
- [ ] Turizm senaryosu: 50 odalı otel için örnek hesap
- [ ] Fosil yakıt tasarrufunu litre fuel-oil olarak göster (santral verimi kaynağıyla)
