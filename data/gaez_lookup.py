"""FAO GAEZ v4 Suitability Index lookup for a given (lat, lon, urun).

NEDEN: EcoCrop trapezoid tek basina puani 90-100 arasina sikistirir cunku
optimum bandi bir plato; band icine dusen her deger 1.00 alir. GAEZ v4 zaten
iklim + toprak + su butcesini birlestirmis "gold standard" bir uygunluk
gridini bu sikismay1 kirmak icin kalibrator olarak kullaniyoruz.

BOLGE: Turkiye + tarim komsulari (20-48 E, 33-44 N). Global GAEZ yok, bbox
disindaki noktalar icin None doner (skor sadece EcoCrop olur).

CIKTI FORMATI: 0-100 arasi float (Suitability Index extended 0-10000 /100).
sxHi = irrigated, sxHr = rainfed. Su rejimi otomatik ise yagis ile secilir:
yillik yagis, urun opt_min yagisinin >= ise rainfed, degilse irrigated.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml


BURADA = Path(__file__).resolve().parent.parent
KNOWLEDGE = BURADA / "knowledge"
NPZ_YOLU = KNOWLEDGE / "gaez_tr.npz"
INDEX_YOLU = KNOWLEDGE / "gaez_index.json"
ESLEME_YOLU = KNOWLEDGE / "gaez_esleme.yaml"


@lru_cache(maxsize=1)
def _yukle() -> dict:
    """NPZ + index + esleme dosyalarini bir kez yukler (module-level cache)."""
    npz = np.load(NPZ_YOLU)
    with open(INDEX_YOLU, encoding="utf-8") as f:
        idx = json.load(f)
    with open(ESLEME_YOLU, encoding="utf-8") as f:
        esleme = yaml.safe_load(f)
    urun_kodlari = idx["urun_kodlari"]
    kod_to_slot = {k: i for i, k in enumerate(urun_kodlari)}
    # bbox: [lon_min, lat_min, lon_max, lat_max]
    lon_min, lat_min, lon_max, lat_max = idx["bbox"]
    H, W = idx["shape"]
    # affine transform (rasterio): [a, b, c, d, e, f] -> row col from lon lat
    a, b, c, d, e, f = idx["transform"][:6]
    return {
        "sxHi": npz["sxHi"],
        "sxHr": npz["sxHr"],
        "kod_to_slot": kod_to_slot,
        "esleme": esleme,
        "bbox": (lon_min, lat_min, lon_max, lat_max),
        "shape": (H, W),
        # ters affine: (lon, lat) -> (col, row); Turkiye bbox icin a>0, e<0
        "px_size_lon": a,   # 5' = 0.0833 deg
        "px_size_lat": -e,  # 5' = 0.0833 deg (pozitif)
        "origin_lon": c,    # bbox lon_min
        "origin_lat": f,    # bbox lat_max
    }


def _lat_lon_to_row_col(lat: float, lon: float, m: dict) -> tuple[int, int] | None:
    """Bbox disi None. Kenardaki noktayi clamp'e etmiyorum: gercekten disariysa
    kullanicinin GAEZ yok bilgisini almasi lazim."""
    lon_min, lat_min, lon_max, lat_max = m["bbox"]
    if not (lon_min <= lon < lon_max and lat_min < lat <= lat_max):
        return None
    col = int((lon - m["origin_lon"]) / m["px_size_lon"])
    row = int((m["origin_lat"] - lat) / m["px_size_lat"])
    H, W = m["shape"]
    if not (0 <= row < H and 0 <= col < W):
        return None
    return row, col


def gaez_verim(
    lat: float,
    lon: float,
    urun_key: str,
    su_rejimi: str = "otomatik",
    yagis_mm: float | None = None,
    urun_opt_min_yagis: float | None = None,
) -> dict | None:
    """Bir ürün icin GAEZ Suitability Index dondurur.

    urun_key: bizim kısa key (bugday, aycicegi, ...). Eslemede yoksa None.
    su_rejimi: 'rainfed' | 'irrigated' | 'otomatik'. otomatik ise yagis_mm ile
        urun_opt_min_yagis karsilastirilir; yagis yeterliyse rainfed, degilse
        irrigated. Ikisi de eksikse rainfed varsayilir.
    Donus: {'uygunluk_gaez': 0-100 float, 'su_rejimi': 'rainfed'|'irrigated'}
        veya None (eslemede yok / bbox disinda / GAEZ'de ilgili rejim yok).
    """
    m = _yukle()
    esleme = m["esleme"].get(urun_key)
    if esleme is None:
        return None
    gaez_kod = esleme["gaez"]
    slot = m["kod_to_slot"].get(gaez_kod)
    if slot is None:
        return None
    rc = _lat_lon_to_row_col(lat, lon, m)
    if rc is None:
        return None
    row, col = rc

    # Su rejimi secimi
    if su_rejimi == "otomatik":
        if yagis_mm is not None and urun_opt_min_yagis is not None:
            secilen = "rainfed" if yagis_mm >= urun_opt_min_yagis else "irrigated"
        else:
            secilen = "rainfed"
    else:
        secilen = su_rejimi

    # Sentinel -1: bu urun icin secilen rejim GAEZ'de yok, digerini dene
    arr = m["sxHi"] if secilen == "irrigated" else m["sxHr"]
    val = int(arr[slot, row, col])
    if val < 0:
        # secilen rejim yok, digerine fallback
        secilen = "rainfed" if secilen == "irrigated" else "irrigated"
        arr = m["sxHi"] if secilen == "irrigated" else m["sxHr"]
        val = int(arr[slot, row, col])
        if val < 0:
            return None

    return {"uygunluk_gaez": val / 100.0, "su_rejimi": secilen}


@lru_cache(maxsize=4096)
def _bolge_median_cached(row: int, col: int) -> float | None:
    """Bir hucrede tum 50 GAEZ urunu icin her iki rejimin ust degerlerinden
    olusan medyan. Konumun 'tarimsal uygunluk taban seviyesi'ni verir."""
    m = _yukle()
    vals = []
    for slot in range(m["sxHi"].shape[0]):
        hi = int(m["sxHi"][slot, row, col])
        hr = int(m["sxHr"][slot, row, col])
        v = max(hi, hr)
        if v >= 0:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    return (vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2) / 100.0


def gaez_bolge_prior(lat: float, lon: float) -> float | None:
    """Bu konumdaki 50 GAEZ urunun median uygunlugu (0-100).

    NEDEN: GAEZ 43/115 urunumuzu eslesiyor, geri kalan 72'ye direkt katkida
    bulunamiyor. Ecocrop yalniz kaldiginda o urunler 100'e cikip GAEZ katkili
    olanlari geriye itiyordu (Bursa'da kinoa/susam/mercimek ilk 5'e giriyor).
    Bu asimetriyi kirmak icin GAEZ eslesmeyen urune BOLGENIN TIPIK uygunlugu
    (median) prior olarak uygulanir. Bu bir tahmin degildir; bolgedeki 50
    urunun gercek median'idir. Konya gibi kurak yerde median dusuk cikar
    (~20) ve genel skorlari asagi ceker; Antalya'da yuksek cikar (~78) ve
    ilgili urunleri asagi cekmez. Ecocrop trapezoid'inin sikismis 90-100
    aralignini bolgesel gerceklikle dogal olarak acar."""
    m = _yukle()
    rc = _lat_lon_to_row_col(lat, lon, m)
    if rc is None:
        return None
    return _bolge_median_cached(rc[0], rc[1])
