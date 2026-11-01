"""Görselleştirme bileşenleri: akılda canlandırması zor sayıları basitleştirir.

Kural: zaman içinde değişimi önemli olan veri -> grafik (charts.py).
Tek bir orantı / durum / yön -> bu dosyadaki göstergeler.
Tüm renkler assets/theme.css değişkenlerinden gelir (neon + siyah/beyaz, gölgesiz).
"""
from __future__ import annotations

import reflex as rx

svg = rx.el.svg


def panel(*children, **props) -> rx.Component:
    return rx.box(*children, class_name="panel " + props.pop("extra_class", ""), **props)


def live_dot(title: str = "Canlı veri") -> rx.Component:
    """'Şu an' yazısı yerine: yanıp sönen küçük nokta (canlı veri)."""
    return rx.box(class_name="live-dot", custom_attrs={"title": title, "aria-label": title, "role": "img"})


def eyebrow(text) -> rx.Component:
    return rx.text(text, class_name="eyebrow")


def big_number(value, unit: str = "", size: str = "7") -> rx.Component:
    return rx.hstack(
        rx.text(value, size=size, weight="bold", class_name="mono"),
        rx.text(unit, size="2", class_name="muted"),
        align="baseline", spacing="1",
    )


# ------------------------------------------------------------------ yüzde bar
def meter(label, value, pct, note=None, dim=False) -> rx.Component:
    """Yüzde dolgulu bar. pct: 0–100 (str veya Var)."""
    return rx.box(
        rx.hstack(
            rx.text(label, size="1", class_name="muted"),
            rx.spacer(),
            rx.text(value, size="2", weight="medium", class_name="mono"),
            width="100%", align="baseline",
        ),
        rx.box(rx.box(class_name="fill dim" if dim else "fill", style={"width": pct + "%"}),
               class_name="track", margin_top="6px"),
        rx.text(note, size="1", class_name="muted", margin_top="4px") if note is not None else rx.fragment(),
        width="100%",
    )


def diverge(label, value, left_pct, width_pct) -> rx.Component:
    """−1…+1 aralığındaki değer için ortadan sapan bar (ör. korelasyon)."""
    return rx.box(
        rx.hstack(rx.text(label, size="1", class_name="muted"), rx.spacer(),
                  rx.text(value, size="2", weight="medium", class_name="mono"), width="100%"),
        rx.box(rx.box(class_name="dfill", style={"left": left_pct + "%", "width": width_pct + "%"}),
               rx.box(class_name="mid"), class_name="dtrack", margin_top="6px"),
        rx.hstack(rx.text("−1 zıt", size="1", class_name="muted"), rx.spacer(),
                  rx.text("0", size="1", class_name="muted"), rx.spacer(),
                  rx.text("+1 aynı", size="1", class_name="muted"), width="100%", margin_top="2px"),
        width="100%",
    )


def level3(status) -> rx.Component:
    """uygun / sınırlı / zayıf -> 3 / 2 / 1 dolu blok."""
    def blocks(n: int):
        return rx.box(*[rx.el.span(class_name="on" if i < n else "") for i in range(3)], class_name="lvl3")
    return rx.match(status, ("uygun", blocks(3)), ("sınırlı", blocks(2)), ("yasak", blocks(0)), blocks(1))


def bar_list(rows, label_key: str, pct_key: str, text_key: str, note_key: str | None = None) -> rx.Component:
    """Etiket + yüzde bar listesi (bölge karşılaştırması vb.)."""
    return rx.vstack(
        rx.foreach(rows, lambda r: rx.box(
            rx.hstack(rx.text(r[label_key], size="2"), rx.spacer(),
                      rx.text(r[text_key], size="2", class_name="mono"), width="100%"),
            rx.box(rx.box(class_name="fill", style={"width": r[pct_key] + "%"}), class_name="track",
                   margin_top="4px"),
            rx.text(r[note_key], size="1", class_name="muted") if note_key else rx.fragment(),
            width="100%",
        )),
        spacing="3", width="100%",
    )


# ------------------------------------------------------------------ batarya
def battery(pct, text, low) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.box(
                rx.box(class_name=rx.cond(low, "lvl low", "lvl"), style={"width": pct + "%"}),
                rx.box(*[rx.el.span() for _ in range(5)], class_name="ticks"),
                class_name="body",
            ),
            rx.box(class_name="nub"),
            class_name="battery",
        ),
        rx.text(text, size="6", weight="bold", class_name="mono"),
        spacing="2", width="100%",
    )


# ------------------------------------------------------------------ pusula
def compass(deg, center_text, size: str = "120px") -> rx.Component:
    """Rüzgârın GELDİĞİ yön: ok çemberin o kenarından merkeze doğru eser."""
    labels = [("K", 60, 9), ("D", 113, 64), ("G", 60, 118), ("B", 7, 64)]
    return svg(
        svg.circle(cx="60", cy="60", r="50", class_name="gauge-line"),
        svg.circle(cx="60", cy="60", r="34", class_name="gauge-line", style={"strokeDasharray": "2 4"}),
        *[svg.text(t, x=str(x), y=str(y), class_name="gauge-text", style={"textAnchor": "middle"})
          for t, x, y in labels],
        svg.g(
            svg.line(x1="60", y1="12", x2="60", y2="44", class_name="gauge-neon"),
            svg.polygon(points="53,40 67,40 60,54", class_name="gauge-fill-neon"),
            class_name="rot",
            style={"transform": "rotate(" + deg + "deg)", "transformOrigin": "60px 60px"},
        ),
        svg.text(center_text, x="60", y="64", class_name="gauge-text",
                 style={"textAnchor": "middle", "fill": "var(--fg)", "fontSize": "11px"}),
        view_box="0 0 120 120", width=size, height=size,
    )


# ------------------------------------------------------------------ panel eğimi
def tilt_view(tilt, label) -> rx.Component:
    """Yandan görünüş: zemin + eğik panel."""
    return svg(
        svg.line(x1="8", y1="86", x2="152", y2="86", class_name="gauge-fg"),
        *[svg.line(x1=str(x), y1="86", x2=str(x - 6), y2="94", class_name="gauge-line") for x in range(18, 152, 14)],
        svg.g(
            svg.line(x1="40", y1="86", x2="140", y2="86", style={"stroke": "var(--neon)", "strokeWidth": "5"}),
            class_name="rot",
            style={"transform": "rotate(-" + tilt + "deg)", "transformOrigin": "40px 86px"},
        ),
        svg.line(x1="40", y1="86", x2="40", y2="40", class_name="gauge-line", style={"strokeDasharray": "2 3"}),
        svg.circle(cx="40", cy="86", r="3", style={"fill": "var(--fg)"}),
        svg.text(label, x="150", y="20", class_name="gauge-text",
                 style={"textAnchor": "end", "fill": "var(--fg)", "fontSize": "12px"}),
        view_box="0 0 160 100", width="100%", height="100px",
    )


# ------------------------------------------------------------------ güneş yayı
def sun_arc(x, y, up, label) -> rx.Component:
    """Güneyden bakış: soldan (doğu) sağa (batı) gün yayı ve güneşin şu anki yeri."""
    return svg(
        svg.path(d="M 10 100 A 90 90 0 0 1 190 100", class_name="gauge-line", style={"strokeDasharray": "3 4"}),
        svg.line(x1="4", y1="100", x2="196", y2="100", class_name="gauge-fg"),
        svg.text("D", x="10", y="112", class_name="gauge-text", style={"textAnchor": "middle"}),
        svg.text("G", x="100", y="112", class_name="gauge-text", style={"textAnchor": "middle"}),
        svg.text("B", x="190", y="112", class_name="gauge-text", style={"textAnchor": "middle"}),
        rx.cond(up == "1",
                svg.circle(cx=x, cy=y, r="8", class_name="gauge-fill-neon"),
                svg.circle(cx="100", cy="100", r="5", style={"fill": "var(--muted)"})),
        svg.text(label, x="100", y="20", class_name="gauge-text",
                 style={"textAnchor": "middle", "fill": "var(--fg)", "fontSize": "11px"}),
        view_box="0 0 200 116", width="100%", height="116px",
    )


# ------------------------------------------------------------------ güç akışı
def _node(icon: str, label: str, value, x: str, y: str, on, hub: bool = False) -> rx.Component:
    return rx.box(
        rx.hstack(rx.icon(icon, size=14), rx.text(label, size="1", class_name="muted"),
                  spacing="1", justify="center", align="center"),
        rx.text(value, size="3", weight="bold", class_name="mono"),
        class_name=rx.cond(on, "node on" + (" hub" if hub else ""), "node" + (" hub" if hub else "")),
        style={"left": x, "top": y},
    )


def _line(x1, y1, x2, y2, cls) -> rx.Component:
    return svg.line(x1=x1, y1=y1, x2=x2, y2=y2, class_name=cls)


def power_flow(D) -> rx.Component:
    """Kaynaklardan eve, bataryaya ve şebekeye anlık güç akışı (çizgiler akar)."""
    def cls(key: str, rev_key: str | None = None):
        if rev_key is None:
            return rx.cond(D[key] == "1", "flow on", "flow")
        return rx.cond(D[key] == "1", "flow on", rx.cond(D[rev_key] == "1", "flow on rev", "flow"))

    return rx.box(
        svg(
            _line("14", "20", "50", "48", cls("on_pv")),
            _line("14", "80", "50", "48", cls("on_wind")),
            _line("50", "48", "86", "20", cls("on_load")),
            _line("50", "48", "86", "80", cls("on_exp", "on_imp")),
            _line("50", "48", "50", "86", cls("on_chg", "on_dis")),
            view_box="0 0 100 100", preserve_aspect_ratio="none",
        ),
        _node("sun", "Güneş", D["pv_now"] + " kW", "14%", "20%", D["on_pv"] == "1"),
        _node("wind", "Rüzgâr", D["wind_now"] + " kW", "14%", "80%", D["on_wind"] == "1"),
        _node("cpu", "İnverter", D["mode_short"], "50%", "48%", True, hub=True),
        _node("building-2", "Tesis", D["load_now"] + " kW", "86%", "20%", D["on_load"] == "1"),
        _node("utility-pole", "Şebeke", D["grid_text"], "86%", "80%",
              (D["on_exp"] == "1") | (D["on_imp"] == "1")),
        _node("battery-charging", "Batarya", D["batt_text"], "50%", "86%",
              (D["on_chg"] == "1") | (D["on_dis"] == "1")),
        class_name="flowbox",
    )


# ------------------------------------------------------------------ 24 saat şeridi
def day_strip(cells) -> rx.Component:
    """Üst: saatlik üretim (renk = sistemin kararı). Alt: batarya doluluğu."""
    return rx.vstack(
        rx.box(rx.foreach(cells, lambda c: rx.box(
            class_name="bar " + c["cat"], style={"height": c["h"] + "%"}, custom_attrs={"title": c["tip"]})),
            class_name="strip", width="100%"),
        rx.box(rx.foreach(cells, lambda c: rx.box(
            class_name="bar", style={"height": c["soc"] + "%"}, custom_attrs={"title": c["tip"]})),
            class_name="strip soc", width="100%"),
        rx.box(rx.foreach(cells, lambda c: rx.text(c["lbl"], size="1", class_name="muted mono",
                                                     text_align="center")),
               style={"display": "grid", "gridTemplateColumns": "repeat(24, 1fr)"}, width="100%"),
        rx.hstack(
            *[rx.hstack(rx.box(class_name="legend-dot", style=st), rx.text(t, size="1", class_name="muted"),
                        spacing="0", align="center")
              for t, st in [("depola / şebekeye ver", {"background": "var(--neon)"}),
                            ("bataryadan besle", {"background": "var(--fg)", "opacity": ".55"}),
                            ("şebekeden çek", {"background": "var(--muted)", "opacity": ".45"}),
                            ("kısıt", {"outline": "1px solid var(--neon)", "outlineOffset": "-1px"}),
                            ("batarya %", {"background": "var(--neon)", "opacity": ".45"})]],
            spacing="4", wrap="wrap",
        ),
        spacing="1", width="100%",
    )


# ------------------------------------------------------------------ uygun / değil ikonu
def ok_icon(icon: str, label: str, ok) -> rx.Component:
    """Kaynak ikonu + ✓ (uygun) / ✗ (uygun değil). ok: '1' / '0'."""
    good = ok == "1"
    return rx.hstack(
        rx.icon(icon, size=16),
        rx.text(label, size="2"),
        rx.cond(good, rx.icon("circle-check", size=18, color="var(--ok)"),
                rx.icon("circle-x", size=18, color="var(--bad)")),
        spacing="1", align="center",
        custom_attrs={"title": rx.cond(good, label + ": uygun", label + ": uygun değil")},
    )


# ------------------------------------------------------------------ yığılı bar
def stack_bar(segments: list[tuple], height: str = "22px") -> rx.Component:
    """segments: [(yüzde, renk_css, etiket, değer)] — toplam %100. Altında lejant."""
    return rx.vstack(
        rx.box(*[rx.box(style={"width": pct + "%", "background": color, "height": "100%"},
                        custom_attrs={"title": label}) for pct, color, label, _ in segments],
               style={"display": "flex", "width": "100%", "height": height, "background": "var(--track)",
                      "overflow": "hidden"}),
        rx.hstack(*[rx.hstack(rx.box(class_name="legend-dot", style={"background": color}),
                              rx.text(label, size="1", class_name="muted"),
                              rx.text(value, size="1", weight="bold", class_name="mono"),
                              spacing="1", align="center")
                    for _, color, label, value in segments],
                  spacing="4", wrap="wrap"),
        spacing="2", width="100%",
    )


# ------------------------------------------------------------------ şehir ihtiyacı paneli
def city_panel(C, compact: bool = False) -> rx.Component:
    """Seçili noktanın ilçe ihtiyacı ve o noktaya göre boyutlanmış santralin karşılama oranları.
    compact=True: yalnızca ihtiyaç, santral ve bataryalı karşılama (özet sayfa)."""
    if compact:
        return rx.cond(
            C.length() > 0,
            rx.vstack(
                eyebrow(C["ilce"] + " ilçesinin ihtiyacı"),
                big_number(C["need_year"], "/ yıl", "7"),
                rx.cond(
                    C["ok"] == "1",
                    rx.vstack(
                        rx.text("Bu noktada gereken santral", size="1", class_name="muted"),
                        rx.text(C["plant"], size="3", weight="bold", class_name="mono"),
                        meter("İhtiyacın karşılanan kısmı (bataryalı)", C["with_batt"], C["with_batt_pct"]),
                        spacing="2", width="100%",
                    ),
                    rx.text(C["msg"], size="2", style={"color": "var(--bad)"}),
                ),
                spacing="2", width="100%",
            ),
        )
    def kv(label: str, value) -> rx.Component:
        return rx.vstack(rx.text(label, size="1", class_name="muted"),
                         rx.text(value, size="3", weight="bold", class_name="mono"), spacing="0")

    return rx.cond(
        C.length() > 0,
        rx.vstack(
            eyebrow("Şehrin ihtiyacı · " + C["ilce"] + " ilçesi"),
            rx.hstack(kv("Nüfus (2021 tahmini)", C["pop"]), kv("Yıllık ihtiyaç", C["need_year"]),
                      kv("Ortalama güç", C["need_avg"]), spacing="5", wrap="wrap", width="100%"),
            rx.hstack(rx.box(width="10px", height="10px", style={"background": C["fit_color"]}),
                      rx.text("Bu nokta: " + C["fit"], size="2"), align="center", spacing="2"),
            rx.cond(
                C["ok"] == "1",
                rx.vstack(
                    rx.divider(margin_y="4px"),
                    eyebrow("Bu noktada ihtiyacı karşılayacak santral"),
                    rx.text(C["plant"], size="3", weight="bold", class_name="mono"),
                    rx.text("Batarya: " + C["batt"], size="1", class_name="muted mono"),
                    meter("Önümüzdeki 48 saatte, saat saat (üretim " + C["prod48"] + " · ihtiyaç " + C["load48"] + ")",
                          C["cover48"], C["cover48_pct"]),
                    meter("Bir yılda, bataryasız (saat saat)", C["direct"], C["direct_pct"]),
                    meter("Bir yılda, bataryalı", C["with_batt"], C["with_batt_pct"]),
                    rx.text("Kurulu güç / ortalama ihtiyaç: " + C["ratio"] + ". " + C["msg"],
                            size="1", class_name="muted"),
                    spacing="2", width="100%",
                ),
                rx.text(C["msg"], size="2", style={"color": "var(--bad)"}),
            ),
            rx.text(C["sources"], size="1", class_name="muted"),
            spacing="2", width="100%",
        ),
    )
