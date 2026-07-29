"""Kural tabanli urun oneri motoru (Sprint 1 - Sila).

Neden kural tabanli (GBDT'den once)?
  - Hedef urunlerimiz (domates/biber/patates + yoresel) icin dogrudan calisir;
    hazir Kaggle veri seti Hindistan urunlerini kapsar, bunlari icermez.
  - Tamamen aciklanabilir: her urun icin hangi faktorun ne kadar puan verdigini
    dondururuz (rubric: aciklanabilirlik puani). Grad-CAM'in tablo karsiligi.
  - SoilData + ClimateData disinda dis bagimlilik yok; her zaman cevap uretir.

GBDT (train_gbdt.py) veri seti indirilince ikinci bir gorus olarak eklenir;
bu motor birincil ve guvenli yol olarak kalir.

Skorlama: her agronomik faktor icin trapez uyelik fonksiyonu (0..1).
Toplam skor = agirlikli ortalama * 100. Sadece verili faktorler hesaba katilir
(eksik veri cezalandirmaz, agirliktan dusulur).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from core.schemas import ClimateData, SoilData

_KB_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge" / "crop_params.yaml"

# Faktor agirliklari (toplami serbest; oransal kullanilir)
_WEIGHTS = {"ph": 1.0, "sicaklik": 1.0, "yagis": 0.8, "azot": 0.6, "doku": 0.6}


@lru_cache(maxsize=1)
def load_knowledge_base() -> dict:
    """crop_params.yaml'i okur ve onbelleğe alir."""
    with _KB_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _trapezoid(x: float, band: dict) -> float:
    """Trapez uyelik: opt araliginda 1.0, min/max'ta 0.0, arada dogrusal."""
    lo, omin, omax, hi = band["min"], band["opt_min"], band["opt_max"], band["max"]
    if x <= lo or x >= hi:
        return 0.0
    if omin <= x <= omax:
        return 1.0
    if x < omin:
        return (x - lo) / (omin - lo)
    return (hi - x) / (hi - omax)


def _texture_class(soil: SoilData) -> str | None:
    """Kil/kum/silt yuzdesinden basit USDA doku sinifi (recommender esleme icin)."""
    if soil.clay is None or soil.sand is None or soil.silt is None:
        return None
    clay, sand, silt = soil.clay, soil.sand, soil.silt
    if clay >= 40:
        return "kil"
    if sand >= 70:
        return "kum"
    if sand >= 50 and clay < 20:
        return "kumlu_tin"
    if clay >= 27:
        return "killi_tin"
    if silt >= 50:
        return "siltli_tin"
    return "tin"


def _score_crop(crop: dict, soil: SoilData, climate: ClimateData) -> tuple[float, list[dict]]:
    """Tek urun icin agirlikli skor (0..100) ve faktor kirilimini dondurur."""
    factors: list[dict] = []
    total_w = 0.0
    total_s = 0.0

    checks = [
        ("ph", "pH", soil.ph, crop.get("ph")),
        ("sicaklik", "Sıcaklık", climate.temperature, crop.get("sicaklik")),
        ("yagis", "Yağış/su", climate.rainfall, crop.get("yagis_mm")),
        ("azot", "Azot", soil.nitrogen, crop.get("azot_g_kg")),
    ]
    for key, label, value, band in checks:
        if value is None or band is None:
            continue
        m = _trapezoid(value, band)
        w = _WEIGHTS[key]
        total_w += w
        total_s += w * m
        factors.append({"faktor": label, "deger": round(value, 2), "uyum": round(m, 2)})

    # Doku uyumu (kategorik)
    tex = _texture_class(soil)
    pref = crop.get("doku")
    if tex is not None and pref:
        m = 1.0 if tex in pref else 0.4
        w = _WEIGHTS["doku"]
        total_w += w
        total_s += w * m
        factors.append({"faktor": "Doku", "deger": tex, "uyum": round(m, 2)})

    score = (total_s / total_w * 100) if total_w else 0.0
    return round(score, 1), factors


def recommend(
    soil: SoilData,
    climate: ClimateData,
    top_k: int = 3,
) -> list[dict]:
    """Toprak + iklime gore uygun urunleri sirali dondurur.

    Donen her oge: {urun, ad, skor, uygunluk, faktorler, sezon, not}
    faktorler her agronomik faktorun uyum katkisini icerir (aciklanabilirlik).
    """
    kb = load_knowledge_base()
    results = []
    for key, crop in kb.items():
        score, factors = _score_crop(crop, soil, climate)
        results.append(
            {
                "urun": key,
                "ad": crop.get("ad", key),
                "skor": score,
                "uygunluk": _label(score),
                "faktorler": factors,
                "sezon": crop.get("sezon", ""),
                "not": crop.get("notlar", ""),
            }
        )
    results.sort(key=lambda r: r["skor"], reverse=True)
    return results[:top_k]


def _label(score: float) -> str:
    if score >= 75:
        return "Çok uygun"
    if score >= 55:
        return "Uygun"
    if score >= 35:
        return "Sınırlı uygun"
    return "Uygun değil"
