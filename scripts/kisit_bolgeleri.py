"""KKTC kısıt bölgelerini OpenStreetMap'ten (Overpass) üretir.

Çıktılar
  assets/kisit_bolgeleri.geojson        harita katmanı (renk sınıfına göre birleştirilmiş)
  hibrit_enerji/data/kisit_kaynak.geojson  tıklama kontrolü (her alanın adı ve gerekçesi)

Harita sınıfları (kullanıcı kararı — UYGUNLUĞU gösterir)
  kirmizi : ikisine de uygun değil
  sari    : yalnızca GÜNEŞE uygun (rüzgâr kısıtlı)
  mavi    : yalnızca RÜZGÂRA uygun (güneş kısıtlı)

Kullanım:  .venv/bin/python scripts/kisit_bolgeleri.py
Mesafeler (havalimanı, yerleşim) yaklaşık planlama değerleridir; kesin sınır için
ilgili kurum izni gerekir. Veri: © OpenStreetMap katkıcıları (ODbL).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import httpx
from shapely.geometry import LineString, Point, Polygon, mapping
import numpy as np
import shapely
from shapely.ops import polygonize, unary_union

ROOT = Path(__file__).resolve().parents[1]
OUT_MAP = ROOT / "assets" / "kisit_bolgeleri.geojson"
OUT_SRC = ROOT / "hibrit_enerji" / "data" / "kisit_kaynak.geojson"
OVERPASS = "https://overpass-api.de/api/interpreter"
KKTC_REL = 2514541
AREA = 3600000000 + KKTC_REL
BUFFER_ZONE_REL = 3263909
ISLAND_REL = 3263732  # Kıbrıs adası (kara) — KKTC sınırı karasularını da içerir

AIRPORT_WIND_BUFFER_M = 5000
TOWN_WIND_BUFFER_M = 1500
VILLAGE_WIND_BUFFER_M = 500
RESIDENTIAL_WIND_BUFFER_M = 300
MIN_AREA_M2 = 2000
SIMPLIFY_M = 25

# Metre <-> derece (35° enlemde eşdikdörtgen yaklaşım; ada ölçeğinde yeterli)
K_LAT = 110_574.0
K_LON = 111_320.0 * math.cos(math.radians(35.2))
_TO_M = np.array([K_LON, K_LAT])
to_m = lambda g: shapely.transform(g, lambda c: c * _TO_M)  # noqa: E731
to_deg = lambda g: shapely.transform(g, lambda c: c / _TO_M)  # noqa: E731


def overpass(q: str) -> list[dict]:
    for attempt in range(5):
        r = httpx.post(OVERPASS, data={"data": q}, timeout=300,
                       headers={"User-Agent": "kktc-hibrit-enerji/0.1 (hackathon)"})
        if r.status_code == 200:
            return r.json()["elements"]
        print(f"  Overpass {r.status_code}, tekrar deneniyor…", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    r.raise_for_status()
    return []


def _ring(geom: list[dict]) -> list[tuple[float, float]]:
    return [(p["lon"], p["lat"]) for p in geom]


def element_geometry(e: dict):
    """Overpass 'out geom' öğesini shapely alanına çevir (alan değilse None)."""
    if e["type"] == "way":
        pts = _ring(e.get("geometry", []))
        if len(pts) >= 4 and pts[0] == pts[-1]:
            g = Polygon(pts)
            return g if g.is_valid else g.buffer(0)
        return None
    if e["type"] == "relation":
        outer, inner = [], []
        for m in e.get("members", []):
            if m.get("type") != "way" or "geometry" not in m:
                continue
            ls = LineString(_ring(m["geometry"]))
            (inner if m.get("role") == "inner" else outer).append(ls)
        if not outer:
            return None
        o = unary_union(list(polygonize(unary_union(outer))))
        if inner:
            o = o.difference(unary_union(list(polygonize(unary_union(inner)))))
        return o if not o.is_empty else None
    return None


def fetch_layer(selector: str) -> list[tuple[object, str]]:
    q = f"[out:json][timeout:240];area({AREA})->.k;({selector});out geom;"
    out = []
    for e in overpass(q):
        g = element_geometry(e)
        if g is None:
            continue
        t = e.get("tags", {})
        out.append((g, t.get("name:tr") or t.get("name") or t.get("name:en") or ""))
    return out


def main() -> None:
    print("KKTC sınırı…")
    kktc = element_geometry(overpass(f"[out:json][timeout:240];rel({KKTC_REL});out geom;")[0])
    print("Kıbrıs adası (kara)…")
    island = element_geometry(overpass(f"[out:json][timeout:240];rel({ISLAND_REL});out geom;")[0])
    kktc_m = to_m(kktc).intersection(to_m(island).buffer(0))  # yalnızca kara

    src: list[dict] = []  # tıklama kontrolü için kaynak alanlar

    def add(geom_deg, raw_cls: str, reason: str, name: str):
        g = to_m(geom_deg).intersection(kktc_m)
        if g.is_empty or g.area < MIN_AREA_M2:
            return
        g = g.simplify(SIMPLIFY_M, preserve_topology=True)
        src.append({"geom_m": g, "cls": raw_cls, "reason": reason, "name": name})

    print("BM Ara Bölgesi…")
    bz = element_geometry(overpass(f"[out:json][timeout:240];rel({BUFFER_ZONE_REL});out geom;")[0])
    if bz is not None:
        # Ara bölge KKTC sınırının dışında kalır; sınırın 3 km yakınındaki kısmı gösterilir
        g = to_m(bz).intersection(kktc_m.buffer(3000))
        if not g.is_empty:
            src.append({"geom_m": g.simplify(SIMPLIFY_M), "cls": "ikisi",
                        "reason": "BM Ara Bölgesi (Yeşil Hat): yapılaşma yasak", "name": "Ara Bölge"})

    print("Askerî alanlar…")
    for g, n in fetch_layer('way["landuse"="military"](area.k);rel["landuse"="military"](area.k);'):
        add(g, "ikisi", "Askerî alan: kurulum yasak", n)

    print("Korunan alanlar…")
    for g, n in fetch_layer('way["boundary"~"protected_area|national_park"](area.k);'
                            'rel["boundary"~"protected_area|national_park"](area.k);'
                            'way["leisure"="nature_reserve"](area.k);rel["leisure"="nature_reserve"](area.k);'):
        add(g, "ikisi", "Korunan alan / milli park / özel çevre koruma", n)

    print("Havalimanları…")
    for g, n in fetch_layer('way["aeroway"="aerodrome"](area.k);rel["aeroway"="aerodrome"](area.k);'):
        add(g, "ikisi", "Havalimanı alanı", n)
        ring = to_deg(to_m(g).buffer(AIRPORT_WIND_BUFFER_M))
        add(ring, "ruzgar", f"Havalimanı çevresi ~{AIRPORT_WIND_BUFFER_M // 1000} km: türbin yüksekliği uçuş "
                            "güvenliği ve radar için kısıtlı (güneş paneli olabilir)", n)

    print("Yerleşimler…")
    places = overpass(f'[out:json][timeout:240];area({AREA})->.k;node["place"~"city|town|village"](area.k);out;')
    town_buf, village_buf = [], []
    for p in places:
        pt = to_m(Point(p["lon"], p["lat"]))
        if p.get("tags", {}).get("place") in ("city", "town"):
            town_buf.append(pt.buffer(TOWN_WIND_BUFFER_M))
        else:
            village_buf.append(pt.buffer(VILLAGE_WIND_BUFFER_M))
    for bufs, label in ((town_buf, f"Şehir/kasaba çevresi ~{TOWN_WIND_BUFFER_M / 1000:g} km"),
                        (village_buf, f"Köy çevresi ~{VILLAGE_WIND_BUFFER_M} m")):
        if bufs:
            add(to_deg(unary_union(bufs)), "ruzgar",
                f"{label}: türbin gürültüsü ve gölge titreşimi mesafesi (çatı GES olabilir)", "Yerleşim")

    print("Konut alanları…")
    res = [to_m(g).buffer(RESIDENTIAL_WIND_BUFFER_M) for g, _ in
           fetch_layer('way["landuse"="residential"](area.k);rel["landuse"="residential"](area.k);')]
    if res:
        add(to_deg(unary_union(res)), "ruzgar",
            f"Konut alanı ve ~{RESIDENTIAL_WIND_BUFFER_M} m çevresi: türbin gürültüsü ve gölge titreşimi "
            "(çatı GES olabilir)", "Yerleşim")

    print("Su yüzeyleri…")
    for g, n in fetch_layer('way["natural"="water"](area.k);rel["natural"="water"](area.k);'):
        add(g, "ruzgar", "Göl / baraj yüzeyi: türbin kurulamaz; yüzer GES olabilir", n)

    print("Orman alanları…")
    for g, n in fetch_layer('way["landuse"="forest"](area.k);rel["landuse"="forest"](area.k);'
                            'way["natural"="wood"](area.k);rel["natural"="wood"](area.k);'):
        add(g, "gunes", "Orman: ağaç kesimi ve gölge nedeniyle GES uygun değil "
                        "(rüzgâr için orman izni gerekir)", n)

    # ---- renk sınıfları
    both = unary_union([s["geom_m"] for s in src if s["cls"] == "ikisi"])
    wind = unary_union([s["geom_m"] for s in src if s["cls"] == "ruzgar"])
    solar = unary_union([s["geom_m"] for s in src if s["cls"] == "gunes"])
    red = unary_union([both, wind.intersection(solar)])
    yellow = wind.difference(red)   # rüzgâr kısıtlı -> yalnızca güneşe uygun
    blue = solar.difference(red)    # güneş kısıtlı  -> yalnızca rüzgâra uygun

    def feat(g_m, props):
        g = to_deg(g_m.simplify(SIMPLIFY_M, preserve_topology=True))
        return {"type": "Feature", "properties": props, "geometry": mapping(g)}

    OUT_MAP.write_text(json.dumps({"type": "FeatureCollection", "features": [
        feat(red, {"cls": "kirmizi", "label": "İkisine de uygun değil"}),
        feat(yellow, {"cls": "sari", "label": "Yalnızca güneşe uygun"}),
        feat(blue, {"cls": "mavi", "label": "Yalnızca rüzgâra uygun"}),
        feat(kktc_m.boundary, {"cls": "sinir", "label": "KKTC sınırı"}),
    ], "attribution": "© OpenStreetMap katkıcıları (ODbL)"}, ensure_ascii=False))

    OUT_SRC.parent.mkdir(exist_ok=True)
    OUT_SRC.write_text(json.dumps({"type": "FeatureCollection", "features": [
        feat(s["geom_m"], {"cls": s["cls"], "reason": s["reason"], "name": s["name"]}) for s in src
    ]}, ensure_ascii=False))

    km2 = lambda g: g.area / 1e6  # noqa: E731
    print(f"KKTC alanı {km2(kktc_m):,.0f} km² · kırmızı {km2(red.intersection(kktc_m)):,.0f} km² · "
          f"sarı (yalnız güneş) {km2(yellow):,.0f} km² · mavi (yalnız rüzgâr) {km2(blue):,.0f} km² · kaynak alan sayısı {len(src)}")
    print(f"→ {OUT_MAP.relative_to(ROOT)} ({OUT_MAP.stat().st_size / 1024:,.0f} KB)")
    print(f"→ {OUT_SRC.relative_to(ROOT)} ({OUT_SRC.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
