"""Yapay zekâ yatırımcı özeti: istem içeriği ve anahtarsız davranış (internet gerektirmez)."""
import asyncio

import pytest

from hibrit_enerji import ai_brief

D = {
    "kpi": {"yf": "1.741", "yt": "2.404", "wa": "432", "wf": "165"},
    "restrict": {"label": "Yalnızca güneşe uygun", "wind_ok": "0", "solar_ok": "1"},
    "restrict_codes": [{"code": "R02", "short": "Yerleşime yakın", "name": "", "detail": ""}],
    "solar_rows": [{"k": "Sabit panel için en iyi eğim", "v": "33°"}],
    "wind_rows": [{"k": "Ortalama hız (100 m)", "v": "4,9 m/s"}],
    "hybrid_rows": [], "advice": ["Panelleri G yönüne 33° eğimle sabitleyin."],
    "techniques": [{"name": "Rüzgâr türbini", "status": "yasak", "note": "Kısıt: R02"}],
}


def test_prompt_carries_computed_values_and_restrictions():
    p = ai_brief.build_prompt("Dipkarpaz", D, {"kind": "Proje özeti aday bölgesi", "place": "Köy merkezi"})
    for s in ("Dipkarpaz", "1.741 kWh", "432 kWh", "rüzgâra uygun: hayır", "R02 Yerleşime yakın", "33°", "yasak"):
        assert s in p
    assert set(ai_brief.INPUT_KEYS) <= set(D)


def test_system_rules_forbid_invented_numbers_and_model_names():
    assert "uydurma" in ai_brief.SYSTEM and "veri kaynağı adı yazma" in ai_brief.SYSTEM
    assert "tesis" in ai_brief.SYSTEM


def test_missing_key_raises(monkeypatch):
    monkeypatch.setattr(ai_brief, "api_key", lambda: "")
    with pytest.raises(RuntimeError):
        asyncio.run(ai_brief.investor_brief("x", D))
