"""OpenLayers haritası (OSM altlık) — Reflex bileşeni.

- `markers`: [{"center": [lat, lon], "name": str, "color": "#hex", "radius": int}]
- `on_pick(lat, lng)`: haritaya tıklanan noktanın koordinatı
- `solar` / `show_solar`: yıllık ışınım ızgarası (core/fields.solar_field) -> yumuşak ısı haritası
- Sağ üstte pusula kontrolü (ol/control.Control): K/D/G/B; harita döndürülünce döner, tıklayınca kuzeye hizalar.
- `wind` / `show_wind`: şu anki rüzgâr u/v ızgarası (core/fields.wind_field) -> parçacık akımı

OpenLayers `window` gerektirdiği için modüller useEffect içinde dinamik import
edilir; sunucu tarafı ön-render bozulmaz.
"""
from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.utils.imports import ImportVar

OL = "ol@10.4.0"


class OlMap(rx.Component):
    tag = "OlMap"
    lib_dependencies: list[str] = [OL]

    markers: rx.Var[list[dict[str, Any]]]
    center: rx.Var[list[float]]
    zoom: rx.Var[float]
    map_height: rx.Var[str]
    tile_style: rx.Var[str]  # "light" | "dark"
    zones_url: rx.Var[str]   # kısıt bölgeleri GeoJSON (assets)
    show_zones: rx.Var[bool]
    solar: rx.Var[dict[str, Any]]
    show_solar: rx.Var[bool]
    wind: rx.Var[dict[str, Any]]
    show_wind: rx.Var[bool]
    on_pick: rx.EventHandler[lambda lat, lng: [lat, lng]]

    def add_imports(self):
        return {
            "react": [ImportVar(tag="useRef"), ImportVar(tag="useEffect"),
                      ImportVar(tag="createElement")],
            "": ["ol/ol.css"],
        }

    def add_custom_code(self) -> list[str]:
        return ["""

// [açık tema, koyu tema] — açıkta koyu ton, koyuda parlak ton
const ZONE_STYLE = {
  kirmizi: [['rgba(217,45,32,0.28)', '#d92d20'], ['rgba(255,77,64,0.30)', '#ff4d40']],
  sari: [['rgba(201,151,0,0.30)', '#c99700'], ['rgba(255,214,10,0.30)', '#ffd60a']],
  mavi: [['rgba(29,95,209,0.26)', '#1d5fd1'], ['rgba(77,155,255,0.30)', '#4d9bff']],
};

// Işınım ısı haritası rengi: sarı (düşük) -> turuncu (yüksek); t: 0..1
const sunColor = (t) => `hsla(${52 - 24 * t}, 100%, 50%, ${0.22 + 0.5 * t})`;

// Izgara noktalarını (kara) ince bir rastere bilineer aradeğerle; noktası olmayan hücre şeffaf.
function solarImage(field, k) {
  const {lat0, lon0, step, nlat, nlon, min, max} = field;
  const g = Array.from({length: nlat}, () => new Array(nlon).fill(null));
  field.points.forEach(([la, lo, v]) => {
    const i = Math.round((la - lat0) / step), j = Math.round((lo - lon0) / step);
    if (i >= 0 && i < nlat && j >= 0 && j < nlon) g[i][j] = v;
  });
  const W = (nlon - 1) * k + 1, H = (nlat - 1) * k + 1;
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
  const cx = cv.getContext('2d');
  const span = Math.max(max - min, 1e-9);
  for (let y = 0; y < H; y++) {
    const fi = (H - 1 - y) / k, i0 = Math.floor(fi), i1 = Math.min(i0 + 1, nlat - 1), di = fi - i0;
    for (let x = 0; x < W; x++) {
      const fj = x / k, j0 = Math.floor(fj), j1 = Math.min(j0 + 1, nlon - 1), dj = fj - j0;
      let s = 0, w = 0;
      [[i0, j0, (1 - di) * (1 - dj)], [i0, j1, (1 - di) * dj], [i1, j0, di * (1 - dj)], [i1, j1, di * dj]]
        .forEach(([a, b, ww]) => { const v = g[a][b]; if (v !== null && ww > 0) { s += v * ww; w += ww; } });
      if (w === 0) {  // komşu kara noktası yok: en yakın değerle doldur (sınırla kırpılacak)
        let best = null, bd = 1e9;
        field.points.forEach(([la, lo, v]) => { const d = (la - lat0 - fi * step) ** 2 + (lo - lon0 - fj * step) ** 2;
                                               if (d < bd) { bd = d; best = v; } });
        s = best; w = 1;
      }
      cx.fillStyle = sunColor((s / w - min) / span);
      cx.fillRect(x, y, 1, 1);
    }
  }
  // KKTC kara sınırıyla kırp (Yeşil Hat ve kıyı dışına taşmasın)
  if (field.clip && field.clip.length) {
    cx.globalCompositeOperation = 'destination-in';
    cx.beginPath();
    field.clip.forEach((ring) => ring.forEach(([lo, la], n) => {
      const x = (lo - lon0) / step * k, y = H - 1 - (la - lat0) / step * k;
      n ? cx.lineTo(x, y) : cx.moveTo(x, y);
    }));
    cx.fillStyle = '#000';
    cx.fill();
  }
  return cv.toDataURL();
}

// Bilineer u/v örnekleme (lat, lon derece). Izgara dışında null.
function sampleWind(f, lat, lon) {
  const {lats, lons, u, v} = f;
  const st = lats[1] - lats[0], sl = lons[1] - lons[0];
  const fi = (lat - lats[0]) / st, fj = (lon - lons[0]) / sl;
  if (fi < 0 || fj < 0 || fi > lats.length - 1 || fj > lons.length - 1) return null;
  const i0 = Math.floor(fi), j0 = Math.floor(fj);
  const i1 = Math.min(i0 + 1, lats.length - 1), j1 = Math.min(j0 + 1, lons.length - 1);
  const di = fi - i0, dj = fj - j0;
  const lerp = (m) => (m[i0][j0] * (1 - dj) + m[i0][j1] * dj) * (1 - di) + (m[i1][j0] * (1 - dj) + m[i1][j1] * dj) * di;
  return [lerp(u), lerp(v)];
}

// Pusula: OpenLayers kontrolü olarak (zoom düğmeleri gibi haritanın parçası). Harfler Türkçe yönler.
const COMPASS_SVG = `
<svg viewBox="-30 -30 60 60" width="56" height="56" aria-hidden="true">
  <circle r="27" class="cmp-ring"/>
  <path d="M0,-17 L4,0 L0,3 L-4,0 Z" class="cmp-north"/>
  <path d="M0,17 L4,0 L0,-3 L-4,0 Z" class="cmp-south"/>
  <text y="-19" class="cmp-k">K</text><text x="21" y="1" class="cmp-l">D</text>
  <text y="23" class="cmp-l">G</text><text x="-21" y="1" class="cmp-l">B</text>
</svg>`;

function compassControl(Control, view) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.title = 'Pusula: K kuzey, D doğu, G güney, B batı. Tıklayınca kuzeye hizalar.';
  btn.setAttribute('aria-label', 'Pusula, kuzeye hizala');
  btn.innerHTML = COMPASS_SVG;
  const el = document.createElement('div');
  el.className = 'map-compass ol-unselectable ol-control';
  el.appendChild(btn);
  const svgEl = btn.querySelector('svg');
  const sync = () => { svgEl.style.transform = `rotate(${view.getRotation()}rad)`; };
  view.on('change:rotation', sync);
  btn.addEventListener('click', () => view.animate({rotation: 0, duration: 300}));
  sync();
  return new Control({element: el});
}

const R_EARTH = 6378137;
const toLL = (x, y) => [x / R_EARTH * 180 / Math.PI, (2 * Math.atan(Math.exp(y / R_EARTH)) - Math.PI / 2) * 180 / Math.PI];
const fromLL = (lon, lat) => [lon * Math.PI / 180 * R_EARTH, Math.log(Math.tan(Math.PI / 4 + lat * Math.PI / 360)) * R_EARTH];

function OlMap({markers, center, zoom, mapHeight, tileStyle, zonesUrl, showZones, solar, showSolar, wind,
                showWind, onPick, className}) {
  const el = useRef(null);
  const ctx = useRef(null);       // {map, source, ol}
  const cb = useRef(onPick);
  cb.current = onPick;
  const latest = useRef(markers);
  latest.current = markers;
  const windRef = useRef(null);   // {field, on, raf, parts}
  if (!windRef.current) windRef.current = {field: null, on: false, raf: 0, parts: []};
  windRef.current.field = wind && wind.lats ? wind : null;
  windRef.current.on = !!showWind;

  // ---------------------------------------------------------------- rüzgâr akımı (canvas)
  const windColor = () => (getComputedStyle(el.current || document.body).getPropertyValue('--zone-blue') || '#4d9bff').trim();
  const stopWind = () => {
    const w = windRef.current, c = ctx.current;
    if (w.raf) cancelAnimationFrame(w.raf);
    w.raf = 0;
    if (c && c.canvas) c.canvas.getContext('2d').clearRect(0, 0, c.canvas.width, c.canvas.height);
  };
  const startWind = () => {
    const w = windRef.current, c = ctx.current;
    stopWind();
    if (!c || !w.on || !w.field) return;
    const cv = c.canvas, map = c.map, f = w.field;
    const size = map.getSize() || [cv.clientWidth, cv.clientHeight];
    const dpr = window.devicePixelRatio || 1;
    cv.width = size[0] * dpr; cv.height = size[1] * dpr;
    const g = cv.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    const color = windColor();
    const [x0, y0] = fromLL(f.lons[0], f.lats[0]);
    const [x1, y1] = fromLL(f.lons[f.lons.length - 1], f.lats[f.lats.length - 1]);
    const spawn = (p) => { p.x = x0 + Math.random() * (x1 - x0); p.y = y0 + Math.random() * (y1 - y0);
                           p.age = Math.floor(Math.random() * 80); return p; };
    const N = Math.round(Math.min(1800, Math.max(500, size[0] * size[1] / 260)));
    w.parts = Array.from({length: N}, () => spawn({}));
    const view = map.getView();
    const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    // Harita koordinatı -> ekran pikseli (OL dönüşümüyle aynı: merkez, çözünürlük, dönüş)
    const px = (x, y, cxy, res, rot) => {
      const vx = x - cxy[0], vy = y - cxy[1], c = Math.cos(rot), s = Math.sin(rot);
      return [(vx * c + vy * s) / res + size[0] / 2, -(-vx * s + vy * c) / res + size[1] / 2];
    };
    const frame = () => {
      if (!w.on) return;
      const res = view.getResolution(), cxy = view.getCenter(), rot = view.getRotation();
      // iz: eski çizgileri yavaşça sil
      g.globalCompositeOperation = 'destination-in';
      g.fillStyle = 'rgba(0,0,0,0.90)';
      g.fillRect(0, 0, size[0], size[1]);
      g.globalCompositeOperation = 'source-over';
      g.strokeStyle = color; g.lineWidth = 1.3; g.lineCap = 'round';
      g.beginPath();
      const k = 0.35 * res;  // m/s -> harita birimi/kare (yakınlaştırmadan bağımsız ekran hızı)
      for (const p of w.parts) {
        const [lon, lat] = toLL(p.x, p.y);
        const uv = sampleWind(f, lat, lon);
        if (!uv || ++p.age > 90) { spawn(p); p.age = 0; continue; }
        const nx = p.x + uv[0] * k, ny = p.y + uv[1] * k;
        const a = px(p.x, p.y, cxy, res, rot), b = px(nx, ny, cxy, res, rot);
        g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]);
        p.x = nx; p.y = ny;
      }
      g.stroke();
      if (!reduce) w.raf = requestAnimationFrame(frame);
    };
    if (reduce) {  // hareket azaltma: aynı akımı tek seferde, kısa izler olarak çiz
      for (let s = 0; s < 12; s++) frame();
    } else {
      w.raf = requestAnimationFrame(frame);
    }
  };

  // ---------------------------------------------------------------- güneş ısı haritası
  const drawSolar = () => {
    const c = ctx.current;
    if (!c) return;
    const f = solar && solar.points && solar.points.length ? solar : null;
    if (!f) { c.solarLayer.setSource(null); return; }
    if (c.solarKey !== f) {
      c.solarKey = f;
      const [ax, ay] = fromLL(f.lon0, f.lat0);
      const [bx, by] = fromLL(f.lon0 + f.step * (f.nlon - 1), f.lat0 + f.step * (f.nlat - 1));
      c.solarLayer.setSource(new c.ol.ImageStatic({url: solarImage(f, 24), imageExtent: [ax, ay, bx, by],
                                                   interpolate: true}));
    }
  };

  const draw = () => {
    const c = ctx.current;
    if (!c) return;
    const {source, ol} = c;
    source.clear();
    (latest.current || []).forEach((m) => {
      const f = new ol.Feature({geometry: new ol.Point(ol.fromLonLat([m.center[1], m.center[0]]))});
      f.setStyle(new ol.Style({
        image: new ol.CircleStyle({
          radius: m.radius || 8,
          fill: new ol.Fill({color: m.color || '#00ff41'}),
          stroke: new ol.Stroke({color: m.stroke || '#000000', width: 1.5}),
        }),
        zIndex: m.z || 0,
        text: new ol.Text({
          text: m.name || '', offsetY: -((m.radius || 8) + 10),
          font: '600 11px Inter, system-ui, sans-serif',
          fill: new ol.Fill({color: c.dark ? '#f2f2f2' : '#0a0a0a'}),
          stroke: new ol.Stroke({color: c.dark ? '#000000' : '#ffffff', width: 3}),
        }),
      }));
      source.addFeature(f);
    });
  };

  useEffect(() => {
    let alive = true;
    Promise.all([
      import('ol'), import('ol/layer'), import('ol/source'), import('ol/proj'),
      import('ol/geom'), import('ol/style'), import('ol/format'), import('ol/control'),
    ]).then(([core, layer, src, proj, geom, style, fmt, control]) => {
      const solarLayer = new layer.Image({visible: !!showSolar, opacity: 1});
      if (!alive || !el.current) return;
      const source = new src.Vector();
      // OSM karoları (anahtarsız). Tema görünümü CSS filtresiyle verilir (theme.css: .ol-base).
      const tiles = new layer.Tile({source: new src.OSM(), className: 'ol-base'});
      const zoneStyles = {};
      const zoneStyle = (f) => {
        const cls = f.get('cls');
        const key = cls + (ctx.current && ctx.current.dark ? 'd' : 'l');
        if (!zoneStyles[key]) {
          if (cls === 'sinir') {
            const dark = ctx.current && ctx.current.dark;
            zoneStyles[key] = new style.Style({stroke: new style.Stroke({
              color: dark ? '#f2f2f2' : '#0a0a0a', width: 1.6, lineDash: [6, 5]})});
          } else {
            const pair = ZONE_STYLE[cls];
            const [fill, stroke] = pair ? pair[(ctx.current && ctx.current.dark) ? 1 : 0] : ['rgba(0,0,0,0)', '#888'];
            zoneStyles[key] = new style.Style({fill: new style.Fill({color: fill}),
                                               stroke: new style.Stroke({color: stroke, width: 1.2})});
          }
        }
        return zoneStyles[key];
      };
      const zones = new layer.Vector({
        source: new src.Vector({url: zonesUrl, format: new fmt.GeoJSON({
          dataProjection: 'EPSG:4326', featureProjection: 'EPSG:3857'})}),
        style: zoneStyle, visible: showZones !== false,
      });
      const map = new core.Map({
        target: el.current,
        // Varsayılan döndürme düğmesi yerine kendi pusulamız (aynı işi görür: tıklayınca kuzeye hizalar)
        controls: control.defaults({rotate: false}),
        layers: [tiles, solarLayer, zones, new layer.Vector({source, declutter: true})],
        view: new core.View({center: proj.fromLonLat([center[1], center[0]]), zoom: zoom}),
      });
      map.addControl(compassControl(control.Control, map.getView()));  // sağ üst: K/D/G/B
      map.on('singleclick', (e) => {
        const [lng, lat] = proj.toLonLat(e.coordinate);
        if (cb.current) cb.current(lat, lng);
      });
      map.on('pointermove', (e) => {
        map.getTargetElement().style.cursor = 'crosshair';
      });
      // Rüzgâr akımı: haritanın üstünde, tıklamayı engellemeyen canvas
      const canvas = document.createElement('canvas');
      Object.assign(canvas.style, {position: 'absolute', inset: '0', width: '100%', height: '100%',
                                   pointerEvents: 'none'});
      map.getViewport().appendChild(canvas);
      map.on('movestart', () => { if (windRef.current.on) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height); });
      map.on('change:size', () => startWind());
      map.getView().on('change:rotation', () => canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height));
      ctx.current = {map, source, zones, zoneStyles, solarLayer, canvas, solarKey: null,
                     dark: tileStyle === 'dark', ol: {
        Feature: core.Feature, Point: geom.Point, fromLonLat: proj.fromLonLat,
        Style: style.Style, CircleStyle: style.Circle, Fill: style.Fill,
        Stroke: style.Stroke, Text: style.Text, ImageStatic: src.ImageStatic,
      }};
      draw();
      drawSolar();
      startWind();
    });
    return () => {
      alive = false;
      stopWind();
      if (ctx.current) { ctx.current.map.setTarget(undefined); ctx.current = null; }
    };
  }, []);

  useEffect(() => { draw(); }, [markers]);
  useEffect(() => {
    const c = ctx.current;
    if (!c) return;
    c.dark = tileStyle === 'dark';
    c.zones.changed();
    draw();
  }, [tileStyle]);
  useEffect(() => {
    const c = ctx.current;
    if (c) c.zones.setVisible(showZones !== false);
  }, [showZones]);
  useEffect(() => {
    const c = ctx.current;
    if (!c) return;
    drawSolar();
    c.solarLayer.setVisible(!!showSolar);
  }, [solar, showSolar]);
  useEffect(() => { startWind(); return stopWind; }, [wind, showWind, tileStyle]);

  return createElement('div', {ref: el, className, style: {width: '100%', height: mapHeight || '480px'}});
}
"""]


ol_map = OlMap.create
