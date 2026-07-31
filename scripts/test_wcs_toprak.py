"""SoilGrids WCS yedeginin DOGRULUGUNU olcer.

Neden gerekli: rest.isric.org (REST API) kapali. Ayni verinin ikinci kapisi
maps.isric.org (WCS) acik. Ama "acik olmasi" yetmez, AYNI SAYIYI verdigini
gostermek gerekir. Bu test, REST calisirken diske yazilmis onbellek
degerlerini WCS'ten yeniden cekip birebir karsilastirir.

Calistirma: py -m scripts.test_wcs_toprak
"""
from __future__ import annotations

import glob
import json
import sys
import time

from data.soilgrids_wcs import wcs_toprak_al

# Onbellekteki her nokta REST doneminde alinmis GERCEK degerdir.
ONBELLEK = "data/_onbellek/toprak/*.json"

# ESIK NEDEN BU KADAR DAR (yuvarlama hatasi kadar):
# Ilk calistirmada 9 noktanin 6'sinda alti ozelligin hepsinde sapma TAM SIFIR
# cikti. Sapan 3 nokta ise tam olarak REST'in mesafe_km > 0 yazdigi noktalar,
# yani REST o noktada deger bulamayip 2.2 / 7.3 / 7.6 km oteden okumus olan
# noktalar. Yani sapmanin kaynagi WCS'in yanlis okumasi DEGIL, iki surumun
# FARKLI KOORDINATI okumasi. Bu yuzden karsilastirma sadece REST'in tam
# pikseli okudugu (mesafe_km == 0) noktalarda yapilir ve orada esitlik
# beklenir. Kaymis noktalar bilgi amacli ayrica raporlanir.
ESIK = 0.05
ALANLAR = ["ph", "clay", "sand", "silt", "organic_carbon", "nitrogen"]

# ONBELLEK ANAHTARI YUVARLIDIR. Dosya adi "{lat:.2f}_{lon:.2f}" oldugu icin
# REST'in sordugu GERCEK koordinat bu adin +-0.005 derecelik kutusu icinde
# herhangi bir yer olabilir. 0.005 derece ~ 550 m, SoilGrids pikseli ise 250 m;
# yani yuvarlama tek basina piksel degistirmeye yeter. Olctuk: uyusmayan tek
# nokta (-30.42, -61.63) icin kutu tarandiginda 222 m kuzeydeki piksel REST'in
# yazdigi degerin (kil 32.9, organik karbon 23.9) TAM AYNISINI verdi. Bu yuzden
# bir nokta uyusmazsa hemen hata sayilmaz, once kutu taranir.
KUTU = [-0.004, -0.002, 0.0, 0.002, 0.004]


def _kutu_tara(lat: float, lon: float, rest: dict) -> str | None:
    """Yuvarlama kutusunda REST degerinin TAMAMINI veren nokta var mi?

    Sadece uyusmazlik ciktiginda calisir. Amaci farki bahane etmek degil,
    farkin sebebini KANITLAMAK: eger kutu icinde alti ozelligin altisini da
    birebir tutturan bir piksel varsa, sapma WCS'in yanlis okumasindan degil
    onbellek anahtarinin yuvarlanmasindan gelmistir.
    """
    for dla in KUTU:
        for dlo in KUTU:
            t, _m, _d = wcs_toprak_al(lat + dla, lon + dlo)
            if t is None:
                continue
            if all(abs(rest[a] - getattr(t, a)) <= ESIK
                   for a in ALANLAR if rest.get(a) is not None):
                return f"({lat + dla:.3f}, {lon + dlo:.3f})"
    return None


def main() -> None:
    sapmalar: dict[str, list[float]] = {}
    sureler: list[float] = []
    hatalar: list[str] = []
    kaymis: list[str] = []
    bos = 0

    dosyalar = sorted(glob.glob(ONBELLEK))
    print(f"{len(dosyalar)} onbellek noktasi WCS ile yeniden sorgulaniyor\n")

    for yol in dosyalar:
        ad = yol.replace("\\", "/").split("/")[-1][:-5]
        lat, lon = (float(x) for x in ad.split("_"))
        kayit = json.load(open(yol, encoding="utf-8"))
        rest = kayit.get("veri")
        rest_mesafe = kayit.get("mesafe_km") or 0.0

        t0 = time.time()
        wcs, mesafe, durum = wcs_toprak_al(lat, lon)
        s = time.time() - t0
        sureler.append(s)

        if wcs is None:
            print(f"{ad:>18}  {s:5.2f} s  WCS: {durum}")
            if rest is not None:
                hatalar.append(f"{ad}: REST veri veriyordu, WCS vermedi ({durum})")
            else:
                bos += 1
            continue

        if rest is None:
            print(f"{ad:>18}  {s:5.2f} s  WCS deger buldu, REST bulamamisti (fazladan)")
            continue

        satir = []
        uyusmayan: list[str] = []
        for alan in ALANLAR:
            a, b = rest.get(alan), getattr(wcs, alan, None)
            if a is None or b is None:
                continue
            fark = abs(a - b)
            satir.append(f"{alan[:4]} {a:5.1f}/{b:5.1f}")
            if rest_mesafe > 0:
                continue     # farkli koordinat okunmus, karsilastirmaya girmez
            sapmalar.setdefault(alan, []).append(fark)
            if fark > ESIK:
                uyusmayan.append(f"{alan} REST {a} vs WCS {b}")

        etiket = "" if rest_mesafe == 0 else f"  [REST {rest_mesafe} km oteden]"
        if uyusmayan:
            eslesen = _kutu_tara(lat, lon, rest)
            if eslesen:
                etiket = f"  [yuvarlama: tam eslesme {eslesen} noktasinda]"
            else:
                hatalar.extend(f"{ad}: {u}" for u in uyusmayan)
        if rest_mesafe > 0:
            kaymis.append(ad)
        print(f"{ad:>18}  {s:5.2f} s  " + "  ".join(satir) + etiket)

    print(f"\n{'=' * 72}\nSAPMA (REST - WCS, mutlak) -- sadece REST'in tam pikseli okudugu noktalar")
    for alan, l in sapmalar.items():
        print(f"  {alan:16s} ortalama {sum(l)/len(l):5.2f}  en buyuk {max(l):5.2f}"
              f"  ({len(l)} nokta)")
    if kaymis:
        print(f"\nKarsilastirma disi ({len(kaymis)} nokta): REST bu noktalarda deger "
              f"bulamayip komsudan okumus, WCS ise daha yakindan buldu:")
        print(f"  {', '.join(kaymis)}")
    if sureler:
        print(f"\nSURE  en hizli {min(sureler):5.2f} s  "
              f"ortalama {sum(sureler)/len(sureler):5.2f} s  "
              f"en yavas {max(sureler):5.2f} s")
    print(f"Deger bulunamayan nokta: {bos}")

    print(f"\nHATA: {len(hatalar)}")
    for h in hatalar:
        print(f"  {h}")
    sys.exit(1 if hatalar else 0)


if __name__ == "__main__":
    main()
