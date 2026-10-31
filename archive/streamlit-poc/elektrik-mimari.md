# Elektrik mimarisi (şematik, teknik olarak mümkün)

Hedef: hane + orta ölçek tüketici. Öncelik depolama, şebeke desteği opsiyonel
(KKTC geri-besleme mevzuatı belirsiz olduğu için varsayılan: sıfır/sınırlı ihracat).

```
[PV + Çift-eksen Takipçi] --DC--> [Hibrit İnverter] --AC--> [Ev Panosu] --> [Yükler]
       (MPPT dahili)          ^  (ATS + anti-islanding)         |
                              |                                +--> [Akıllı Sayaç]
[Rüzgar Türbini] --AC/DC--> [Şarj Kontrolcüsü] --DC--> [DC Bara] |
                                                        |
                                              [LiFePO4 + BMS] (ev bataryası)
                                                        |
[EV (V2H)] < --AC çift yönlü--> [V2H Şarj İstasyonu] <---> [Ev Panosu]
```

Modüller (basit isimler):
1. PV panel + çift-eksen takipçi + MPPT
2. Mikro rüzgar türbini (3 m/s cut-in) + şarj kontrolcüsü
3. Hibrit inverter (şebeke + ada modu, ATS)
4. LiFePO4 ev bataryası + BMS
5. Çift yönlü EV şarj istasyonu (V2H) + EV bataryası
6. Akıllı sayaç + EMS yazılımı (ileride Rust)

Neden mümkün: hibrit inverter DC barada PV, rüzgar ve bataryayı birleştirir;
ATS kesintide evi adalar; BMS ve V2H şarj istasyonu EV'yi ikinci depo yapar.
Şebekeye satış kapalı tutulursa mevzuat riski doğmaz, destek modu sonra açılır.
