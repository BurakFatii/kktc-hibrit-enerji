"""Ortak arayüz parçaları — düz, gölgesiz; neon + siyah/beyaz."""
from __future__ import annotations

import reflex as rx

from .state import AppState
from .viz import eyebrow, level3, panel

NAV = [
    ("Ana Sayfa", "/"),
    ("Veriler", "/veriler"),
    ("Ayarlar", "/ayarlar"),
    ("Nasıl Çalışır", "/nasil-calisir"),
]


def _nav_link(label: str, href: str, active: bool) -> rx.Component:
    return rx.link(
        label, href=href, size="2", weight="medium", underline="none",
        style={"color": "var(--fg)" if active else "var(--muted)",
               "borderBottom": "2px solid var(--neon)" if active else "2px solid transparent",
               "paddingBottom": "4px"},
    )


def navbar(nav: str = "") -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.link(
                rx.hstack(
                    rx.box(width="10px", height="10px", background="var(--neon)"),
                    rx.text("KKTC HİBRİT ENERJİ", size="2", weight="bold", class_name="mono",
                            style={"letterSpacing": ".06em", "color": "var(--fg)"}),
                    align="center", spacing="2",
                ),
                href="/", underline="none",
            ),
            rx.hstack(*[_nav_link(l, h, h == nav) for l, h in NAV], spacing="5", wrap="wrap"),
            rx.spacer(),
            rx.hstack(
                rx.icon("map-pin", size=13, color="var(--muted)"),
                rx.text(AppState.loc_text, size="1", class_name="mono muted"),
                rx.color_mode.button(size="1", variant="ghost"),
                align="center", spacing="2",
            ),
            align="center", spacing="6", wrap="wrap", width="100%",
        ),
        padding_x="1.25rem", padding_y="0.8rem",
        border_bottom="1px solid var(--line)", background="var(--bg)",
        position="sticky", top="0", z_index="10", width="100%",
    )


def page(*children, title: str, subtitle: str = "", back: tuple[str, str] | None = None,
         nav: str = "") -> rx.Component:
    return rx.box(
        navbar(nav or (back[1] if back else "")),
        rx.container(
            rx.vstack(
                rx.link(rx.hstack(rx.icon("arrow-left", size=14), rx.text(back[0]), spacing="1", align="center"),
                        href=back[1], size="1", underline="none", style={"color": "var(--muted)"})
                if back else rx.fragment(),
                rx.vstack(
                    rx.heading(title, size="7", weight="bold"),
                    rx.text(subtitle, size="2", class_name="muted") if subtitle else rx.fragment(),
                    spacing="1",
                ),
                rx.cond(
                    AppState.loc_status == "yedek",
                    rx.box(rx.hstack(rx.icon("triangle-alert", size=14), rx.text(AppState.loc_note, size="1"),
                                     spacing="2", align="center"),
                           class_name="panel", style={"borderColor": "var(--muted)", "padding": "8px 12px"}),
                ),
                *children,
                spacing="5", width="100%", padding_y="1.5rem",
            ),
            size="4",
        ),
        min_height="100vh", background="var(--bg)",
    )


def section(title: str, tag: str, *children, href: str | None = None, more: str = "Tümünü göster") -> rx.Component:
    """Veriler sayfası bölümü: başlık + 'Tümünü göster' + içerik."""
    return rx.vstack(
        rx.hstack(
            rx.vstack(eyebrow(tag), rx.heading(title, size="5"), spacing="0"),
            rx.spacer(),
            rx.link(rx.button(more, rx.icon("arrow-right", size=14), variant="outline", size="2"),
                    href=href, underline="none") if href else rx.fragment(),
            width="100%", align="end",
        ),
        *children,
        spacing="3", width="100%", padding_top="0.5rem",
    )


def kv_table(rows, title: str) -> rx.Component:
    return panel(
        rx.vstack(
            eyebrow(title),
            rx.foreach(rows, lambda r: rx.hstack(
                rx.text(r["k"], size="2", class_name="muted"), rx.spacer(),
                rx.text(r["v"], size="2", weight="medium", text_align="right", class_name="mono"),
                width="100%", border_bottom="1px solid var(--line)", padding_y="0.35rem")),
            spacing="1", width="100%",
        ),
    )


def error_box(msg) -> rx.Component:
    return rx.cond(msg != "", rx.box(rx.hstack(rx.icon("circle-x", size=14), rx.text(msg, size="2"),
                                               spacing="2", align="center"),
                                     class_name="panel", style={"borderColor": "var(--fg)"}))


def loading_line(flag, text: str = "Hesaplanıyor…") -> rx.Component:
    return rx.cond(flag, rx.hstack(rx.spinner(size="2"), rx.text(text, size="2", class_name="muted"),
                                   align="center"))


def status_badge(status) -> rx.Component:
    return rx.hstack(level3(status),
                     rx.text(status, size="1", class_name="mono",
                             style={"color": rx.cond(status == "yasak", "#ff3b30", "var(--muted)")}),
                     spacing="2", align="center")
