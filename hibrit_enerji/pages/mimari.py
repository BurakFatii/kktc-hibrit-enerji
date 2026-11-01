"""Nasıl çalışır: sunum akışı (sorun -> çözüm -> şema -> bir gün -> fark -> fayda).

Her kavram bir anahtar kelime + altında tek cümle. Teknik ayrıntı yok; animasyonlar theme.css'te
(.hiw-*), hareket azaltma tercihinde durur. Akış sunum belgesiyle ("Enerjide yeni denge") uyumlu.
"""
import reflex as rx

from ..components import page, section
from ..viz import panel, svg


def kw(icon: str, word: str, sentence: str, cls: str = "", delay: float = 0) -> rx.Component:
    """Anahtar kelime kartı: ikon + kelime + tek cümle."""
    return rx.box(
        rx.hstack(rx.icon(icon, size=18, class_name="ink"), rx.text(word, size="4", weight="bold"),
                  align="center", spacing="2"),
        rx.text(sentence, size="2", class_name="muted", margin_top="6px"),
        class_name=f"dnode hiw-rise {cls}".strip(), style={"animationDelay": f"{delay}s"}, width="100%",
    )


# ------------------------------------------------------------------ 1. sorun
PROBLEMS = [
    ("fuel", "Fosil bağımlılığı",
     "KKTC elektriğinin çoğu ithal fuel-oil ile üretiliyor; güneşin payı 2022'de yalnızca %5,6."),
    ("cloud-sun", "Düzensiz üretim",
     "Güneş akşam biter, rüzgâr bölgeden bölgeye değişir; tek kaynak tek başına yetmez."),
    ("trash-2", "Boşa giden enerji",
     "Öğlen fazla üretim depolanamayınca kısılıyor, akşam zirvesinde ise elektrik eksik kalıyor."),
]


def problems() -> rx.Component:
    return rx.grid(*[kw(i, w, s, delay=n * 0.15) for n, (i, w, s) in enumerate(PROBLEMS)],
                   columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%")


# ------------------------------------------------------------------ 2. çözüm: 3 adım
STEPS = [
    ("database", "Veri toplama", "Konum, hava tahmini, geçmiş yılın saatlik verisi ve cihaz bilgileri toplanır."),
    ("line-chart", "Analiz ve tahmin", "Her saat güneşin, rüzgârın ne üreteceği ve tesisin ne tüketeceği hesaplanır."),
    ("cpu", "Akıllı yönetim", "Fazla enerji bataryaya ya da şebekeye gider; eksik önce bataryadan karşılanır."),
]


def steps() -> rx.Component:
    parts = []
    for n, (icon, word, sentence) in enumerate(STEPS):
        parts.append(rx.box(
            rx.hstack(rx.text(f"0{n + 1}", size="1", class_name="mono ink"), rx.icon(icon, size=18),
                      rx.text(word, size="4", weight="bold"), align="center", spacing="2"),
            rx.text(sentence, size="2", class_name="muted", margin_top="6px"),
            class_name="dnode hiw-step", style={"animationDelay": f"{n * 2}s"}, flex="1", width="100%"))
        if n < len(STEPS) - 1:
            parts.append(rx.box(class_name="hiw-arrow", display=rx.breakpoints(initial="none", md="block")))
    return rx.flex(*parts, direction=rx.breakpoints(initial="column", md="row"), align="stretch",
                   spacing="2", width="100%")


# ------------------------------------------------------------------ 3. sistem şeması (sadeleştirilmiş)
NODES = [  # (ikon, kelime, x%, y%, sınıf)
    ("sun", "Güneş", "9%", "18%", ""),
    ("wind", "Rüzgâr", "9%", "50%", ""),
    ("battery-charging", "Batarya", "9%", "82%", ""),
    ("repeat", "Dönüştürücü", "31%", "18%", "conv"),
    ("repeat", "Dönüştürücü", "31%", "50%", "conv"),
    ("arrow-left-right", "Çift yönlü", "31%", "82%", "conv"),
    ("cpu", "İnverter", "70%", "50%", "on"),
    ("building-2", "Tesis", "91%", "22%", ""),
    ("utility-pole", "Şebeke", "91%", "78%", ""),
]
LINES = [  # (x1, y1, x2, y2, sınıf)
    ("9", "18", "31", "18", "flow on"), ("9", "50", "31", "50", "flow on"), ("9", "82", "31", "82", "flow on rev"),
    ("31", "18", "50", "18", "flow on"), ("31", "50", "50", "50", "flow on"), ("31", "82", "50", "82", "flow on rev"),
    ("50", "50", "70", "50", "flow on"), ("70", "50", "91", "22", "flow on"), ("70", "50", "91", "78", "flow on"),
]
PARTS = [
    ("repeat", "Dönüştürücü", "Her kaynağın elektriğini ortak hatta uygun hale getirir."),
    ("git-merge", "Ortak hat", "Güneş, rüzgâr ve batarya enerjisi tek bir hatta buluşur."),
    ("battery-charging", "Batarya", "Fazlayı saklar, gerektiğinde geri verir; bu yüzden çift yönlüdür."),
    ("cpu", "İnverter", "Ortak hattaki elektriği tesisin ve şebekenin kullandığı elektriğe çevirir."),
    ("utility-pole", "Şebeke", "Fazla enerji sınır içinde şebekeye verilir, eksik olunca şebekeden alınır."),
]


def schema() -> rx.Component:
    diagram = rx.box(
        svg(*[svg.line(x1=a, y1=b, x2=c, y2=d, class_name=cl) for a, b, c, d, cl in LINES],
            svg.line(x1="50", y1="10", x2="50", y2="90", class_name="hiw-bus"),
            view_box="0 0 100 100", preserve_aspect_ratio="none"),
        *[rx.box(rx.hstack(rx.icon(ic, size=15), rx.text(w, size="2", weight="bold"), spacing="1",
                           justify="center", align="center"),
                 class_name=f"node {cl}".strip(), style={"left": x, "top": y})
          for ic, w, x, y, cl in NODES],
        rx.text("Ortak hat", size="1", class_name="muted mono hiw-buslabel"),
        class_name="flowbox", style={"height": "320px", "minWidth": "620px"},
    )
    return rx.vstack(
        rx.box(diagram, class_name="panel", overflow_x="auto"),
        rx.grid(*[kw(i, w, s, delay=n * 0.1) for n, (i, w, s) in enumerate(PARTS)],
                columns=rx.breakpoints(initial="1", sm="2", md="5"), spacing="2", width="100%"),
        spacing="3", width="100%",
    )


# ------------------------------------------------------------------ 4. bir gün (canlı sahne)
# Tek kaynak: faz tablosu. Sahnedeki her öğenin animasyonu bu tablodan üretilir (_kf), kartlar senkron kalır.
PHASE_S = 4                      # her faz 4 sn -> döngü 16 sn
CYCLE = PHASE_S * 4
PHASES = [  # (ikon, saat, kelime, cümle)
    ("sunrise", "Sabah · 07:00", "Güneş doğar",
     "Güneş ve rüzgâr tesisi beslemeye başlar; eksik kalan kısım şebekeden alınır."),
    ("sun", "Öğlen · 12:00", "Fazla var",
     "Fazla akıllıca bölünür: batarya akşama dolu girer, kalanı şebekeye verilir."),
    ("sunset", "Akşam · 19:00", "Zirve",
     "Güneş biter, tüketim artar; depolanan enerji ve rüzgâr tesisi besler."),
    ("moon", "Gece · 02:00", "Rüzgâr + şebeke",
     "Rüzgâr üretmeye devam eder, kalan açık şebekeden karşılanır."),
]
BATT = [35, 100, 45, 25]         # fazın sonundaki batarya doluluğu (%)
# Düğümler: (anahtar, ikon, kelime, x%, y%)
DAY_NODES = [("sun", "sun", "Güneş", 14, 22), ("wind", "wind", "Rüzgâr", 14, 78),
             ("site", "building-2", "Tesis", 52, 50), ("batt", "battery-charging", "Batarya", 52, 84),
             ("grid", "utility-pole", "Şebeke", 88, 50)]
# Akışlar: (başlangıç, bitiş, faz deseni: sabah-öğlen-akşam-gece, 1 = akıyor)
DAY_FLOWS = [("sun", "site", "1100"), ("sun", "batt", "0100"), ("wind", "site", "1011"),
             ("batt", "site", "0010"), ("grid", "site", "1001"), ("site", "grid", "0100")]
_POS = {k: (x, y) for k, _, _, x, y in DAY_NODES}


def _kf(name: str, props: dict[str, list[str]]) -> str:
    """4 faz değerinden yumuşak geçişli keyframe: her faz başında %3'lük geçiş, sonra sabit.
    Bir öğenin tek `animation`'ı olabildiği için aynı öğenin tüm özellikleri tek keyframe'de."""
    def at(i: int) -> str:
        return " ".join(f"{k}: {v[i]};" for k, v in props.items())
    pts = [f"0% {{ {at(-1)} }}"] + [f"{i * 25 + 3}% {{ {at(i)} }} {(i + 1) * 25}% {{ {at(i)} }}" for i in range(4)]
    return f"@keyframes {name} {{ {' '.join(pts)} }} .{name} {{ animation: {name} {CYCLE}s linear infinite; }}"


def _bits(pattern: str, on: str, off: str) -> list[str]:
    return [on if c == "1" else off for c in pattern]


def _node_pattern(key: str) -> str:
    """Düğüm, o fazda bir akışın ucundaysa yanar."""
    return "".join("1" if any(p[i] == "1" and key in (a, b) for a, b, p in DAY_FLOWS) else "0" for i in range(4))


def _scene_css() -> str:
    css = []
    for n, (_, _, pat) in enumerate(DAY_FLOWS):
        css.append(_kf(f"dk-f{n}", {"opacity": _bits(pat, "1", "0")}))
    for k, *_ in DAY_NODES:
        css.append(_kf(f"dk-n-{k}", {"border-color": _bits(_node_pattern(k), "var(--neon)", "var(--line)")}))
    for i in range(4):
        one = "".join("1" if j == i else "0" for j in range(4))
        css.append(_kf(f"dk-t{i}", {"opacity": _bits(one, "1", "0")}))                     # başlık + yüzde
        css.append(_kf(f"dk-c{i}", {"opacity": _bits(one, "1", ".45"),                      # kartlar
                                    "border-color": _bits(one, "var(--neon)", "var(--line)")}))
    css.append(_kf("dk-moon", {"opacity": ["0", "0", "0", "1"]}))
    css.append(_kf("dk-sky", {"background-color": ["var(--bg)", "var(--bg)", "var(--bg)", "var(--track)"]}))
    # Güneş: sabah doğar, öğlen tepede, akşam fazının ortasında ufka iner ve kaybolur; gece görünmez
    css.append(f"@keyframes dk-arm {{ 0% {{ transform: rotate(-80deg); }} 37% {{ transform: rotate(0deg); }} "
               f"62% {{ transform: rotate(85deg); }} 100% {{ transform: rotate(85deg); }} }} "
               f".dk-arm {{ animation: dk-arm {CYCLE}s linear infinite; }}")
    css.append(f"@keyframes dk-sun {{ 0%, 58% {{ opacity: 1; }} 62%, 98% {{ opacity: 0; }} 100% {{ opacity: 1; }} }} "
               f".dk-sun {{ animation: dk-sun {CYCLE}s linear infinite; }}")
    # Batarya: fazın ilk %60'ında hedefe ulaşır, sonra yazdığı yüzdeyle aynı kalır
    css.append(f"@keyframes dk-batt {{ 0% {{ width: {BATT[-1]}%; }} "
               + " ".join(f"{i * 25 + 15}% {{ width: {v}%; }} {(i + 1) * 25}% {{ width: {v}%; }}"
                          for i, v in enumerate(BATT))
               + f" }} .dk-batt {{ animation: dk-batt {CYCLE}s linear infinite; }}")
    css.append(f"@keyframes dk-cur {{ from {{ width: 0; }} to {{ width: 100%; }} }} "
               f".dk-cur {{ animation: dk-cur {CYCLE}s linear infinite; }}")
    css.append(f".day-line {{ animation-duration: .9s; animation-timing-function: linear; animation-iteration-count: infinite; }}")
    return "\n".join(css)


NOON = 1  # hareket azaltma tercihinde sahne bu fazda sabit kalır (satır içi başlangıç stilleri)


def day_scene() -> rx.Component:
    def line(a_, b_, cls, style=None):
        (x1, y1), (x2, y2) = _POS[a_], _POS[b_]
        return svg.line(x1=str(x1), y1=str(y1), x2=str(x2), y2=str(y2), class_name=cls, style=style or {})

    pairs = {tuple(sorted((a_, b_))) for a_, b_, _ in DAY_FLOWS}
    lines = [line(a_, b_, "day-base") for a_, b_ in sorted(pairs)]
    lines += [svg.g(line(a_, b_, "day-line"), class_name=f"dk-f{n}",
                    style={"opacity": "1" if p[NOON] == "1" else "0"})
              for n, (a_, b_, p) in enumerate(DAY_FLOWS)]

    def node(k, ic, w, x, y):
        extra = rx.fragment()
        if k == "batt":
            extra = rx.box(
                rx.box(rx.box(class_name="dk-batt", style={"width": f"{BATT[NOON]}%"}), class_name="day-batt"),
                rx.box(*[rx.text(f"%{v}", as_="span", size="1", class_name=f"mono muted dk-t{i}",
                                 style={"opacity": "1" if i == NOON else "0"}) for i, v in enumerate(BATT)],
                       class_name="day-pct"))
        return rx.box(rx.hstack(rx.icon(ic, size=16), rx.text(w, size="2", weight="bold"), spacing="1",
                                justify="center", align="center"), extra,
                      class_name=f"day-node dk-n-{k}",
                      style={"left": f"{x}%", "top": f"{y}%",
                             "borderColor": "var(--neon)" if _node_pattern(k)[NOON] == "1" else "var(--line)"})

    sky = rx.box(
        rx.box(rx.box(class_name="day-sun dk-sun"), class_name="day-arm dk-arm"),
        rx.box(rx.icon("moon", size=20), class_name="day-moon dk-moon", style={"opacity": "0"}),
        rx.box(*[rx.vstack(
                    rx.text(t, size="1", class_name="mono ink"),
                    rx.text(w, size="5", weight="bold"),
                    spacing="0", class_name=f"day-txt dk-t{i}", style={"opacity": "1" if i == NOON else "0"})
                 for i, (_, t, w, _) in enumerate(PHASES)], class_name="day-clock",
               style={"position": "absolute", "left": "14px", "top": "12px", "width": "50%", "height": "64px"}),
        class_name="day-sky dk-sky",
    )
    flow = rx.box(svg(*lines, view_box="0 0 100 100", preserve_aspect_ratio="none"),
                  *[node(*n) for n in DAY_NODES], class_name="day-flow")
    timeline = rx.box(
        *[rx.hstack(rx.icon(ic, size=13), rx.text(t.split(" · ")[0], size="1", class_name="mono muted"),
                    spacing="1", align="center") for ic, t, _, _ in PHASES],
        rx.box(class_name="day-cursor dk-cur"),
        class_name="day-timeline",
    )
    cards = rx.grid(
        *[rx.box(
            rx.hstack(rx.icon(ic, size=16, class_name="ink"), rx.text(t, size="1", class_name="mono muted"),
                      align="center", spacing="2"),
            rx.text(w, size="3", weight="bold", margin_top="4px"),
            rx.text(s_, size="2", class_name="muted", margin_top="4px"),
            class_name=f"dnode day-card dk-c{n}",
            style={"opacity": "1" if n == NOON else ".45",
                   "borderColor": "var(--neon)" if n == NOON else "var(--line)"}, width="100%")
          for n, (ic, t, w, s_) in enumerate(PHASES)],
        columns=rx.breakpoints(initial="1", sm="2", md="4"), spacing="2", width="100%",
    )
    return panel(rx.vstack(
        rx.el.style(_scene_css()),
        rx.box(sky, rx.box(flow, overflow_x="auto"), timeline, class_name="day"),
        cards, spacing="3", width="100%"))


# ------------------------------------------------------------------ 5. fark: basit kural vs akıllı yönetim
HOURS = list(range(6, 19))
BASIC_SOC = [10, 25, 45, 70, 95, 100, 100, 100, 100, 100, 100, 95, 85]
SMART_SOC = [10, 15, 22, 32, 45, 58, 70, 80, 88, 95, 100, 95, 85]
BASIC_CUT = [0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0]


def soc_row(word: str, sentence: str, socs: list[int], cuts: list[int]) -> rx.Component:
    return rx.vstack(
        rx.text(word, size="3", weight="bold"),
        rx.text(sentence, size="2", class_name="muted"),
        rx.box(*[rx.box(class_name=("bar curt" if c else "bar gain") + " hiw-grow",
                        style={"height": f"{s}%", "animationDelay": f"{i * 0.08}s"},
                        custom_attrs={"title": f"{h:02d}:00 · batarya %{s}" + (" · boşa gidiyor" if c else "")})
                 for i, (h, s, c) in enumerate(zip(HOURS, socs, cuts))],
               class_name="strip", style={"gridTemplateColumns": f"repeat({len(HOURS)}, 1fr)"}, width="100%"),
        spacing="1", width="100%",
    )


def difference() -> rx.Component:
    return panel(rx.grid(
        rx.vstack(
            soc_row("Basit kural", "Batarya 11:00'de dolar, öğlen üretilen enerji boşa gider.",
                    BASIC_SOC, BASIC_CUT),
            soc_row("Akıllı yönetim", "Önce şebekeye verir; batarya yine akşama dolu girer, hiçbir şey boşa gitmez.",
                    SMART_SOC, [0] * len(HOURS)),
            rx.box(*[rx.text(f"{h:02d}" if h % 3 == 0 else "", size="1", class_name="muted mono", text_align="center")
                     for h in HOURS],
                   style={"display": "grid", "gridTemplateColumns": f"repeat({len(HOURS)}, 1fr)"}, width="100%"),
            spacing="4", width="100%",
        ),
        rx.vstack(
            rx.text("%58–100", size="8", weight="bold", class_name="mono ink"),
            rx.text("daha az boşa giden enerji", size="3", weight="bold"),
            rx.text("Bölgelerin geçmiş yıl simülasyonunda, aynı bataryayla.", size="2", class_name="muted"),
            spacing="1", justify="center", height="100%",
        ),
        columns=rx.breakpoints(initial="1", md="3fr 1fr"), spacing="5", width="100%",
    ))


# ------------------------------------------------------------------ 6. kullanıcı ne kazanır
BENEFITS = [
    ("activity", "Takip", "Üretimi, batarya doluluğunu ve tüketimi anlık izler."),
    ("map-pin", "Planla", "Haritada nokta seçer; ne üreteceğini ve nasıl kurulacağını görür."),
    ("trending-up", "Kazan", "Daha az fosil yakıt, daha düşük fatura, daha güvenilir elektrik."),
]

# ------------------------------------------------------------------ 7. altyapı + dürüst sınırlar
TOOLS = ["pvlib", "windpowerlib", "Open-Meteo", "OpenLayers", "Gemini", "Reflex"]
LIMITS = [
    ("scan-search", "~9 km veri", "Dağ sırtı ve burun rüzgârı yerel ölçümle doğrulanmalı."),
    ("gauge", "Simülasyon", "Tüketim ve batarya, sayaç bağlanana kadar faturadan tahmin edilir."),
    ("target", "Kusursuz tahmin", "Simülasyondaki yönetim hava tahmininin doğru çıktığını varsayar."),
    ("receipt", "Varsayım maliyet", "Yerel tekliflerle Ayarlar'dan güncellenir."),
]


def mimari() -> rx.Component:
    return page(
        section("Sorun", problems()),
        section("Çözüm: 3 adım", steps()),
        section("Sistem şeması", schema()),
        section("Bir günde akıllı yönetim", day_scene()),
        section("Farkımız", difference()),
        section("Kullanıcı ne kazanır?",
                rx.grid(*[kw(i, w, s, delay=n * 0.15) for n, (i, w, s) in enumerate(BENEFITS)],
                        columns=rx.breakpoints(initial="1", md="3"), spacing="3", width="100%")),
        section("Altyapı ve sınırlar",
                rx.flex(*[rx.box(rx.text(t, size="2", weight="bold", class_name="mono"), class_name="hiw-chip")
                          for t in TOOLS], wrap="wrap", style={"gap": "8px"}, width="100%"),
                rx.grid(*[kw(i, w, s) for i, w, s in LIMITS],
                        columns=rx.breakpoints(initial="1", sm="2", md="4"), spacing="2", width="100%")),
        nav="/nasil-calisir",
        title="Nasıl çalışır",
    )
