"""Iklim risk kural motoru (Sprint 2).

MAKINE OGRENMESI DEGIL: hava tahminini (Open-Meteo) urune ozel agronomik
esiklerle karsilastiran seffaf kural motoru. Hava tahminini biz uretmeyiz;
katma deger, tahmini urune ozel RISK'e cevirmektir (don/sicak/yagis/kuraklik).

Esikler crop_params.yaml'daki sicaklik trapezinden turetilir:
  min < opt_min < opt_max < max
Ideal aralik [opt_min, opt_max]; [opt_max, max] arasi hafif stres, max ustu
gercek stres. Boylece ayni sicak dalgasi her urunde FARKLI risk uretir
(patates max=28 ile zeytin max=40 ayni 35 C'ye ayni tepkiyi vermez).

Ek olarak GUN SAYISI (siddet) hesaplanir ve donemin buyuk kismi urunun ust/alt
sinirini asiyorsa UYGUNLUK karari verilir: surekli yuksek risk demek, o urunun
o donem/bolge icin uygun olmadigi demektir.
"""
from __future__ import annotations

# don hassasiyeti yuksek urunler (subtropik/sicak sever)
_FROST_SENSITIVE = {"narenciye", "muz", "biber", "domates"}


def _count(vals: list[float], pred) -> int:
    return sum(1 for v in vals if pred(v))


def _gun_ifade(gun: int, toplam: int) -> str:
    """'3 gün (16 günün)' gibi siddet ifadesi."""
    return f"{gun}/{toplam} gün"


def assess_climate_risk(
    tmins: list[float],
    tmaxs: list[float],
    precs: list[float],
    crop_key: str | None = None,
    crop_params: dict | None = None,
) -> list[dict]:
    """Tahmin serisinden urune ozel risk listesi uretir.

    Her risk: {tur, seviye (yuksek/orta/dusuk), aciklama}
    crop_params verilirse urune ozel sicaklik trapezi (min/opt_min/opt_max/max)
    kullanilir; gun sayisi ile siddet ve uygunluk karari eklenir.
    """
    if not tmins or not tmaxs:
        return []

    n = len(tmaxs)
    tmin_min = min(tmins)
    tmax_max = max(tmaxs)
    prec_total = sum(precs) if precs else 0.0
    prec_max = max(precs) if precs else 0.0

    sic = (crop_params or {}).get("sicaklik", {})
    cold_min = sic.get("min")
    opt_min = sic.get("opt_min")
    opt_max = sic.get("opt_max")
    hot_max = sic.get("max")
    sensitive = crop_key in _FROST_SENSITIVE if crop_key else False

    risks: list[dict] = []

    # --- Don / soguk stresi ---
    frost_days = _count(tmins, lambda t: t <= 0)
    if frost_days:
        risks.append({"tur": "don", "seviye": "yuksek",
                      "aciklama": f"En düşük {tmin_min:.1f} °C, {_gun_ifade(frost_days, n)} donlu: "
                                  "örtü veya sulama ile koruma şart."})
    elif tmin_min <= 4 and sensitive:
        risks.append({"tur": "don", "seviye": "orta",
                      "aciklama": f"En düşük {tmin_min:.1f} °C: soğuğa hassas ürün için soğuk/don riski."})
    elif cold_min is not None:
        cold_days = _count(tmins, lambda t: t < cold_min)
        if cold_days:
            seviye = "orta" if cold_days < n / 2 else "yuksek"
            risks.append({"tur": "soguk", "seviye": seviye,
                          "aciklama": f"{_gun_ifade(cold_days, n)} gece {cold_min} °C alt sınırının altında "
                                      f"(en düşük {tmin_min:.1f} °C): gelişim yavaşlar."})

    # --- Sicak stresi (opt_max ustu hafif, max ustu gercek stres) ---
    if hot_max is not None and opt_max is not None:
        hot_days = _count(tmaxs, lambda t: t >= hot_max)
        warm_days = _count(tmaxs, lambda t: opt_max <= t < hot_max)
        if hot_days:
            # siddet: donemin yarisi ya da +3 C asim -> yuksek
            seviye = "yuksek" if (hot_days >= n / 2 or tmax_max >= hot_max + 3) else "orta"
            risks.append({"tur": "sicak", "seviye": seviye,
                          "aciklama": f"{_gun_ifade(hot_days, n)} ürünün {hot_max} °C üst sınırını aşıyor "
                                      f"(en yüksek {tmax_max:.1f} °C): çiçek/meyve dökümü ve verim kaybı riski."})
        elif warm_days:
            risks.append({"tur": "sicak", "seviye": "orta",
                          "aciklama": f"{_gun_ifade(warm_days, n)} ideal aralığın ({opt_max} °C) üstünde "
                                      f"(en yüksek {tmax_max:.1f} °C): gölgeleme ve sulamayı artırın."})
    elif hot_max is None and tmax_max >= 40:
        risks.append({"tur": "sicak", "seviye": "yuksek",
                      "aciklama": f"En yüksek sıcaklık {tmax_max:.1f} °C: aşırı sıcak."})

    # --- Asiri yagis / mantar baskisi ---
    heavy_rain_days = _count(precs, lambda p: p >= 30) if precs else 0
    wet_days = _count(precs, lambda p: 15 <= p < 30) if precs else 0
    if heavy_rain_days:
        risks.append({"tur": "yagis", "seviye": "yuksek",
                      "aciklama": f"{_gun_ifade(heavy_rain_days, n)} 30 mm üstü yağış "
                                  f"(en fazla {prec_max:.0f} mm/gün): sel/erozyon ve mantar hastalığı baskısı."})
    elif wet_days:
        risks.append({"tur": "yagis", "seviye": "orta",
                      "aciklama": f"{_gun_ifade(wet_days, n)} 15-30 mm yağış: nemli koşul, mantar hastalıklarını izleyin."})

    # --- Kuraklik / su stresi ---
    if prec_total < 2 and tmax_max >= 30:
        risks.append({"tur": "kuraklik", "seviye": "orta",
                      "aciklama": "Dönem boyunca kayda değer yağış yok ve sıcaklık yüksek: "
                                  "su stresi var, sulama planı şart."})

    # --- Uygunluk karari: donemin buyuk kismi urunun sinirini asiyorsa ---
    if hot_max is not None:
        hot_days = _count(tmaxs, lambda t: t >= hot_max)
        if hot_days >= 0.6 * n:
            risks.append({"tur": "uygunluk", "seviye": "yuksek",
                          "aciklama": f"Günlerin çoğu ({_gun_ifade(hot_days, n)}) üst sıcaklık sınırının üstünde: "
                                      "bu ürün bu dönemde açık alan için uygun değil, örtü altı/gölge ya da farklı "
                                      "sezon gerekir."})
    if sensitive and frost_days >= 0.3 * n:
        risks.append({"tur": "uygunluk", "seviye": "yuksek",
                      "aciklama": f"Soğuğa hassas ürün ve {_gun_ifade(frost_days, n)} donlu: "
                                  "bu dönemde açık alanda yetiştirmek riskli, uygun değil."})

    if not risks:
        risks.append({"tur": "genel", "seviye": "dusuk",
                      "aciklama": "Önümüzdeki dönemde bu ürün için belirgin bir iklim riski görünmüyor, koşullar uygun."})
    return risks
