"""KKTC ilçe sınırlarını OpenStreetMap'ten indirir -> hibrit_enerji/data/ilceler.geojson

Lefke ilçesi 2016'da Güzelyurt'tan ayrıldı; 2011 sayımı nüfusu birleşik olduğu için
iki ilçe "Güzelyurt (Lefke dahil)" olarak birleştirilir.
Kullanım:  .venv/bin/python scripts/ilceler.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import mapping
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kisit_bolgeleri import (AREA, ISLAND_REL, element_geometry, overpass, to_deg,  # noqa: E402
                             to_m)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "hibrit_enerji" / "data" / "ilceler.geojson"
MERGE = {"Lefke": "Güzelyurt"}


def main() -> None:
    island = to_m(element_geometry(overpass(f"[out:json][timeout:240];rel({ISLAND_REL});out geom;")[0])).buffer(0)
    els = overpass(f'[out:json][timeout:240];area({AREA})->.k;'
                   f'rel["boundary"="administrative"]["admin_level"="5"](area.k);out geom;')
    parts: dict[str, list] = {}
    for e in els:
        name = (e.get("tags", {}).get("name:tr") or e["tags"].get("name", "")).replace(" ilçesi", "").strip()
        g = element_geometry(e)
        if not name or g is None:
            continue
        name = MERGE.get(name, name)
        parts.setdefault(name, []).append(to_m(g).intersection(island))
    feats = []
    for name, gs in parts.items():
        g = unary_union(gs).simplify(30, preserve_topology=True)
        label = "Güzelyurt (Lefke dahil)" if name == "Güzelyurt" else name
        feats.append({"type": "Feature", "properties": {"ilce": name, "label": label},
                      "geometry": mapping(to_deg(g))})
        print(f"{label}: {g.area / 1e6:,.0f} km²")
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats,
                               "attribution": "© OpenStreetMap katkıcıları (ODbL)"}, ensure_ascii=False))
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:,.0f} KB)")


if __name__ == "__main__":
    main()
