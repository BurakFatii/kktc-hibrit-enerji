"""Yatırımcı özeti: seçili noktanın hesaplanmış verilerini Gemini'ye (Google AI Studio) anlattırır.

Yapay zekâ hiçbir sayı üretmez; yalnızca services.site_report çıktısını yatırımcı diliyle yorumlar.
Anahtar ortam değişkeninden okunur (GEMINI_API_KEY), proje kökündeki .env dosyası da desteklenir.
.env gitignore'dadır; anahtarı koda yazma.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Sırayla denenir; biri hata verirse sonraki. GEMINI_MODEL ile başa model eklenebilir.
# Ölçüm (01.11.2026, ücretsiz katman): Pro modellerin kotası 0 (HTTP 429); gemini-3.8-flash ~100 sn;
# gemini-3.5-flash ~8 sn ve metin kalitesi yeterli -> ana model. Diğerleri yedek.
MODELS = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-3.5-flash-lite"]
TIMEOUT_S = 90.0
# services.site_report çıktısından kullanılan alanlar
INPUT_KEYS = ("kpi", "restrict", "restrict_codes", "solar_rows", "wind_rows", "hybrid_rows", "advice", "techniques")

_cache: dict[tuple, str] = {}


def _load_env() -> None:
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and not k.startswith("#"):
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key() -> str:
    _load_env()
    return os.environ.get("GEMINI_API_KEY", "")


def models() -> list[str]:
    extra = os.environ.get("GEMINI_MODEL", "").strip()
    return ([extra] if extra else []) + [m for m in MODELS if m != extra]


SYSTEM = """Sen Kuzey Kıbrıs'ta (KKTC) yenilenebilir enerji yatırımlarına danışmanlık yapan bir uzmansın.
Sana bir haritada seçilmiş noktanın HESAPLANMIŞ verileri verilecek. Görevin bu noktayı bir yatırımcıya
anlatmak: bu konumda bir yılda ne üretilir, hangi kurulum uygun, kurulum nasıl yapılmalı.

Kurallar:
- YALNIZCA verilen sayıları kullan; yeni sayı, fiyat, getiri oranı veya kaynak uydurma.
- Kısıt (uygunluk) bilgisine mutlaka uy: rüzgâra uygun değilse türbin önerme, güneşe uygun değilse
  panel önerme; ikisine de uygun değilse bunu açıkça söyle ve yakında uygun bir alan aramayı öner.
- "Ev/hane" deme, "tesis" de. Elektrikli araç önerme.
- Hava modeli veya veri kaynağı adı yazma; "geçmiş yılın saatlik verisi" de.
- Sade, güven veren, abartısız Türkçe. Teknik jargonu bir yatırımcının anlayacağı dile çevir.
- Biçim: 3 kısa paragraf, başlıksız, madde işaretsiz, toplam 150–220 kelime.
  1) Konumun potansiyeli (1 kW güneş ve 1 kW rüzgâr bir yılda ne üretir, hangisi öne çıkıyor).
  2) Önerilen kurulum (panel eğimi/yönü, türbin yönü, takipçi/otomatik yönlenme değer mi, kısıtlar).
  3) Yatırımcı için sonuç: güçlü yan, dikkat edilmesi gereken risk ve bir sonraki adım.
- Sayıları verildiği biçimde yaz (Türkçe ondalık virgül)."""


def build_prompt(label: str, d: dict, region: dict | None = None) -> str:
    """site_report çıktısından modele gidecek veri metni."""
    k, r = d["kpi"], d["restrict"]
    rows = lambda rs: "\n".join(f"- {x['k']}: {x['v']}" for x in rs)  # noqa: E731
    codes = "; ".join(f"{c['code']} {c['short']}" + (f" ({c['name']})" if c["name"] else "")
                      for c in d.get("restrict_codes", [])) or "yok"
    parts = [
        f"Seçili nokta: {label}",
        f"Uygunluk: {r['label']} · rüzgâra uygun: {'evet' if r['wind_ok'] == '1' else 'hayır'} · "
        f"güneşe uygun: {'evet' if r['solar_ok'] == '1' else 'hayır'} · kısıt kodları: {codes}",
        f"Bir yılda 1 kW sabit güneş paneli: {k['yf']} kWh; takipçili: {k['yt']} kWh",
        f"Bir yılda 1 kW otomatik yönlenen rüzgâr türbini: {k['wa']} kWh; sabit yönlü: {k['wf']} kWh",
        "Güneş verileri:\n" + rows(d["solar_rows"]),
        "Rüzgâr verileri:\n" + rows(d["wind_rows"]),
        "Güneş–rüzgâr birlikteliği:\n" + rows(d["hybrid_rows"]),
        "Uygulamanın hesapladığı kurulum önerileri:\n" + "\n".join(f"- {a}" for a in d["advice"]),
        "Uygulanabilir teknikler:\n" + "\n".join(f"- {t['name']}: {t['status']} — {t.get('note', '')}"
                                                 for t in d.get("techniques", [])),
    ]
    if region:
        parts.insert(1, f"Bölge bilgisi: {region.get('kind', '')} · {region.get('place', '')}"
                        + (f" · avantaj: {region['advantage']}" if region.get("advantage") else "")
                        + (f" · zorluk: {region['challenge']}" if region.get("challenge") else ""))
    return "\n\n".join(parts)


async def investor_brief(label: str, d: dict, region: dict | None = None) -> str:
    """Yatırımcı metnini döndürür. Anahtar yoksa / tüm modeller başarısızsa RuntimeError."""
    key = api_key()
    if not key:
        raise RuntimeError("Yapay zekâ anahtarı tanımlı değil (GEMINI_API_KEY).")
    prompt = build_prompt(label, d, region)
    ck = (prompt,)
    if ck in _cache:
        return _cache[ck]
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 4096,
                             "thinkingConfig": {"thinkingLevel": "low"}},
    }
    last = ""
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for m in models():
            try:
                res = await client.post(API.format(model=m), json=body, headers={"x-goog-api-key": key})
            except httpx.HTTPError as e:
                last = f"{m}: {type(e).__name__}"
                continue
            if res.status_code != 200:
                last = f"{m}: HTTP {res.status_code}"
                continue
            data = res.json()
            parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
            if text:
                _cache[ck] = text
                return text
            last = f"{m}: boş yanıt"
    raise RuntimeError(f"Yapay zekâ yanıt vermedi ({last}).")
