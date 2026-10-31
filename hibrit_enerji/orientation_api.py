"""Saha yönlendirme API'si: M5Stack StickS3 panel/türbin yön bulucu için anlık hedefler.

Kullanım (Reflex yerelde çalışırken ayrı uçta):
    .venv/bin/python -m hibrit_enerji.orientation_api --port 8001

StickS3 her ~5 sn'de bir sorar:
    GET /api/yonlendirme?lat=35.1856&lon=33.3823
    GET /api/saglik

Dönen hedefler:
- güneş: panel normali güneşe bakmalı -> yaw hedefi = güneş azimutu,
  pitch hedefi = güneş yüksekliği (90 - zenit). Gece ise "gece": true.
- rüzgâr: rotor rüzgâra dönmeli -> yaw hedefi = rüzgârın GELDİĞİ yön
  (hub yüksekliğine ara değerlenmiş), pitch hedefi = 0 (yatay).

Hesaplar core/ içinden gelir (pvlib NREL SPA + windpowerlib log ara değer);
burada yeni fizik formülü yoktur. Arayüz kuralı gereği model adı
yazılmaz, yalnızca "geçmiş yıl / tahmin" denir.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

from .core import meteo
from .core.config import FALLBACK_LOCATION
from .core.production import Orientation, compute
from .core.spec import SystemSpec


def build_guidance(w: meteo.Weather, lat: float, lon: float,
                   now_utc: dt.datetime | None = None) -> dict:
    """Anlık yönlendirme paketi (ağ gerektirmez; test edilebilir)."""
    i = meteo.current_index(w, now_utc)
    spec = SystemSpec()
    p = compute(w, spec, lat, lon,
                Orientation(tilt_deg=spec.fixed_tilt_deg, azimuth_deg=spec.fixed_azimuth_deg,
                            wind_facing_deg=spec.wind_fixed_dir_deg, source="varsayilan"))

    sun_az = float(p.sun_az[i] % 360)
    sun_zen = float(p.sun_zen[i])
    night = bool(sun_zen >= 90)
    solar_target = {"az_deg": round(sun_az, 1),
                    "egim_deg": round(max(90.0 - sun_zen, 0.0), 1),
                    "gece": night}
    wind_from = float(np.asarray(p.hub_wd)[i] % 360)
    wind_target = {"gelis_yonu_deg": round(wind_from, 1),
                   "govbek_hizi_ms": round(float(np.asarray(p.hub_ws)[i]), 1)}
    stamp = np.datetime_as_string(np.asarray(w.time)[i], unit="s")
    return {"konum": {"lat": lat, "lon": lon},
            "zaman_utc": str(stamp),
            "gunes": solar_target,
            "ruzgar": wind_target,
            "pusula": {"kuzey": 0, "not": "cihaz yaw referansi manyetik kuzey olmali"}}


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        url = urllib.parse.urlparse(self.path)
        if url.path == "/api/saglik":
            self._send(200, {"durum": "tamam"})
            return
        if url.path != "/api/yonlendirme":
            self._send(404, {"hata": "bilinmeyen adres"})
            return
        q = urllib.parse.parse_qs(url.query)
        try:
            lat = float(q.get("lat", [FALLBACK_LOCATION["lat"]])[0])
            lon = float(q.get("lon", [FALLBACK_LOCATION["lon"]])[0])
        except (TypeError, ValueError):
            self._send(400, {"hata": "lat/lon sayi olmali"})
            return
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            self._send(400, {"hata": "lat/lon aralik disi"})
            return
        try:
            w = meteo.fetch_forecast(lat, lon)
        except Exception as e:  # ağ yoksa StickS3'e anlaşılır hata
            self._send(502, {"hata": f"tahmin alinamadi: {e}"})
            return
        self._send(200, build_guidance(w, lat, lon))

    def log_message(self, *args: object) -> None:
        pass  # StickS3 yoklamaları konsolu kirletmesin


def serve(port: int = 8001) -> None:
    srv = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
    print(f"Yonlendirme API: http://localhost:{port}/api/yonlendirme?lat=..&lon=..")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description="StickS3 yönlendirme API'si")
    ap.add_argument("--port", type=int, default=8001)
    serve(ap.parse_args().port)


if __name__ == "__main__":
    main()
