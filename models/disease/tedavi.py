"""Model etiketi -> knowledge/treatments.yaml kaydi eslestirici.

treatments.yaml deseni: her kayit `anahtar: [<kelime>, ...]` icerir. Model
etiketi ('domates_erken_yaniklik' gibi) '_' -> boslugu ile ASCII sorgu diziye
cevrilir ve anahtar listelerinde EN UZUN eslesme aranir (kismi kelime
karisikligini onlemek icin).

Cikti: {ad, konak, belirti, dogal, kimyasal, korunma} veya None
  (saglikli, tanimsiz veya karsiligi bulunmayan etiketler icin).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_BURADA = Path(__file__).resolve().parent.parent.parent
_YAML = _BURADA / "knowledge" / "treatments.yaml"


@lru_cache(maxsize=1)
def _tedaviler() -> dict:
    """treatments.yaml'i bir kez okur. Her kayit icin normalize edilmis
    anahtar setini (ASCII, kucuk harf, boslukla) hazirlar."""
    with open(_YAML, encoding="utf-8") as f:
        ham = yaml.safe_load(f)
    hazir = {}
    for kod, kayit in ham.items():
        anahtar = kayit.get("anahtar") or []
        # Her anahtari kucuk harf + tek boslukla normalize et
        norm = [_normalize(a) for a in anahtar]
        hazir[kod] = {"kayit": kayit, "norm_anahtar": norm}
    return hazir


def _normalize(s: str) -> str:
    """Kucuk harf, birden fazla boslugu tek boslukla degistir."""
    return " ".join(s.lower().split())


def _ascii_varyant(model_etiket: str) -> str:
    """Model etiketi ('domates_erken_yaniklik') -> aranan ASCII dize
    ('domates erken yaniklik'). treatments.yaml anahtarlari zaten ASCII
    varyantlari iceriyor."""
    return model_etiket.replace("_", " ")


def tedavi_bul(model_etiket: str) -> dict | None:
    """Model etiketine karsi gelen tedavi kaydini dondurur.

    None doner:
    - 'diger' (hedef disi)
    - '<urun>_saglikli' (tedavi gereksiz)
    - treatments.yaml'da eslesme yok

    Cikti dict: {ad, konak, belirti, dogal, kimyasal, korunma} (ham yaml
    kaydi + gerekmeyen 'anahtar' field'i cikarilir).
    """
    if model_etiket == "diger" or model_etiket.endswith("_saglikli"):
        return None

    sorgu = _ascii_varyant(model_etiket)
    tedaviler = _tedaviler()

    # En uzun anahtar eslesmesini bul (ornek: "erken yaniklik" >
    # "yaniklik", ilki daha spesifik)
    en_iyi = None
    en_iyi_uzunluk = 0
    for kod, veri in tedaviler.items():
        for anahtar in veri["norm_anahtar"]:
            if anahtar in sorgu and len(anahtar) > en_iyi_uzunluk:
                en_iyi = veri["kayit"]
                en_iyi_uzunluk = len(anahtar)

    if en_iyi is None:
        return None

    return {
        "ad": en_iyi.get("ad", ""),
        "konak": en_iyi.get("konak", []),
        "belirti": en_iyi.get("belirti", ""),
        "dogal": en_iyi.get("dogal", ""),
        "kimyasal": en_iyi.get("kimyasal", ""),
        "korunma": en_iyi.get("korunma", ""),
    }
