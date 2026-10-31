// sticks3-yonlendirme.ino — M5Stack StickS3 panel / türbin yön bulucu.
//
// İki arayüz, ön butonla (BtnA) değişir:
//   GÜNEŞ  : panel normalini güneşe çevir (yaw = güneş azimutu, eğim = güneş yüksekliği)
//   RÜZGAR : türbin rotoru rüzgâra dönsün (yaw = rüzgârın GELDİĞİ yön, eğim = 0 yatay)
//
// Hedefler Reflex'le aynı bilgisayarda koşan yerli API'den gelir
// (hibrit_enerji/orientation_api.py, :8001). Cihaz 5 sn'de bir sorar.
//
// YÖN ÖLÇÜMÜ (BMI270'de pusula YOK; gerekli olan yalnızca yaw + eğim):
//   yaw   = gyro-z tümlevi (göreli; kuzeye tutup YAN butona (BtnB) 1 sn basınca sıfırlanır)
//   eğim  = ivmeölçerden yatayla açı (durağan, kararlı)
//   roll (normal çevresi dönüş) BİLEREK kullanılmaz: düz panelin baktığı yönü ve
//   yatay türbinin rüzgâr alışını değiştirmez. Cihaz panele/direğe düz bantlanır;
//   bu montajda cihaz z-ekseni düşeye yakın olduğundan gyro-z ≈ saf yaw'dır.
// SES: BtnB kısa basış DÜŞÜK -> ORTA -> YÜKSEK döner.
// Ses + ekran, Apple "Bul"daki yönlendirmeye benzer: yaklaştıkça bip sıklaşır ve
// tizleşir (yaw bozuksa kalın 500-800 Hz, eğim bozuksa ince 900-1400 Hz);
// kilitlenince (<4° yaw, <3° eğim) yeşil KİLİT ekranı ve yükselen 3 nota.
// Mod değişiminde kulak ikonu: güneş tek tiz, rüzgar çift kalın bip.
//
// MONTAJ: cihazı panelin arkasına ya da direğe ekran dışa bakacak, üst kenarı
// "ileri" (panel normali / rotor ekseni) yönünde olacak şekilde düz bantlayın.
//
// Gerekli: Arduino IDE + "M5Stack" kart paketi (StickS3) + M5Unified + M5GFX + ArduinoJson(v7).
#include <M5Unified.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ---------------- AYARLAR (kendi ağınıza göre değiştirin) ----------------
static const char* WIFI_SSID = "SUPER 5G";
static const char* WIFI_PASS = "SUPER.5G";
static const char* API_HOST = "192.168.0.165";  // Reflex'i çalıştıran PC'nin YEREL IP'si
static const int API_PORT = 8001;
static const float LAT = 35.1856;  // Lefkoşa yedeği; uygulamayla aynı konum olmalı
static const float LON = 33.3823;
static const unsigned long POLL_MS = 5000;
// --------------------------------------------------------------------------

enum Mod : uint8_t { MOD_GUNES, MOD_RUZGAR };

Mod mod = MOD_GUNES;
float hedefYaw = 180.0;   // derece: güneş azimutu ya da rüzgâr geliş yönü
float hedefEgim = 30.0;   // derece: güneş yüksekliği ya da 0 (türbin yatay)
float gunesAz = 180.0, gunesEgim = 30.0, ruzgarYon = 315.0;
float ruzgarHiz = 0.0;  // bilgi amaçlı (m/s)
bool gece = false;
bool veriVar = false;
unsigned long sonPoll = 0;

// IMU durumu
float yaw = 0.0;  // BtnB uzun basış anı = manyetik kuzey kabul edilir
unsigned long sonImuMs = 0;
bool kilit = false;

// Ses düzeyi: DÜŞÜK -> ORTA -> YÜKSEK -> DÜŞÜK ... (BtnB kısa basış)
static const uint8_t SESLER[] = {48, 110, 170};
static const char* SES_ADI[] = {"DUSUK", "ORTA", "YUKSEK"};
uint8_t sesIdx = 0;
bool uzunB = false;  // BtnB uzun basış tetiklendi mi
bool kuzeyGoster = false;  // son işlem yaw sıfırlama mıydı
unsigned long sesGosterMs = 0;  // bilgi satırı ekranda ne zamana kadar kalsın

static float sar(float a) {  // -180..+180 aralığına sar
  while (a > 180.0) a -= 360.0;
  while (a < -180.0) a += 360.0;
  return a;
}

void hedefiUygula();  // ön bildirim

void apiSor() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.setTimeout(4000);
  String url = String("http://") + API_HOST + ":" + API_PORT + "/api/yonlendirme?lat=" +
               String(LAT, 4) + "&lon=" + String(LON, 4);
  http.begin(url);
  int kod = http.GET();
  if (kod == 200) {
    JsonDocument doc;
    if (!deserializeJson(doc, http.getString())) {
      gunesAz = (float)doc["gunes"]["az_deg"];
      gunesEgim = (float)doc["gunes"]["egim_deg"];
      ruzgarYon = (float)doc["ruzgar"]["gelis_yonu_deg"];
      ruzgarHiz = (float)doc["ruzgar"]["govbek_hizi_ms"];
      gece = (bool)doc["gunes"]["gece"];
      hedefiUygula();
      veriVar = true;
    }
  }
  http.end();
}

// Son yanıttaki hedefi aktif moda uygula.
void hedefiUygula() {
  if (mod == MOD_GUNES) {
    hedefYaw = gunesAz;
    hedefEgim = gunesEgim;
  } else {
    hedefYaw = ruzgarYon;
    hedefEgim = 0.0;
  }
}

void setup() {
  auto cfg = M5.config();
  M5.begin(cfg);
  M5.Display.setRotation(1);  // 240x135 yatay
  M5.Display.setTextSize(2);
  M5.Speaker.setVolume(48);  // bilerek kısık (~%20)

  M5.Display.fillScreen(BLACK);
  M5.Display.setTextColor(GREEN, BLACK);
  M5.Display.setCursor(8, 8);
  M5.Display.println("YON BULUCU");
  M5.Display.setTextSize(1);
  M5.Display.println("WiFi baglaniyor...");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
    M5.update();
    delay(100);
  }
  sonImuMs = millis();
  apiSor();  // ilk veri hemen gelsin
  sonPoll = millis();
}

void donguSes(float yawHata, float egimHata) {
  float ay = fabs(yawHata), ae = fabs(egimHata);
  bool simdiKilit = (ay < 4.0 && ae < 3.0 && veriVar);
  if (simdiKilit && !kilit) {  // kilit anı: yükselen 3 nota
    M5.Speaker.tone(660, 100);
    delay(130);
    M5.Speaker.tone(880, 100);
    delay(130);
    M5.Speaker.tone(1320, 200);
  }
  kilit = simdiKilit;
  if (kilit) return;

  // Bul uygulamasındaki gibi: yaklaştıkça sıklaşan + tizleşen bip.
  // Hangi eksen bozuksa onun perdesi duyulur: yaw = kalın, eğim = ince.
  bool yawBaskin = ay >= ae;
  float hata = yawBaskin ? ay : ae;
  unsigned long aralik = (unsigned long)(150 + min(hata, 90.0f) * 12);  // 150..1230 ms
  float oran = 1.0f - min(hata, 60.0f) / 60.0f;                          // 0 (uzak) .. 1 (yakın)
  int frekans = yawBaskin ? (500 + (int)(oran * 300))                    // 500..800 Hz
                          : (900 + (int)(oran * 500));                   // 900..1400 Hz
  static unsigned long sonBip = 0;
  if (millis() - sonBip > aralik) {
    sonBip = millis();
    M5.Speaker.tone(frekans, 70);
  }
}

void okCiz(int x, int y, float hata, bool yatay) {
  // Hata yönüne bakan küçük neon ok; hata ~0 ise gizlenir.
  if (fabs(hata) < 2.0) return;
  uint16_t renk = (fabs(hata) < 10.0) ? GREEN : YELLOW;
  if (yatay) {
    if (hata > 0) M5.Display.fillTriangle(x, y - 8, x, y + 8, x + 12, y, renk);  // sağa dön
    else M5.Display.fillTriangle(x, y - 8, x, y + 8, x - 12, y, renk);            // sola dön
  } else {
    if (hata > 0) M5.Display.fillTriangle(x - 8, y, x + 8, y, x, y - 12, renk);  // kaldır
    else M5.Display.fillTriangle(x - 8, y, x + 8, y, x, y + 12, renk);            // yatır
  }
}

void ekranCiz(float tilt, float yawHata, float egimHata) {
  M5.Display.fillScreen(BLACK);
  bool gunes = (mod == MOD_GUNES);
  M5.Display.setTextSize(2);
  M5.Display.setTextColor(gunes ? YELLOW : CYAN, BLACK);
  M5.Display.setCursor(6, 4);
  M5.Display.print(gunes ? "GUNES" : "RUZGAR");
  M5.Display.setTextSize(1);
  M5.Display.setTextColor(WHITE, BLACK);
  M5.Display.setCursor(150, 8);
  M5.Display.print(WiFi.status() == WL_CONNECTED ? (veriVar ? "cevrimici" : "veri yok") : "WiFi yok");

  M5.Display.setTextSize(2);
  if (kilit) {
    M5.Display.setTextColor(GREEN, BLACK);
    M5.Display.setCursor(60, 44);
    M5.Display.print("KILITLENDI");
  } else {
    M5.Display.setTextColor(WHITE, BLACK);
    M5.Display.setCursor(6, 36);
    M5.Display.printf("YAW %+5.0f", yawHata);
    M5.Display.setCursor(6, 62);
    M5.Display.printf("EGIM %+4.0f", egimHata);
    okCiz(200, 46, yawHata, true);
    okCiz(200, 96, egimHata, false);
  }

  M5.Display.setTextSize(1);
  M5.Display.setTextColor(DARKGREY, BLACK);
  M5.Display.setCursor(6, 112);
  if (gunes)
    M5.Display.printf("hedef: yon %.0f egim %.0f | simdi: %.0f/%.0f", hedefYaw, hedefEgim,
                      fmod(yaw + 360.0, 360.0), tilt);
  else
    M5.Display.printf("hedef: %.0f (%.1f m/s) | simdi: %.0f", hedefYaw, ruzgarHiz,
                      fmod(yaw + 360.0, 360.0));
  M5.Display.setCursor(6, 124);
  if (millis() - sesGosterMs < 1500) {
    if (kuzeyGoster)
      M5.Display.print("KUZEY SIFIRLANDI");
    else
      M5.Display.printf("SES:%s (B ile degisir)", SES_ADI[sesIdx]);
  } else
    M5.Display.print("A:mod B:ses (uzun bas:kuzey)");
}

void loop() {
  M5.update();

  if (M5.BtnA.wasPressed()) {  // mod değiştir + kulak ikonu
    mod = (mod == MOD_GUNES) ? MOD_RUZGAR : MOD_GUNES;
    hedefiUygula();
    kilit = false;
    if (mod == MOD_GUNES)
      M5.Speaker.tone(1200, 90);  // güneş: tek tiz bip
    else {                        // rüzgar: çift kalın bip
      M5.Speaker.tone(600, 90);
      delay(120);
      M5.Speaker.tone(600, 90);
    }
  }
  // BtnB kısa basış: ses DÜŞÜK -> ORTA -> YÜKSEK; uzun basış (1 sn): yaw sıfırla.
  if (M5.BtnB.pressedFor(1000) && !uzunB) {
    uzunB = true;
    yaw = 0.0;  // cihaz kuzeye bakarken basılı tutuluyor kabul edilir
    kuzeyGoster = true;
    sesGosterMs = millis();
    M5.Speaker.tone(1174, 120);
  }
  if (M5.BtnB.wasReleased()) {
    if (!uzunB) {
      sesIdx = (sesIdx + 1) % 3;
      M5.Speaker.setVolume(SESLER[sesIdx]);
      kuzeyGoster = false;
      sesGosterMs = millis();
      M5.Speaker.tone(880, 80);  // yeni düzeyi duyur
    }
    uzunB = false;
  }

  // IMU: eğim ivmeden, yaw gyro-z tümlevinden (kuzey referansı BtnB ile).
  float ax = 0, ay = 0, az = 1, gx = 0, gy = 0, gz = 0;
  unsigned long simdi = millis();
  float dt = (simdi - sonImuMs) / 1000.0;
  sonImuMs = simdi;
  M5.Imu.getAccel(&ax, &ay, &az);
  if (dt > 0 && dt < 1.0 && M5.Imu.getGyro(&gx, &gy, &gz)) yaw = fmod(yaw + gz * dt + 540.0, 360.0) - 180.0;
  float tilt = atan2f(sqrtf(ax * ax + ay * ay), fabsf(az)) * 57.2958;  // yatayla açı

  if (simdi - sonPoll > POLL_MS) {
    sonPoll = simdi;
    apiSor();
  }

  float yawHata = veriVar ? sar(hedefYaw - (fmod(yaw + 360.0, 360.0))) : 0;
  float egimHata = veriVar ? (hedefEgim - tilt) : 0;
  donguSes(yawHata, egimHata);
  ekranCiz(tilt, yawHata, egimHata);
  delay(50);
}
