"""Kısıt bölgeleri: bir nokta hangi enerji kaynağına uygun?

Veri: hibrit_enerji/data/kisit_kaynak.geojson (scripts/kisit_bolgeleri.py ile OSM'den üretilir).
Kaynak alan sınıfları: "ikisi" (ikisine de kısıt), "ruzgar" (rüzgâra kısıt), "gunes" (güneşe kısıt).

Harita renkleri (kullanıcı kararı — UYGUNLUĞU gösterir):
  kirmizi : ikisine de uygun değil
  sari    : yalnızca GÜNEŞE uygun (rüzgâr kısıtlı)
  mavi    : yalnızca RÜZGÂRA uygun (güneş kısıtlı)
  uygun   : bilinen kısıt yok, ikisine de uygun
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shapely import STRtree
from shapely.geometry import Point, shape

DATA = Path(__file__).resolve().parents[1] / "data" / "kisit_kaynak.geojson"

# Renkler tema değişkenlerinden (assets/theme.css): açık temada koyu, koyu temada parlak ton
COLOR = {"kirmizi": "var(--zone-red)", "sari": "var(--zone-yellow)", "mavi": "var(--zone-blue)",
         "uygun": "var(--neon)"}
LABEL = {"kirmizi": "İkisine de uygun değil", "sari": "Yalnızca güneşe uygun",
         "mavi": "Yalnızca rüzgâra uygun", "uygun": "Güneşe ve rüzgâra uygun"}

# Kısa kodlar: A = ikisi, R = rüzgâr, G = güneş. (gerekçe metninin başı -> kod, sade açıklama)
CODES = [
    ("BM Ara Bölgesi", "A01", "BM ara bölgesi"),
    ("Askerî alan", "A02", "Askerî alan"),
    ("Korunan alan", "A03", "Koruma alanı"),
    ("Havalimanı alanı", "A04", "Havalimanı"),
    ("Havalimanı çevresi", "R01", "Havalimanına yakın"),
    ("Şehir/kasaba çevresi", "R02", "Yerleşime yakın"),
    ("Köy çevresi", "R02", "Yerleşime yakın"),
    ("Konut alanı", "R02", "Yerleşime yakın"),
    ("Göl / baraj", "R03", "Su yüzeyi"),
    ("Orman", "G01", "Orman alanı"),
]


def _code(reason: str) -> tuple[str, str]:
    for prefix, code, short in CODES:
        if reason.startswith(prefix):
            return code, short
    return "X00", reason.split(":")[0]


@lru_cache(maxsize=1)
def _index():
    if not DATA.exists():
        return None, []
    feats = json.loads(DATA.read_text())["features"]
    geoms = [shape(f["geometry"]) for f in feats]
    return STRtree(geoms), [(g, f["properties"]) for g, f in zip(geoms, feats)]


def check(lat: float, lon: float) -> dict:
    """{'cls', 'label', 'wind_ok', 'solar_ok', 'codes': [{'code','short','name','detail'}], 'reasons': [...]}"""
    tree, items = _index()
    pt = Point(lon, lat)
    hits = []
    if tree is not None:
        for i in tree.query(pt):
            g, props = items[int(i)]
            if g.contains(pt):
                hits.append(props)
    wind_ok = not any(h["cls"] in ("ikisi", "ruzgar") for h in hits)
    solar_ok = not any(h["cls"] in ("ikisi", "gunes") for h in hits)
    if not wind_ok and not solar_ok:
        cls = "kirmizi"
    elif not wind_ok:
        cls = "sari"
    elif not solar_ok:
        cls = "mavi"
    else:
        cls = "uygun"
    codes, seen = [], set()
    for h in sorted(hits, key=lambda h: _code(h["reason"])[0]):
        code, short = _code(h["reason"])
        name = h.get("name") if h.get("name") and h["name"] != "Yerleşim" else ""
        key = (code, name)
        if key in seen:
            continue
        seen.add(key)
        codes.append({"code": code, "short": short, "name": name, "detail": h["reason"]})
    return {"cls": cls, "label": LABEL[cls], "wind_ok": wind_ok, "solar_ok": solar_ok, "codes": codes,
            "reasons": [c["detail"] + (f" — {c['name']}" if c["name"] else "") for c in codes]}
