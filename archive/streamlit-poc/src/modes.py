"""Çalışma modu önerisi. Öncelik: depola -> tüket -> (opsiyonel) şebekeyi destekle."""
from __future__ import annotations


def suggest_mode(total_kw: float, consumption_kw: float,
                 soc_pct: float, ev_connected: bool = False) -> tuple[str, str]:
    """(mod, açıklama) döndürür."""
    surplus = total_kw - consumption_kw
    if surplus >= 0:
        if soc_pct < 95:
            return ("DEPOLA", "Üretim fazla: önce ev bataryasını doldur.")
        if ev_connected:
            return ("EV'İ ŞARJ ET", "Batarya dolu: fazlayı elektrikli araca aktar.")
        return ("ŞEBEKEYİ DESTEKLE (OPSİYONEL)",
                "Depolar dolu: KKTC mevzuatı netleşene kadar sınırlı/sıfır geri besleme.")
    # açık var
    if soc_pct > 20:
        return ("BATARYADAN BESLE", "Üretim düşük: evi bataryadan besle, şebekeyi beklet.")
    if ev_connected:
        return ("EV DESTEĞİ (V2H)", "Batarya kritik: EV bataryasından eve destek al.")
    return ("ŞEBEKEDEN ÇEK", "Üretim + depo yetersiz: şebekeden minimum çek.")
