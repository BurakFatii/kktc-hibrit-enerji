"""Enerji yönetim sistemi (EMS): saatlik enerji dağıtımı.

Stratejiler
-----------
"yok"   : Batarya yok. Fazla -> şebeke (limit dahilinde) -> kısıtlama.
"basit" : Klasik kural. Fazla önce bataryaya, sonra şebekeye, sonra kısıtlama.
"akilli": Tahmine dayalı. Önümüzdeki 24 saatin üretim fazlasına bakar:
          batarya gün içinde zaten dolacaksa, önce şebeke limitini kullanır,
          bataryaya yalnızca limitin ÜSTÜNDEKİ fazlayı (ve gerekiyorsa bir pay)
          yükler. Böylece öğlen 'batarya dolu + limit dolu' anında enerji
          kısılmaz; batarya akşama yine dolu girer.

Şebekeye verme hedeflerden biridir; yalnızca export_limit_kw ile sınırlanır.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .spec import SystemSpec

EV_POWER_KW = 7.0


@dataclass
class EmsResult:
    prod: np.ndarray
    load: np.ndarray
    soc_kwh: np.ndarray        # Saat SONUNDA kullanılabilir batarya enerjisi
    charge: np.ndarray         # Bataryaya giren (kW, üretimden)
    discharge: np.ndarray      # Bataryadan yüke giden (kW)
    export: np.ndarray
    grid_import: np.ndarray
    curtail: np.ndarray
    ev_charge: np.ndarray
    ev_discharge: np.ndarray
    usable_kwh: float
    strategy: str
    modes: list[str] = field(default_factory=list)

    def soc_pct(self) -> np.ndarray:
        if self.usable_kwh <= 0:
            return np.zeros_like(self.soc_kwh)
        return self.soc_kwh / self.usable_kwh * 100


def _window_sums(surplus: np.ndarray, limit, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """Her saat için, içinde bulunulan FAZLA DÖNEMİNİN sonuna kadar (en çok horizon saat)
    limit üstü / limit altı fazla toplamları. Batarya, açık başlamadan dolmalı;
    ertesi günün fazlası bugünün akşamını kurtarmaz."""
    s = np.clip(surplus, 0, None)
    above = np.clip(s - limit, 0, None)
    below = np.minimum(s, limit)
    ca = np.concatenate([[0.0], np.cumsum(above)])
    cb = np.concatenate([[0.0], np.cumsum(below)])
    n = len(s)
    # run_end[t] = t'den sonra fazlanın ilk bittiği indeks
    run_end = np.empty(n, dtype=int)
    nxt = n
    for t in range(n - 1, -1, -1):
        if surplus[t] < 0:
            nxt = t
        run_end[t] = nxt
    idx = np.arange(n)
    end = np.minimum(run_end, idx + horizon)
    return ca[end] - ca[idx], cb[end] - cb[idx]


def simulate(prod: np.ndarray, load: np.ndarray, spec: SystemSpec, strategy: str = "akilli",
             soc0_frac: float = 0.5, horizon: int = 24, ev_connected: bool = False,
             ev_soc0_frac: float = 0.8, with_modes: bool = False,
             export_limit: np.ndarray | None = None) -> EmsResult:
    """export_limit: saatlik şebekeye verme sınırı (kW). Verilmezse spec.export_limit_kw (sabit)."""
    n = len(prod)
    usable = spec.battery_usable_kwh if strategy != "yok" else 0.0
    eff = float(np.sqrt(max(min(spec.battery_rt_eff_pct, 100.0), 1.0) / 100.0))
    pmax = max(spec.battery_power_kw, 0.0)
    limit_arr = (np.clip(np.asarray(export_limit, dtype=float), 0, None) if export_limit is not None
                 else np.full(n, max(spec.export_limit_kw, 0.0)))

    ev_on = ev_connected and spec.ev_enabled and spec.ev_kwh > 0
    ev_cap = spec.ev_kwh if ev_on else 0.0
    ev_floor = ev_cap * spec.ev_reserve_pct / 100.0
    ev_soc = ev_cap * ev_soc0_frac

    surplus = prod - load
    if strategy == "akilli":
        win_above, win_below = _window_sums(surplus, limit_arr, horizon)

    arrays = {k: np.zeros(n) for k in
              ("soc", "chg", "dis", "exp", "imp", "cur", "evc", "evd")}
    soc = usable * soc0_frac
    modes: list[str] = []

    for t in range(n):
        s = surplus[t]
        limit = limit_arr[t]
        chg = dis = exp = imp = cur = evc = evd = 0.0
        if s >= 0:
            room_in = (usable - soc) / eff if usable > 0 else 0.0
            if strategy == "akilli" and usable > 0:
                need = room_in * 1.10  # tahmin hatasına karşı %10 pay
                if win_above[t] >= need:
                    want = max(s - limit, 0.0)
                else:
                    share = (need - win_above[t]) / win_below[t] if win_below[t] > 0 else 1.0
                    want = max(s - limit, 0.0) + min(1.0, share) * min(s, limit)
            else:
                want = s
            chg = min(want, pmax, room_in)
            rest = s - chg
            exp = min(rest, limit)
            rest -= exp
            extra = min(rest, max(pmax - chg, 0.0), max(room_in - chg, 0.0))
            chg += extra
            rest -= extra
            if ev_on and rest > 0:
                evc = min(rest, EV_POWER_KW, (ev_cap - ev_soc) / eff)
                ev_soc += evc * eff
                rest -= evc
            cur = max(rest, 0.0)
            soc += chg * eff
        else:
            deficit = -s
            if usable > 0:
                dis = min(deficit, pmax, soc * eff)
                soc -= dis / eff
                deficit -= dis
            if ev_on and spec.ev_v2h and deficit > 0:
                evd = min(deficit, EV_POWER_KW, max(ev_soc - ev_floor, 0.0) * eff)
                ev_soc -= evd / eff
                deficit -= evd
            imp = deficit
        soc = min(max(soc, 0.0), usable)
        for k, v in (("soc", soc), ("chg", chg), ("dis", dis), ("exp", exp), ("imp", imp),
                     ("cur", cur), ("evc", evc), ("evd", evd)):
            arrays[k][t] = v
        if with_modes:
            modes.append(mode_key(chg, dis, exp, imp, cur, evc, evd))

    return EmsResult(prod=prod, load=load, soc_kwh=arrays["soc"], charge=arrays["chg"],
                     discharge=arrays["dis"], export=arrays["exp"], grid_import=arrays["imp"],
                     curtail=arrays["cur"], ev_charge=arrays["evc"], ev_discharge=arrays["evd"],
                     usable_kwh=usable, strategy=strategy, modes=modes)


MODES = {
    "sarj": ("BATARYAYI ŞARJ ET", "Üretim tüketimden fazla; fazlalık bataryada saklanıyor."),
    "sarj_ver": ("BATARYA + ŞEBEKE", "Fazla üretim bataryaya ve şebekeye paylaştırılıyor; "
                 "batarya akşama dolu girecek şekilde planlandı."),
    "ver": ("ŞEBEKEYE VER", "Batarya ihtiyacı karşılandı; fazlalık izin verilen limit içinde şebekeye veriliyor."),
    "ev_sarj": ("ARACI ŞARJ ET", "Batarya dolu; fazlalık elektrikli araca aktarılıyor."),
    "kisit": ("ÜRETİMİ KISITLA", "Batarya dolu ve şebeke limiti dolu; fazla üretim kısılıyor."),
    "besle": ("BATARYADAN BESLE", "Üretim yetersiz; tesis bataryadan besleniyor."),
    "v2h": ("ARAÇTAN BESLE (V2H)", "Batarya yetersiz; elektrikli aracın yedek dışı enerjisi kullanılıyor."),
    "cek": ("ŞEBEKEDEN ÇEK", "Üretim ve depo yetersiz; açık şebekeden karşılanıyor."),
    "denge": ("DENGEDE", "Üretim tüketimi tam karşılıyor."),
}


def mode_key(chg, dis, exp, imp, cur, evc, evd, eps: float = 0.02) -> str:
    if cur > eps:
        return "kisit"
    if imp > eps:
        return "cek"
    if evd > eps:
        return "v2h"
    if dis > eps:
        return "besle"
    if chg > eps and exp > eps:
        return "sarj_ver"
    if chg > eps:
        return "sarj"
    if evc > eps:
        return "ev_sarj"
    if exp > eps:
        return "ver"
    return "denge"
