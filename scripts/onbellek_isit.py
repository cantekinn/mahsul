"""One cikan noktalarin onbellegini doldurur (depoya gomulecek).

Calistirma: py -m scripts.onbellek_isit

NEDEN: ucretsiz barindirmada disk kalici degil. Bu noktalarin onbellegi depoya
girerse, canli surumde kutudan cikar cikmaz hazir gelirler.

NE ISITILIR: yer adi, yukselti, iklim, toprak ve parsel. Hepsi ayri ayri
onbelleklenir, biri basarisiz olursa digerleri yine yazilir.

BASARISIZ KATMAN ZORLA YAZILMAZ. Bir katman alinamazsa o nokta icin ONBELLEGE
BOS SONUC KOYULMAZ; yoksa gecici bir arizayi depoya gomup kalici yalana
cevirmis oluruz. Bu proje bu hatayi sekiz kez yasadi. Alinamayan katman
raporda gosterilir ve script tekrar calistirilinca yeniden denenir.

NEDEN NOKTALAR ARASINDA BEKLENIYOR: bkz ARA_S.
"""
from __future__ import annotations

import re
import sys
import time

from data.global_location import (
    konum_ozeti, parselleri_al, toprak_al_durum,
)
from data.one_cikan import ONE_CIKANLAR

# NOKTALAR ARASI BEKLEME. Script istekleri ara vermeden atinca Open-Meteo
# reddediyordu ve sebebini kendisi yaziyor:
#   {"error":true,"reason":"Minutely API request limit exceeded.
#    Please try again in one minute."}
# Yani sinir DAKIKALIK, saatlik degil. Olctuk: aralik yokken 37 noktanin ancak
# 7'si, ikinci kosuda 9'u daha isindi; her kosu ayni duvara carpiyordu. Tek
# basina atilan ayni 30 yillik sorgu ise HTTP 200 donuyor.
#
# SURE NEDEN 8 SANIYE: bir kosuda araliksiz 9 istek geciyor, 10.'su reddediliyor
# (olculdu, iki bagimsiz kosuda ayni sayi). Yani tavan dakikada ~9 istek.
# 60/9 = 6.7 s gercek sinir; 8 s onun biraz ustunde kaliyor. 37 nokta icin
# yaklasik 5 dakika eder ve bu script gunde bir kez elle calistiriliyor.
#
# BEKLEME NEDEN KUTUPHANEYE KONMADI: data/open_meteo.py canli istegin de
# yolunda. Oraya 60 saniyelik bir bekleme koysaydik kullanicinin tarayicisi
# haritaya tiklayinca bir dakika donardi. Toplu isitme ile tekil istek farkli
# davranis ister; bekleme toplu isin oldugu yere ait.
ARA_S = 8.0


def _temiz(s: object) -> str:
    """Windows konsolu (cp1254) Turkce disi karakterlerde cokuyor."""
    return re.sub(r"[^\x00-\x7f]", "?", str(s))


def main() -> None:
    t_bas = time.time()
    eksikler: list[str] = []
    sayac = {"konum": 0, "toprak": 0, "parsel": 0}

    print(f"{len(ONE_CIKANLAR)} nokta isitiliyor\n")
    for i, (not_, lat, lon) in enumerate(ONE_CIKANLAR, 1):
        t0 = time.time()
        # Konum: yer adi + yukselti + iklim. Yavas katmanlar kapali, onlari
        # asagida kendi uc noktalarinin kullandigi yoldan isitiyoruz ki
        # onbellek anahtarlari birebir ayni olsun.
        k = konum_ozeti(lat, lon, parsel_ara=False, toprak_ara=False)
        konum_ok = k.yer_adi is not None and k.iklim is not None
        if konum_ok:
            sayac["konum"] += 1
        else:
            eksikler.append(f"{not_}: konum/iklim ({_temiz('; '.join(k.eksik))})")

        toprak, mesafe, t_durum = toprak_al_durum(lat, lon)
        if t_durum == "ok":
            sayac["toprak"] += 1
        else:
            eksikler.append(f"{not_}: toprak ({t_durum})")

        parseller, p_durum = parselleri_al(lat, lon)
        if p_durum == "ok":
            sayac["parsel"] += 1
        else:
            eksikler.append(f"{not_}: parsel ({p_durum})")

        print(f"{i:3d}/{len(ONE_CIKANLAR)}  {time.time() - t0:6.2f} s  "
              f"{_temiz(not_):32s} "
              f"{_temiz(k.yer_adi or 'ad yok')[:34]:34s} "
              f"pH {toprak.ph if toprak else '-':>4} "
              f"{'' if mesafe in (0.0, None) else f'({mesafe} km)':9s} "
              f"{len(parseller):3d} parsel")

        # Son noktadan sonra beklemek bos yere 8 saniye kaybettirir.
        if i < len(ONE_CIKANLAR):
            time.sleep(ARA_S)

    print(f"\n{'=' * 78}")
    print(f"Toplam sure: {(time.time() - t_bas) / 60:.1f} dakika")
    n = len(ONE_CIKANLAR)
    for ad, s in sayac.items():
        print(f"  {ad:8s} {s}/{n} isitildi")
    print(f"\nEKSIK KALAN: {len(eksikler)} (bunlar onbellege YAZILMADI, "
          f"script tekrar calistirilinca yeniden denenir)")
    for e in eksikler:
        print(f"  {e}")
    # Eksik katman olmasi scripti basarisiz saymaz: parsel katmani dis
    # sunucuya bagli ve o sunucu 429 dondurdugunde tekrar denemek gerekir.
    sys.exit(0)


if __name__ == "__main__":
    main()
