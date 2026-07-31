"""Kuresel oneri motorunun DOGRULUK testi.

Calistirma: py -m scripts.test_global_reco

TESTIN NE OLCTUGU (ve nicin boyle degistirildigi):
Ilk surumde tek olcut "bolgenin ana urunu ilk 20'de mi" idi. Bu olcut yanlisti,
cunku modelin veremeyecegi bir bilgiyi soruyordu. Model EcoCrop tabanli bir
IKLIM-TOPRAK UYGUNLUK modelidir; "burada ne yetisir" sorusunu yanitlar.
"Burada en cok ne ekilir" sorusunun cevabi ise pazar fiyati, sozlesmeli tarim,
sulama altyapisi ve gelenekle belirlenir; EcoCrop'ta bu verilerin hicbiri yok.
Olctuk: Antalya'da model ilk sirlara pamuk, fasulye, salatalik, kavun, nohut
koyuyor. Bunlarin hepsi Antalya'da gercekten yetisir; yani liste yanlis degil,
sadece "en karli" siralamasi degil. Narenciyeyi 45. siraya koymasi bu yuzden
tek basina bir hata kaniti sayilamaz.

Bu yuzden test uc ayri sey olcer:
  1) ELENMEME   : bolgenin gercek ana urunu elenmemis olmali. Elenmisse model
                  "burada bu yetismez" demis olur ki bu kesin bir hatadir.
  2) UYGUN BULMA: ana urun en az "Uygun" (>=55) puan almali.
  3) YANLIS POZITIF: bolgede kesinlikle yasayamayacak urunler onerilmemeli.
                  Asil koruyucu olcut budur. Ciftciyi zarara sokan sey listenin
                  4. degil 1. sirasinda yanlis urun olmasidir. Bu olcut gercek
                  bir hatayi yakaladi: EcoCrop'ta kis dayanikliligi verisi
                  olmayan 10 cok yillik urun eleme disi kaliyordu ve Antalya'ya
                  (olculen mutlak minimum -2.3 C) ANANAS 97.3 puanla 3. siradan
                  oneriliyordu. Ananas donda olur.
Sira bilgisi yine basiliyor ama BASARI OLCUTU DEGIL, bilgi amaclidir.
"""
from __future__ import annotations

import re

from core.schemas import SoilData
from data.global_location import toprak_al
from data.open_meteo import get_monthly_climate
from models.crop_reco.global_reco import gruba_gore, urun_oner

# (ad, lat, lon, bolgenin gercek ana urunleri, orada YASAYAMAYACAK urunler)
# "yasayamaz" listesi kamuya acik iklim gercekleriyle secildi:
#   Antalya kisin -2.3 C gorur      -> tropik cok yilliklar korumasiz yasamaz
#   Iowa kisin -34 C gorur          -> narenciye/zeytin/hurma yasamaz
#   Riverina yarikurak (415 mm)     -> celtik/cay yagmurla yetismez
YERLER = [
    ("Iowa (ABD)", 42.03, -93.63,
     ["misir", "soya"],
     ["portakal", "limon", "zeytin", "muz", "kahve", "ananas"]),
    ("Antalya (TR)", 36.92, 30.83,
     ["portakal", "mandalina", "limon", "domates", "zeytin"],
     ["ananas", "kahve", "yag_palmiyesi", "kakao"]),
    ("Pencap (IN)", 30.90, 75.85,
     ["bugday", "celtik", "pamuk"],
     ["kakao", "yag_palmiyesi"]),
    ("Nakuru (KE)", -0.30, 36.08,
     ["misir", "bugday", "patates"],
     ["hurma"]),
    ("Riverina (AU)", -34.75, 146.05,
     ["bugday", "arpa", "uzum"],
     ["kakao", "muz", "kahve"]),
]

UYGUN_ESIK = 55.0        # "Uygun" etiketinin alt siniri


def _temiz(s: object) -> str:
    """Windows konsolu (cp1254) Turkce disi karakterlerde cokuyor."""
    return re.sub(r"[^\x00-\x7f]", "?", str(s))


def main() -> None:
    elenmedi_top = uygun_top = beklenen_top = 0
    yanlis_pozitif: list[str] = []

    for ad, lat, lon, beklenen, yasayamaz in YERLER:
        toprak, _ = toprak_al(lat, lon)
        toprak = toprak or SoilData()
        iklim = get_monthly_climate(lat, lon)

        liste = urun_oner(toprak, iklim, adet=10_000)
        sira = {r["urun"]: i + 1 for i, r in enumerate(liste)}
        kayit = {r["urun"]: r for r in liste}

        print(f"\n{'=' * 72}\n{ad}   pH {toprak.ph}  "
              f"yillik yagis {iklim['yillik_yagis']:.0f} mm  "
              f"mutlak min {iklim['mutlak_min']} C  "
              f"({iklim['yil_sayisi']} yillik normal)")

        print(f"{'-' * 72}\nIlk 10 oneri ({len(liste)} urun uygun bulundu):")
        for r in liste[:10]:
            ne_zaman = "cok yillik" if r["cok_yillik"] else f"ekim {r['ekim_ayi']}"
            su = f" sulama {r['su_acigi_mm']} mm" if r["su_acigi_mm"] else ""
            print(f"  {r['skor']:5.1f}  {_temiz(r['ad']):20s} "
                  f"{_temiz(r['grup']):13s} {ne_zaman}{su}")

        print("1) Bolgenin ana urunleri elenmis mi, uygun bulunmus mu:")
        for u in beklenen:
            beklenen_top += 1
            r = kayit.get(u)
            if r is None:
                print(f"    {u:12s} ELENDI  <- HATA")
                continue
            elenmedi_top += 1
            iyi = r["skor"] >= UYGUN_ESIK
            uygun_top += iyi
            print(f"    {u:12s} skor {r['skor']:5.1f} ({_temiz(r['uygunluk'])}), "
                  f"sira {sira[u]}/{len(liste)}   {'' if iyi else '<- esigin altinda'}")

        print("2) Burada yasayamayacak urunler onerilmis mi:")
        for u in yasayamaz:
            if u in kayit:
                yanlis_pozitif.append(f"{ad}: {u} ({kayit[u]['skor']:.1f}, "
                                      f"{sira[u]}. sira)")
                print(f"    {u:12s} ONERILDI skor {kayit[u]['skor']:5.1f} <- HATA")
            else:
                print(f"    {u:12s} dogru sekilde elendi")

    print(f"\n{'=' * 72}\nSONUC")
    print(f"  Ana urun elenmedi     : {elenmedi_top}/{beklenen_top}")
    print(f"  Ana urun >= {UYGUN_ESIK:.0f} puan : {uygun_top}/{beklenen_top}")
    print(f"  Yanlis pozitif        : {len(yanlis_pozitif)}")
    for y in yanlis_pozitif:
        print(f"      {y}")

    print(f"\n{'=' * 72}\nGRUP BAZLI ORNEK (Antalya) - arayuzde cesitlilik icin:")
    toprak, _ = toprak_al(36.92, 30.83)
    iklim = get_monthly_climate(36.92, 30.83)
    for g, l in gruba_gore(toprak or SoilData(), iklim, grup_basina=3).items():
        adlar = ", ".join(f"{_temiz(r['ad'])} ({r['skor']:.0f})" for r in l)
        print(f"  {_temiz(g):14s} {adlar}")


if __name__ == "__main__":
    main()
