# K1 · Problem Tanımı ve Çözüm Uyumu (%20)

> **Jüri sorusu:** Takım, çözmeyi hedeflediği problemi doğru tanımlamış ve bu probleme uygun bir çözüm geliştirmiş mi?

**Son güncelleme:** 31.10.2026 · **Durum:** 🟡 taslak (kaynaklar eklenecek)

---

## Sunumda söylenecek kısa cevap

Kuzey Kıbrıs elektriğini büyük ölçüde fosil yakıtla üretiyor. Tek başına güneş paneli de günün yarısında hiç üretmiyor. Biz kamu kurumları ve şirketler için güneşi, rüzgârı, bataryayı ve tahmine dayalı akıllı yönetimi bir araya getiren bir sistem tasarladık. Hangi bölgede (kısıt alanları dahil), hangi kapasitede ve hangi kontrol stratejisiyle verimli çalışacağını saatlik meteoroloji verisiyle gösteriyoruz.

## Değerlendirme ölçütleri

| Ölçüt | Cevabımız | Kanıt (uygulamada) | Durum |
|---|---|---|---|
| Hedef kitle ve ihtiyaçları doğru belirlenmiş mi? | Kamu kurumları (belediye, bakanlık, okul/hastane yerleşkeleri, KIB-TEK planlaması) ve şirketler (otel, sanayi, ticari tesis, enerji yatırımcısı). Farklı bütçeler için kademeli kurulum. | Ayarlar: "Tesis tipi"; Harita: uygunluk katmanı | ✅ |
| Problemin gerçekliği ve önemi ortaya konmuş mu? | Güneş tek başına günün ~%51'inde üretmiyor; akşam tüketim zirvesi güneşsiz saatlere denk geliyor. | Senaryolar: S1 "Üretimsiz saat %51" | 🟡 resmi enerji istatistiği eklenecek |
| Çözüm problemle doğrudan ilişkili mi? | Aşağıdaki "problem → çözüm" tablosuna bakınız. | Tüm sayfalar | ✅ |

## Problem

1. **Fosil yakıt bağımlılığı ve yakıt maliyeti.** KKTC elektriği ağırlıkla fuel-oil santrallerinden geliyor. `[KAYNAK: KIB-TEK / resmi üretim istatistiği eklenecek]`
2. **Yenilenebilirin değişkenliği.** Güneş gündüz yüksek üretir, akşam ve gece sıfıra düşer. 2025 saatlik verisiyle, Gazimağusa'daki sabit panel yılın **%51** saatinde üretim yapmıyor.
3. **Rüzgârın güneşi tamamlayıp tamamlamadığı bilinmiyor.** Bunu **varsaymıyoruz**; her bölge için saatlik veriyle **test ediyoruz** (proje özetindeki not).
4. **Son kullanıcı teknik değil.** Panel açısı, türbin yönü ve batarya boyutu gibi kararlar uzman bilgisi gerektiriyor.
5. **Bütçe farkı.** Herkes güneş takipçili sistem ve otomatik yönlenen türbin alamaz.

## Hedef kitle ve ihtiyaçları

| Kitle | İhtiyaç | Ürünün karşılığı |
|---|---|---|
| Kamu kurumu / belediye (yerleşke, okul, hastane) | Enerji maliyetini düşürmek, kesintiye dayanıklılık, kamuya örnek olmak | Tesis tipi "Kamu / yerleşke"; batarya + akıllı yönetim; günlük "tüketim nereden karşılandı" görünümü |
| Şirket — otel, ticari ve sanayi tesisi | Gündüz yoğun tüketim, maliyet öngörüsü, sürdürülebilirlik raporu | Tesis tipi "Ticari / sanayi"; kapasite taraması, geri ödeme süresi, CO₂ göstergesi |
| Enerji yatırımcısı / KIB-TEK planlaması | Santral için uygun saha seçimi; seçilen noktadaki santral ilçenin ihtiyacını karşılar mı? | Harita: uygunluk katmanı (kırmızı / sarı / mavi) + kısıt kodları; Veriler: ilçe ihtiyacı, noktaya göre boyutlanan santral ve karşılama oranları |
| Düşük bütçeli kurum | Ucuz kurulum | Sabit panel + uygulamanın hesapladığı en iyi açı; sabit türbin veya dikey eksenli türbin (VAWT) |

## Problem → çözüm eşlemesi

| Problem | Çözüm bileşeni | Nerede |
|---|---|---|
| Güneşin akşam ve gece üretmemesi | Rüzgâr + batarya; batarya akşama dolu girecek şekilde planlanır | Ana sayfa "Önümüzdeki 24 saat", EMS |
| Değişkenlik | Hibrit üretim; saatlik dalgalanma ve üretimsiz saat ölçülür | Senaryolar: "Dalgalanma (CV)", "Üretimsiz saat" |
| Tamamlayıcılık belirsizliği | Güneş–rüzgâr korelasyonu ve rüzgârın güneşsiz saatlerdeki payı hesaplanır | Harita: "Hibrit (tamamlayıcılık testi)" |
| Teknik olmayan kullanıcı | Yalnızca etiket değerleri istenir; açı ve yönü uygulama hesaplar; özet sayfalarda sade dil | Ayarlar, Ana sayfa |
| Yanlış sahaya kurulum | Uygunluk katmanı: kırmızı (ikisine de uygun değil), sarı (yalnızca güneş), mavi (yalnızca rüzgâr) + kısa kısıt kodları | Harita |
| Bütçe farkı | Sabit ↔ takipçi, otomatik ↔ sabit türbin seçenekleri ve kayıplarının gösterilmesi | Harita: "Kurulum önerisi" |
| Fazla üretimin boşa gitmesi | Şebekeye limit dahilinde verme + akıllı EMS ile daha az kısılan enerji | Senaryolar: S4a ↔ S4 |

## Güncel sonuçlar (veriyle problem kanıtı)

Kaynak: `scripts/rapor.py`, geçmiş yıl verisi (ECMWF IFS ~9 km, Open-Meteo arşivi, 2025), varsayılan sistem.

| Bölge | Üretimsiz saat: yalnızca güneş → hibrit | Öz yeterlilik: yalnızca güneş → hibrit + batarya + akıllı |
|---|---|---|
| Gazimağusa | %51 → %43 | %43 → %97 |
| Dipkarpaz | %51 → %33 | %43 → %98 |
| Beşparmak | %51 → %49 | %43 → %95 |
| Karpaz Yarımadası | %51 → **%20** | %43 → %99 |
| Kormacit hattı | %51 → %36 | %43 → %98 |

Rüzgârın güneşsiz saatleri belirgin biçimde azalttığı yerler **Karpaz Yarımadası**, **Kormacit** ve **Dipkarpaz**. İç ve dağlık noktalarda (Beşparmak, Alevkayası, Geçitkale) rüzgâr zayıf; ayrıntılar K4'te.

## Açık işler

- [ ] KKTC elektrik üretim karışımı ve yakıt maliyeti için resmi kaynak ekle
- [ ] Hedef kitle için 3–5 kısa görüşme yap (belediye enerji sorumlusu, otel / sanayi tesisi yöneticisi) ve bulguları buraya yaz
- [ ] Kesinti sıklığı verisi bul (ada modu ihtiyacını desteklemek için)
