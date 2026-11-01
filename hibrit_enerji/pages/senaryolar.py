"""Doğrulama: 4 senaryo × aday bölgeler + kapasite taraması."""
import reflex as rx

from ..components import error_box, loading_line, page
from ..core.config import CANDIDATE_REGIONS
from ..state import ScenarioState
from ..viz import bar_list, eyebrow, meter, panel

S = ScenarioState.smart


def dict_table(rows, cols: list[tuple[str, str]]) -> rx.Component:
    return rx.box(
        rx.table.root(
            rx.table.header(rx.table.row(*[rx.table.column_header_cell(h) for _, h in cols])),
            rx.table.body(rx.foreach(rows, lambda r: rx.table.row(
                *[rx.table.cell(r[k]) for k, _ in cols]))),
            size="1", variant="ghost", width="100%",
        ),
        overflow_x="auto", width="100%",
    )


def senaryolar() -> rx.Component:
    return page(
        rx.hstack(
            rx.text("Ayrıntı bölgesi:", size="2"),
            rx.select(["Seçili nokta"] + list(CANDIDATE_REGIONS), value=ScenarioState.region,
                      on_change=ScenarioState.set_region, size="2"),
            rx.button(rx.icon("play", size=14), "Yeniden çalıştır", size="2", variant="outline",
                      on_click=ScenarioState.run, loading=ScenarioState.loading),
            align="center", wrap="wrap",
        ),
        error_box(ScenarioState.error),
        loading_line(ScenarioState.loading, "11 bölge için 8760 saatlik simülasyon çalışıyor (ilk açılış "
                     "~15 sn, sonra önbellekten)…"),
        rx.box(rx.vstack(rx.foreach(ScenarioState.conclusion, lambda t: rx.text(t, size="2", as_="div")),
                         spacing="1"),
               class_name="panel", style={"borderColor": "var(--neon)"}),
        rx.cond(
            ScenarioState.rows.length() > 0,
            rx.vstack(
                rx.heading("Senaryolar: ", ScenarioState.place, size="4"),
                rx.grid(
                    panel(eyebrow("İhtiyacın karşılanan kısmı"), bar_list(ScenarioState.rows, "ad", "ozv", "oz")),
                    panel(eyebrow("Enerji açığı (şebekeden)"), bar_list(ScenarioState.rows, "ad", "acikp", "acikt")),
                    panel(eyebrow("Yatırım (en yükseğe göre)"), bar_list(ScenarioState.rows, "ad", "yatp", "yatt")),
                    panel(eyebrow("Önlenen CO₂ (en yükseğe göre)"), bar_list(ScenarioState.rows, "ad", "co2p", "co2t")),
                    columns=rx.breakpoints(initial="1", md="2"), spacing="3", width="100%",
                ),
                panel(rx.vstack(
                    eyebrow("Akıllı yönetim boşa giden enerjiyi azaltır"),
                    meter("Basit kural · yılda boşa giden", S["cut_basic"], S["cut_basic_pct"], dim=True),
                    meter("Akıllı yönetim · yılda boşa giden", S["cut_smart"], S["cut_smart_pct"]),
                    rx.text("Fark: " + S["cut_drop"], size="2", weight="bold", class_name="mono ink"),
                    spacing="3", width="100%")),
                panel(rx.plotly(data=ScenarioState.fig_monthly, width="100%")),
                rx.heading("Bölgeler (her biri kendi ilçesinin ihtiyacı için)", size="4"),
                panel(eyebrow("Batarya olmadan ihtiyacın saat saat karşılanan kısmı"),
                      bar_list(ScenarioState.compare, "bolge", "s3v", "s3", note_key="kisit")),
                rx.heading("Hangi kapasitede? (önerilen santralin katları, en düşük net maliyetli 8 tasarım)", size="4"),
                dict_table(ScenarioState.sweep, [
                    ("pv", "Güneş"), ("wind", "Rüzgâr"), ("batt", "Batarya"), ("oz", "İhtiyacın karşılanan kısmı"),
                    ("kisilan", "Kısılan"), ("yatirim", "Yatırım"), ("net", "Yıllık net maliyet")]),
                rx.el.details(
                    rx.el.summary(rx.text("Tüm değerler (tablo)", as_="span", weight="medium"),
                                  style={"cursor": "pointer"}),
                    rx.vstack(
                        dict_table(ScenarioState.rows, [
                            ("kod", "Kod"), ("ad", "Senaryo"), ("uretim", "Üretim"),
                            ("acik", "Enerji açığı"), ("verilen", "Diğer ilçelere"),
                            ("kisilan", "Kısılan"), ("oz", "Karşılanan"),
                            ("dalga", "Dalgalanma (CV)"), ("sifir", "Üretimsiz saat"),
                            ("yatirim", "Yatırım"), ("geri", "Geri ödeme"), ("co2", "CO₂ t/yıl")]),
                        dict_table(ScenarioState.compare, [
                            ("bolge", "Bölge"), ("kisit", "Uygunluk · ilçe"), ("s1", "S1 güneş"),
                            ("s3", "S3 hibrit"), ("s4", "S4 bataryalı"), ("kisilan", "Kısılan: basit → akıllı")]),
                        spacing="3", padding_top="8px", width="100%"),
                    width="100%",
                ),
                rx.text(ScenarioState.note, " · İhtiyaç: ilçe nüfusu × kişi başı tüketim (2011 resmî verilerinden). "
                        "Santral, seçili noktanın verimine ve uygunluğuna göre boyutlanır; fazla üretim o saatteki "
                        "KKTC'nin geri kalanının ihtiyacı kadar diğer ilçelere verilebilir. Maliyetler Ayarlar > "
                        "Gelişmiş'teki santral ölçeği varsayımlarıdır. Akıllı yönetim simülasyonda kusursuz tahmin "
                        "varsayar.", size="1", class_name="muted"),
                spacing="4", width="100%",
            ),
        ),
        back=("Veriler", "/veriler"),
        title="Senaryolar ve doğrulama",
    )
