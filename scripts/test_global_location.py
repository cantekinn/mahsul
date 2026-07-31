"""Kuresel konum katmanini 6 kitadan gercek noktalarla olcer.

Neden var: katmanin "calisiyor" demesi yetmez, HANGI kaynagin nerede bos
dondugunu sayiyla bilmemiz lazim. Cikti bir kapsama tablosudur.

Noktalar bilerek zor secildi:
  - Antalya    : bilinen iyi durum (referans)
  - Pencap     : SoilGrids komsularda da bos donmustu
  - Sao Paulo  : OSM'de parsel yok, toprak 5. komsuda bulunmustu
  - Iowa       : yogun tarim, her katman dolu olmali
  - Nakuru     : Afrika, toprak 1. komsuda
  - Riverina   : Avustralya
  - Akdeniz    : okyanus noktasi, karada=False donmeli

Calistirma: py -m scripts.test_global_location
"""
from __future__ import annotations

import time

from data.global_location import konum_ozeti, rastgele_tarim_noktasi

NOKTALAR = [
    ("Antalya (TR)", 36.92, 30.83),
    ("Pencap (IN)", 30.90, 75.85),
    ("Sao Paulo (BR)", -21.17, -47.81),
    ("Iowa (US)", 42.03, -93.63),
    ("Nakuru (KE)", -0.30, 36.08),
    ("Riverina (AU)", -34.75, 146.05),
    ("Akdeniz ortasi", 35.00, 18.00),
]


def _satir(ad: str, o, sn: float) -> str:
    t = "-" if o.toprak is None else "var"
    if o.toprak is not None and o.toprak_kaynak_mesafe_km:
        t = f"{o.toprak_kaynak_mesafe_km} km"
    i = "-" if o.iklim is None else f"{o.iklim.temperature}C"
    y = "-" if o.yukselti_m is None else f"{o.yukselti_m:.0f}m"
    k = "kara" if o.karada else "DENIZ"
    # Parsel sutunu: sunucu cevap vermediyse sayi yerine "?" yazariz.
    p = str(len(o.parseller)) if o.parsel_durum in ("ok", "sorgulanmadi") else "?"
    return f"{ad:16s} {k:5s} {y:>7s} {t:>8s} {i:>8s} {p:>7s} {sn:7.1f}s"


def main() -> None:
    print(f"{'nokta':16s} {'yer':5s} {'yukselti':>7s} {'toprak':>8s} "
          f"{'iklim':>8s} {'parsel':>7s} {'sure':>8s}")
    print("-" * 72)

    ozetler = []
    for ad, lat, lon in NOKTALAR:
        t0 = time.time()
        o = konum_ozeti(lat, lon)
        sn = time.time() - t0
        ozetler.append((ad, o))
        print(_satir(ad, o, sn))

    print("\nEKSIK KATMANLAR (durustce raporlanan):")
    for ad, o in ozetler:
        if o.eksik:
            print(f"  {ad:16s} {', '.join(o.eksik)}")

    # Onbellek gercekten ise yariyor mu? Ayni noktayi tekrar sor.
    t0 = time.time()
    konum_ozeti(36.92, 30.83, parsel_ara=False)
    print(f"\nOnbellek testi (Antalya, parselsiz tekrar): {time.time() - t0:.1f}s")

    print("\nRASTGELE NOKTA:")
    t0 = time.time()
    r = rastgele_tarim_noktasi(tohum=7)
    print(f"  {r.lat}, {r.lon} -> {r.ulke} | {r.yer_adi}")
    print(f"  yukselti {r.yukselti_m} m, parsel {len(r.parseller)}, "
          f"sure {time.time() - t0:.1f}s")
    if r.toprak:
        print(f"  toprak pH {r.toprak.ph}, kil {r.toprak.clay}%, kum {r.toprak.sand}%")
    if r.eksik:
        print(f"  eksik: {', '.join(r.eksik)}")


if __name__ == "__main__":
    main()
