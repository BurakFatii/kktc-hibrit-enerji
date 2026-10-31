# KKTC Hibrit Enerji (Güneş-takipçi + Rüzgar + Depolama + EV)

Hane ve orta ölçekli tüketiciye (ev, market, otel, ofis) yönelik:
üret → depola → tüket, şebekeye destek opsiyonel.

## Ücretsiz veri: Open-Meteo
- Anahtar yok, kota yok, KKTC koordinatlarıyla çalışır.
- Uç: `https://api.open-meteo.com/v1/forecast`
- Konumlar `src/config.py` içindedir (Lefkoşa varsayılan).

## Kurulum (proje içi ortam)
```bash
cd kktc-hibrit-enerji
uv venv || python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Yapı
```
app.py              # minimal panel
src/config.py       # KKTC konumları + varsayılan boyutlar
src/meteo.py        # Open-Meteo istemcisi
src/energy.py       # güneş (takipçi) + rüzgar hesabı
src/battery.py      # ev bataryası + yüzde
src/modes.py        # çalışma modu önerisi (depolama öncelikli)
docs/elektrik-mimari.md  # şematik elektrik yapısı
```

Rust EMS (elektriksel yazılım) sonraki aşamadır; bu panel onun
göstereceği verilerin prototipidir.
