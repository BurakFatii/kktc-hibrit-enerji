# StickS3 Yön Bulucu

M5Stack StickS3 ile güneş paneli ve rüzgâr türbini yönlendirme yardımcısı.
Cihaz, Reflex'le aynı bilgisayarda koşan yerli API'den anlık hedefi çeker;
ekran + kısık sesli biplerle "Bul" uygulamasındaki gibi hedefe götürür.

## Donanım

- M5Stack StickS3 (ESP32-S3, 135×240 ekran, BMI270 IMU, hoparlör, 2 buton)
- StickS3'ün pusulası (manyetometre) **yoktur**: yaw gyro tümleviyle bulunur,
  kuzeye tutup yan butona basarak sıfırlanır. Dakikalar içinde birkaç derece
  kayabilir; kilit öncesi BtnB ile tazelenir.

## Kurulum

1. Arduino IDE'ye kart paketi: Dosya → Tercihler → Ek kart URL'si:
   `https://m5stack.oss-cn-shenzhen.aliyuncs.com/resource/arduino/package_m5stack_index.json`,
   sonra Kart Yöneticisi'nden `M5Stack` (StickS3 seçilir).
2. Kütüphane Yöneticisi'nden: `M5Unified`, `M5GFX`, `ArduinoJson` (v7).
3. `sticks3-yonlendirme.ino` dosyasını açın, üstteki AYARLAR'ı doldurun:
   - `WIFI_SSID` / `WIFI_PASS` — bilgisayarınızla **aynı 2.4 GHz ağ**
   - `API_HOST` — Reflex'i çalıştıran bilgisayarın **yerel IP'si**
     (`localhost` yazılmaz; örn. `192.168.1.50`)
   - `LAT` / `LON` — uygulamayla aynı konum
4. Yükleyin.

## API'yi başlatma (bilgisayarda)

```bash
.venv/bin/python -m hibrit_enerji.orientation_api --port 8001
```

Sağlık: `http://YEREL_IP:8001/api/saglik`
Veri: `http://YEREL_IP:8001/api/yonlendirme?lat=35.1856&lon=33.3823`

Hedefler `core/`'dan gelir (pvlib güneş konumu + windpowerlib göbek
rüzgârı); yeni fizik formülü içermez.

## Kullanım

| Tuş | İşlev |
|---|---|
| Ön buton (A) | GÜNEŞ ↔ RÜZGAR arayüzü değiştirir |
| Yan buton (B, kısa) | Ses DÜŞÜK → ORTA → YÜKSEK → DÜŞÜK döner (yeni düzey ekranda yazıp örnek bip çalar) |
| Yan buton (B, 1 sn basılı) | Cihaz kuzeye bakarken yaw sıfırlanır (`KUZEY SIFIRLANDI`) |

- Cihazı panel arkasına / direğe ekran dışa bakacak, üst kenar "ileri"
  yönde olacak şekilde düz bantlayın.
- Yaklaştıkça bip sıklaşır ve tizleşir; bozuk eksen perdesinden anlaşılır
  (yaw: kalın, eğim: ince). `<4°` yaw + `<3°` eğimde yeşil **KİLİTLENDİ**
  ekranı ve yükselen 3 nota gelir.
- Mod değişiminde kulak ikonu: güneş tek tiz bip, rüzgâr çift kalın bip.
- Gece saatlerinde güneş hedefi park konumudur (doğu, 0 eğim).
- `WiFi yok` / `veri yok` yazıyorsa önce API'nin ayakta olduğunu ve
  IP'yi doğrulayın.
