"""GAEZ v4 Suitability Index rasterlerini Turkiye+komsular bbox'ine kesip
paketler.

NEDEN VSI CURL: GAEZ v4 GCS mirror'daki 102 tif dosyasi (51 crop x 2 rejim)
toplam ~420 MB. Ham indirmek yerine rasterio'nun /vsicurl/ arabirimi ile HTTP
range request kullaniyoruz; sadece Turkiye window'una denk gelen tile'lar
indirilir. Olculdu: dosya basi ~2 saniye, toplam 3-4 dakika, disk kullanimi 0.

NEDEN SADECE TURKIYE: kullanici karari (max performans TR, min diger). Global
15' katmani ~100 MB olur ve Render 512 MB tier'inde sikinti yaratir. Global
istekler EcoCrop ile devam eder, GAEZ sadece Turkiye bbox'inde devreye girer.

BBOX: 20-48 E, 33-44 N. 336x132 pixel/rejim/urun @ 5 arcminute.

CIKTI:
  knowledge/gaez_tr.npz  (compressed)
    - sxHi: int16 array shape (N, 132, 336)   irrigated suitability
    - sxHr: int16 array shape (N, 132, 336)   rainfed suitability
    - urun_kodlari: str array shape (N,)      GAEZ crop codes (whe, mze, ...)
  knowledge/gaez_index.json
    - bbox, shape, transform, urun_kodlari
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds


# GAEZ v4 51 urun kodu (8110H klasoru icerigi, sxHi/sxHr prefix)
URUNLER = [
    "alf", "ban", "bck", "brl", "bsg", "cab", "car", "chk", "cit", "coc",
    "cof", "con", "cot", "cow", "csv", "flx", "fml", "grd", "grm", "jtr",
    "mis", "mze", "nap", "oat", "olp", "olv", "oni", "pea", "phb", "pig",
    "pml", "rcd", "rcg", "rcw", "rsd", "rub", "rye", "sfl", "soy", "spo",
    "srg", "sub", "suc", "swg", "tea", "tob", "tom", "whe", "wpo", "yam",
]

# Turkiye + tarim komsulari (Balkan, Kibris, Levant, Kafkas eteklerini kapsar)
BBOX_LON_MIN, BBOX_LAT_MIN, BBOX_LON_MAX, BBOX_LAT_MAX = 20.0, 33.0, 48.0, 44.0

BASE = "https://storage.googleapis.com/gaez-v4-data/data/res05/CRUTS32/Hist/8110H"

BURADA = Path(__file__).resolve().parent.parent
KNOWLEDGE = BURADA / "knowledge"


def bir_urun_oku(prefix: str, urun: str) -> tuple[np.ndarray, tuple, tuple] | None:
    """VSI curl ile tek raster'in Turkiye window'unu okur.

    Donus: (array, transform, shape) veya None (dosya yok/hata).
    """
    url = f"/vsicurl/{BASE}/{prefix}_{urun}.tif"
    try:
        with rasterio.open(url) as src:
            win = from_bounds(BBOX_LON_MIN, BBOX_LAT_MIN,
                              BBOX_LON_MAX, BBOX_LAT_MAX, src.transform)
            a = src.read(1, window=win)
            trans = src.window_transform(win)
            return a.astype(np.int16), tuple(trans), a.shape
    except rasterio.RasterioIOError:
        return None


def ana() -> int:
    KNOWLEDGE.mkdir(exist_ok=True)
    t0 = time.time()

    # Referans transform + shape ilk basarili okumadan alinir.
    ref_trans: tuple | None = None
    ref_shape: tuple | None = None
    sxHi_map: dict[str, np.ndarray] = {}
    sxHr_map: dict[str, np.ndarray] = {}

    for i, urun in enumerate(URUNLER, 1):
        for prefix, hedef in (("sxHi", sxHi_map), ("sxHr", sxHr_map)):
            sonuc = bir_urun_oku(prefix, urun)
            if sonuc is None:
                print(f"  [{i:>2}/{len(URUNLER)}] {prefix}_{urun}: YOK", flush=True)
                continue
            a, trans, shape = sonuc
            if ref_trans is None:
                ref_trans, ref_shape = trans, shape
            elif shape != ref_shape:
                print(f"  UYARI: {prefix}_{urun} shape {shape} != referans {ref_shape}",
                      flush=True)
                continue
            hedef[urun] = a
        gecen = time.time() - t0
        print(f"  [{i:>2}/{len(URUNLER)}] {urun} tamam ({gecen:.1f}s)", flush=True)

    if ref_shape is None:
        print("HATA: hicbir raster okunamadi", file=sys.stderr)
        return 1

    # NEDEN UNION: sxHi (irrigated) 29 urun, sxHr (rainfed) 50 urun. Intersection
    # alsak mze/whe/oat/tom gibi kritik urunler duser. Union alip eksik yaninda
    # sentinel -1 dolduruyoruz; runtime'da mevcut rejimi secer.
    ortak = sorted(set(sxHi_map) | set(sxHr_map))
    if not ortak:
        print("HATA: hicbir urun okunamadi", file=sys.stderr)
        return 1

    N, H, W = len(ortak), ref_shape[0], ref_shape[1]
    sxHi_arr = np.full((N, H, W), -1, dtype=np.int16)
    sxHr_arr = np.full((N, H, W), -1, dtype=np.int16)
    for k, urun in enumerate(ortak):
        if urun in sxHi_map:
            sxHi_arr[k] = sxHi_map[urun]
        if urun in sxHr_map:
            sxHr_arr[k] = sxHr_map[urun]

    # NPZ (compressed) + index JSON
    npz_yolu = KNOWLEDGE / "gaez_tr.npz"
    idx_yolu = KNOWLEDGE / "gaez_index.json"

    np.savez_compressed(npz_yolu,
                        sxHi=sxHi_arr,
                        sxHr=sxHr_arr,
                        urun_kodlari=np.array(ortak))
    npz_kb = npz_yolu.stat().st_size / 1024

    meta = {
        "bbox": [BBOX_LON_MIN, BBOX_LAT_MIN, BBOX_LON_MAX, BBOX_LAT_MAX],
        "shape": [H, W],
        "transform": list(ref_trans),
        "urun_kodlari": ortak,
        "kaynak": "GAEZ v4, CRUTS32 baseline 1981-2010, high input",
        "skala": "0-10000 (Suitability Index extended); 100'e bolununce 0-100",
        "olcum_tarihi": time.strftime("%Y-%m-%d"),
        "lisans": "CC BY 4.0 - FAO+IIASA GAEZ v4",
    }
    idx_yolu.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    gecen = time.time() - t0
    print(f"\nOK  {len(ortak)} urun, sekil {H}x{W}, {npz_kb:.1f} KB")
    print(f"OK  npz: {npz_yolu}")
    print(f"OK  index: {idx_yolu}")
    print(f"OK  toplam sure: {gecen:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(ana())
