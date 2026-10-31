"""OpenLayers haritası (OSM altlık) — Reflex bileşeni.

- `markers`: [{"center": [lat, lon], "name": str, "color": "#hex", "radius": int}]
- `on_pick(lat, lng)`: haritaya tıklanan noktanın koordinatı

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

function OlMap({markers, center, zoom, mapHeight, tileStyle, zonesUrl, showZones, onPick, className}) {
  const el = useRef(null);
  const ctx = useRef(null);       // {map, source, ol}
  const cb = useRef(onPick);
  cb.current = onPick;
  const latest = useRef(markers);
  latest.current = markers;

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
      import('ol/geom'), import('ol/style'), import('ol/format'),
    ]).then(([core, layer, src, proj, geom, style, fmt]) => {
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
        layers: [tiles, zones, new layer.Vector({source, declutter: true})],
        view: new core.View({center: proj.fromLonLat([center[1], center[0]]), zoom: zoom}),
      });
      map.on('singleclick', (e) => {
        const [lng, lat] = proj.toLonLat(e.coordinate);
        if (cb.current) cb.current(lat, lng);
      });
      map.on('pointermove', (e) => {
        map.getTargetElement().style.cursor = 'crosshair';
      });
      ctx.current = {map, source, zones, zoneStyles, dark: tileStyle === 'dark', ol: {
        Feature: core.Feature, Point: geom.Point, fromLonLat: proj.fromLonLat,
        Style: style.Style, CircleStyle: style.Circle, Fill: style.Fill,
        Stroke: style.Stroke, Text: style.Text,
      }};
      draw();
    });
    return () => {
      alive = false;
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

  return createElement('div', {ref: el, className, style: {width: '100%', height: mapHeight || '480px'}});
}
"""]


ol_map = OlMap.create
