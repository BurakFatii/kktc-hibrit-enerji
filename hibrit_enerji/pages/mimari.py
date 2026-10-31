"""Nasıl çalışır: teknik mimari ve karar mantığı — görsel anlatım (jüri K3)."""
import reflex as rx

from ..components import page, section
from ..viz import eyebrow, panel, svg

# ------------------------------------------------------------------ 1. veriden karara
PIPE = [
    ("database", "Veri", ["Tarayıcı konumu", "Open-Meteo tahmini (3 gün)", "Geçmiş yılın 8760 saati",
                          "Cihaz etiket değerleri"]),
    ("sigma", "Fizik modeli", ["pvlib · güneş konumu, Perez ışınımı", "pvlib · NOCT sıcaklık, PVWatts",
                               "windpowerlib · göbek hızı, hava yoğunluğu", "windpowerlib · güç eğrisi"]),
    ("cpu", "Enerji yönetimi", ["Saatlik denge: üretim − tüketim", "Tahmine dayalı batarya planı",
                                "Şebekeye limitli verme", "Kısıt alanı kontrolü"]),
    ("monitor", "Çıktı", ["Anlık karar ve güç akışı", "Panel açısı · türbin yönü",
                          "Bölge analizi", "4 senaryo · kapasite taraması"]),
]


def pipe_node(icon: str, title: str, items: list[str], n: int) -> rx.Component:
    return rx.box(
        rx.hstack(rx.text(f"0{n}", size="1", class_name="mono ink"), rx.icon(icon, size=16),
                  rx.text(title, weight="bold", size="3"), align="center", spacing="2"),
        rx.vstack(*[rx.text(i, size="1", class_name="muted") for i in items], spacing="1", padding_top="8px"),
        class_name="dnode key" if n in (2, 3) else "dnode", flex="1", min_width="180px", width="100%",
    )


def pipeline() -> rx.Component:
    parts = []
    for n, (icon, title, items) in enumerate(PIPE, start=1):
        parts.append(pipe_node(icon, title, items, n))
        if n < len(PIPE):
            parts.append(rx.box(class_name="hconn", display=rx.breakpoints(initial="none", md="block")))
    return rx.flex(*parts, direction=rx.breakpoints(initial="column", md="row"), align="center",
                   spacing="2", width="100%")


# ------------------------------------------------------------------ 2. elektrik mimarisi
NODES = [  # (ikon, etiket, alt etiket, x%, y%, vurgulu)
    ("sun", "PV paneller", "sabit / takipçili", "11%", "16%", False),
    ("wind", "Rüzgâr türbini", "otomatik / sabit", "11%", "50%", False),
    ("zap", "MPPT · şarj", "DC", "33%", "33%", False),
    ("cpu", "Hibrit inverter", "ATS · ada modu", "57%", "33%", True),
    ("battery-charging", "LiFePO4 + BMS", "tesis bataryası", "57%", "80%", False),
    ("building-2", "Tesis panosu", "yükler", "87%", "16%", False),
    ("gauge", "Akıllı sayaç", "ölçüm", "87%", "50%", False),
    ("utility-pole", "Şebeke", "limitli verme", "87%", "86%", False),
]
LINES = [("11", "16", "33", "33"), ("11", "50", "33", "33"), ("33", "33", "57", "33"),
         ("57", "33", "57", "80"), ("57", "33", "87", "16"), ("87", "16", "87", "50"),
         ("87", "50", "87", "86")]


def electrical() -> rx.Component:
    return rx.box(
        svg(*[svg.line(x1=a, y1=b, x2=c, y2=d, class_name="flow on") for a, b, c, d in LINES],
            view_box="0 0 100 100", preserve_aspect_ratio="none"),
        *[rx.box(rx.hstack(rx.icon(ic, size=14), rx.text(lbl, size="1", weight="bold"), spacing="1",
                           justify="center", align="center"),
                 rx.text(sub, size="1", class_name="muted"),
                 class_name="node on" if key else "node", style={"left": x, "top": y})
          for ic, lbl, sub, x, y, key in NODES],
        class_name="flowbox", style={"height": "380px", "minWidth": "560px"},
    )


# ------------------------------------------------------------------ 3. karar ağacı
def q(text: str) -> rx.Component:
    return rx.box(rx.text(text, size="2", weight="bold"), class_name="dnode key", width="100%")


def a(text: str, tag: str = "") -> rx.Component:
    return rx.box(rx.hstack(rx.text(tag, size="1", class_name="mono ink") if tag else rx.fragment(),
                            rx.text(text, size="2"), spacing="2", align="center"),
                  class_name="dnode", width="100%")


def down() -> rx.Component:
    return rx.box(class_name="dconn")


def decision_tree() -> rx.Component:
    return rx.vstack(
        rx.box(q("Her saat: üretim tüketimden fazla mı?"), max_width="520px", width="100%", margin="0 auto"),
        rx.grid(
            rx.vstack(
                rx.text("EVET · fazla var", size="1", class_name="mono ink"),
                q("Tahmin: batarya bu fazla dönemi içinde zaten dolacak mı?"), down(),
                a("Önce şebeke limitini kullan, bataryaya limitin üstünü yükle", "evet →"), down(),
                a("Batarya akşama yine dolu girer; öğlen kısıt olmaz"), down(),
                a("Dolmayacaksa: önce batarya, kalanı şebekeye", "hayır →"), down(),
                a("Batarya ve limit doluysa: üretim kısıtlanır"),
                spacing="0", align="stretch", width="100%",
            ),
            rx.vstack(
                rx.text("HAYIR · açık var", size="1", class_name="mono muted"),
                a("Tesisi bataryadan besle", "1"), down(),
                a("Kalan açığı şebekeden çek", "2"),
                spacing="0", align="stretch", width="100%",
            ),
            columns=rx.breakpoints(initial="1", md="2"), spacing="5", width="100%",
        ),
        spacing="4", width="100%",
    )


# ------------------------------------------------------------------ 4. basit vs akıllı
HOURS = list(range(6, 19))
BASIC_SOC = [10, 25, 45, 70, 95, 100, 100, 100, 100, 100, 100, 95, 85]
SMART_SOC = [10, 15, 22, 32, 45, 58, 70, 80, 88, 95, 100, 95, 85]
BASIC_CUT = [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0]


def soc_row(label: str, socs: list[int], cuts: list[int], note: str) -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text(label, size="2", weight="bold"), rx.spacer(), rx.text(note, size="1", class_name="muted"),
                  width="100%", wrap="wrap"),
        rx.box(*[rx.box(class_name="bar curt" if c else "bar gain", style={"height": f"{s}%"},
                        custom_attrs={"title": f"{h:02d}:00 · batarya %{s}" + (" · kısıt" if c else "")})
                 for h, s, c in zip(HOURS, socs, cuts)],
               class_name="strip", style={"gridTemplateColumns": f"repeat({len(HOURS)}, 1fr)"}, width="100%"),
        spacing="1", width="100%",
    )


def compare_strategies() -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow("Aynı güneşli gün · batarya doluluğu 06:00–18:00 (örnek)"),
            soc_row("Basit kural", BASIC_SOC, BASIC_CUT, "11:00'de dolar → öğlen limit dolu, enerji kısılır"),
            soc_row("Akıllı yönetim", SMART_SOC, [0] * len(HOURS), "önce şebeke; batarya 16:00'da dolar → kısıt yok"),
            rx.box(*[rx.text(f"{h:02d}" if h % 3 == 0 else "", size="1", class_name="muted mono", text_align="center")
                     for h in HOURS],
                   style={"display": "grid", "gridTemplateColumns": f"repeat({len(HOURS)}, 1fr)"}, width="100%"),
            rx.hstack(rx.box(class_name="legend-dot", style={"background": "var(--neon)"}),
                      rx.text("batarya doluluğu", size="1", class_name="muted"),
                      rx.box(class_name="legend-dot",
                             style={"outline": "1px solid var(--neon)", "outlineOffset": "-1px", "marginLeft": "12px"}),
                      rx.text("kısılan enerji olan saat", size="1", class_name="muted"), align="center", spacing="0"),
            rx.text("İki durumda da batarya akşama dolu girer, öz yeterlilik aynı kalır. Fark, öğlen boşa giden "
                    "enerjinin şebekeye verilmesidir; simülasyonda kısılan enerji bölgeye göre %58–100 azalır.",
                    size="1", class_name="muted"),
            spacing="3", width="100%",
        ),
    )


# ------------------------------------------------------------------ 5. kütüphaneler + sınırlar
LIBS = [("pvlib", "güneş modeli"), ("windpowerlib", "rüzgâr modeli"), ("Open-Meteo", "hava verisi"),
        ("OpenLayers", "harita"), ("Reflex", "arayüz"), ("Plotly", "grafikler")]
LIMITS = ["Geçmiş yıl verisi ~9 km çözünürlükte; dağ sırtı ve burun rüzgârı yerel ölçümle doğrulanmalı.",
          "Tüketim ve batarya, sayaç/BMS bağlanana kadar fatura değerinden simüle edilir.",
          "Simülasyondaki akıllı yönetim kusursuz tahmin varsayar; sahada tahmin hatası olur.",
          "Maliyetler varsayımdır; Ayarlar'dan yerel tekliflerle güncellenmelidir."]


def mimari() -> rx.Component:
    return page(
        section("Veriden karara", "01 · Akış", pipeline()),
        section("Elektrik mimarisi", "02 · Sahadaki sistem",
                rx.box(electrical(), class_name="panel", overflow_x="auto"),
                rx.text("Hibrit inverter DC barada güneş, rüzgâr ve bataryayı birleştirir; ATS kesintide tesisi adalar. "
                        "Aynı karar mantığı sahada gömülü cihazda (Rust) çalışacak; bu uygulama izleme ve planlama "
                        "paneli olarak kalacak.", size="2", class_name="muted")),
        section("Akıllı yönetim nasıl karar verir?", "03 · Saatlik karar", panel(decision_tree())),
        section("Basit kural ile akıllı yönetim", "04 · Fark nerede?", compare_strategies()),
        rx.grid(
            panel(rx.vstack(eyebrow("Kullanılan kütüphaneler"),
                            rx.grid(*[rx.box(rx.text(n, size="2", weight="bold", class_name="mono"),
                                             rx.text(d, size="1", class_name="muted"), class_name="dnode")
                                      for n, d in LIBS], columns="2", spacing="2", width="100%"),
                            spacing="3", width="100%")),
            panel(rx.vstack(eyebrow("Bilinen sınırlar"),
                            *[rx.hstack(rx.box(width="6px", height="6px", background="var(--muted)", margin_top="7px",
                                               flex_shrink="0"), rx.text(t, size="2"), align="start", spacing="2")
                              for t in LIMITS], spacing="2", width="100%")),
            columns=rx.breakpoints(initial="1", md="2"), spacing="3", width="100%",
        ),
        nav="/nasil-calisir",
        title="Nasıl çalışır",
        subtitle="Verinin kaynağından karara kadar sistemin teknik mimarisi.",
    )
