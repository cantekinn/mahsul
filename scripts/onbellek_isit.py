"""One cikan noktalarin onbellegini doldurur (depoya gomulecek).

Calistirma: py -m scripts.onbellek_isit

NEDEN: ucretsiz barindirmada disk kalici degil. Bu noktalarin onbellegi depoya
girerse, canli surumde kutudan cikar cikmaz hazir gelirler.

NE ISITILIR: yer adi, yukselti, iklim, toprak, parsel ve anlik tahmin kaydi.
Hepsi ayri ayri onbelleklenir, biri basarisiz olursa digerleri yine yazilir.

IKI AYRI KUME ISITILIR ve AYRI RAPORLANIR: hazir noktalar (data/one_cikan.py)
ve kayitli tapu parselleri (data/parseller/). Gerekce isitilacak_gruplar()
docstring'inde.

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

from data import open_meteo
from data.global_location import (
    konum_ozeti, parselleri_al, toprak_al_durum,
)
from data.one_cikan import ONE_CIKANLAR
from data.parcel_files import load_parcels

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
# 60/9 = 6.7 s gercek sinir; 8 s onun biraz ustunde kaliyor.
#
# SURE OLCULDU, TAHMIN EDILMEDI: 68 noktalik kosu 19.6 dakika surdu. Once
# buraya "yaklasik 5 dakika" yazmistim; o sayi yalnizca beklemeleri topluyor,
# isteklerin kendi suresini saymiyordu (nokta basina 1.4 s ile 36 s arasinda
# olculdu, parsel katmani zaman asimina kadar gidebiliyor). Script gunde bir
# kez elle calistiriliyor, bu sure sorun degil; yanlis yazilmis olmasi sorun.
#
# BEKLEME NEDEN KUTUPHANEYE KONMADI: data/open_meteo.py canli istegin de
# yolunda. Oraya 60 saniyelik bir bekleme koysaydik kullanicinin tarayicisi
# haritaya tiklayinca bir dakika donardi. Toplu isitme ile tekil istek farkli
# davranis ister; bekleme toplu isin oldugu yere ait.
ARA_S = 8.0


def _temiz(s: object) -> str:
    """Windows konsolu (cp1254) Turkce disi karakterlerde cokuyor."""
    return re.sub(r"[^\x00-\x7f]", "?", str(s))


def isitilacak_gruplar() -> list[tuple[str, list[tuple[str, float, float]]]]:
    """Isitilacak noktalar IKI AYRI KUME halinde: hazir noktalar, tapu parselleri.

    NEDEN PARSELLER DE ISITILIYOR: olctuk, 48 tapu kaydi 2 ondalikta 32 ayri
    noktaya dusuyor ve bunlarin 30'u onbellekte YOKTU. Yani listeden tapu secen
    kullanici, sirf o koordinat onceden isitilmadigi icin 30 yillik iklim
    normalini calisma aninda sorduruyordu; ucretsiz katmanin saatlik kotasi
    doluysa urun onerisi komple dusuyordu. Oysa parsel listesi SABIT, hangi
    koordinatlarin sorulacagi onceden bilinir. Bilinen bir sorguyu kullanici
    beklerken yapmak icin bir sebep yok.

    NEDEN TEK LISTE DEGIL IKI KUME: iki kumede eksik kalmak ayni sey demek
    degil. Hazir nokta listesi elle yazilmis sabit bir liste; oradaki bir
    eksik buyuk ihtimalle benim koordinat notumdur. Tapu parseli ise
    kullanicinin KENDI kaydi; oradaki eksik, o parseli secen kisinin
    karsisina bos kart olarak cikar. Tek bir "60/68" sayisi bu iki durumu
    ayni kefeye koyuyor ve hangisinin eksik kaldigini soylemiyordu.

    2 ONDALIKTA TEKILLESTIRME: onbellek anahtari da 2 ondalik kullaniyor
    (bkz. data/open_meteo.py). Ayni hucreye dusen iki parseli iki kez isitmak
    ayni dosyayi iki kez yazardi, sadece kotayi yerdi. Elenen sayi raporda
    ACIKCA yaziliyor ki "48 tapu vardi, 31 nokta isindi" bir kayip gibi
    okunmasin.
    """
    hazir = list(ONE_CIKANLAR)
    gorulen = {(round(lat, 2), round(lon, 2)) for _, lat, lon in hazir}

    tapu: list[tuple[str, float, float]] = []
    for kayit in load_parcels():
        p = kayit["parcel"]
        anahtar = (round(p.lat, 2), round(p.lon, 2))
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        tapu.append((f"{kayit['bolge']} ada {p.ada}", p.lat, p.lon))

    return [("hazir noktalar", hazir), ("tapu parselleri", tapu)]


def _isit(
    grup_ad: str,
    noktalar: list[tuple[str, float, float]],
    sira: int,
    toplam: int,
) -> tuple[dict, list[str], int]:
    """Bir kumeyi isitir; kendi sayaci ve kendi eksik listesiyle doner.

    `sira`/`toplam` yalnizca ekrandaki ilerleme ve son noktadan sonra bosuna
    beklememek icin; kumeler arasinda da bekleme surer, cunku dis servisin
    dakikalik siniri kumeleri ayirt etmiyor.
    """
    eksikler: list[str] = []
    sayac = {"konum": 0, "toprak": 0, "parsel": 0, "tahmin": 0}

    print(f"--- {grup_ad} ({len(noktalar)} nokta) ---")
    for not_, lat, lon in noktalar:
        sira += 1
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

        # ANLIK TAHMIN KAYDI. Ustteki katmanlarin aksine bu veri BAYATLAR:
        # sulama, karbon, iklim riski ve sezon gunlugu onumuzdeki gunlerin
        # ET0/yagis tahminine bakiyor. O yuzden gomulu kopya "guncel veri"
        # degil YEDEK; kota dolu oldugunda kart bos kalmasin diye duruyor ve
        # kullaniciya cekildigi tarihle birlikte gosteriliyor.
        try:
            open_meteo.yedek_yaz(lat, lon, open_meteo._tahmin_penceresi(lat, lon))
            sayac["tahmin"] += 1
            tahmin_ok = "tahmin ok"
        except Exception as exc:
            eksikler.append(f"{not_}: tahmin ({_temiz(exc)[:60]})")
            tahmin_ok = "tahmin YOK"

        print(f"{sira:3d}/{toplam}  {time.time() - t0:6.2f} s  "
              f"{_temiz(not_):32s} "
              f"{_temiz(k.yer_adi or 'ad yok')[:34]:34s} "
              f"pH {toprak.ph if toprak else '-':>4} "
              f"{'' if mesafe in (0.0, None) else f'({mesafe} km)':9s} "
              f"{len(parseller):3d} parsel  {tahmin_ok}")

        # Son noktadan sonra beklemek bos yere 8 saniye kaybettirir.
        if sira < toplam:
            time.sleep(ARA_S)

    print()
    return sayac, eksikler, sira


def main() -> None:
    t_bas = time.time()
    gruplar = isitilacak_gruplar()
    toplam = sum(len(n) for _, n in gruplar)
    tapu_ham = len(load_parcels())
    tapu_elenen = tapu_ham - len(gruplar[1][1])

    print(f"{toplam} nokta isitiliyor:")
    for ad, n in gruplar:
        print(f"  {ad:18s} {len(n):3d}")
    print(f"({tapu_ham} tapu kaydinin {tapu_elenen} tanesi 2 ondalikta baska bir "
          f"noktayla ayni onbellek hucresine dusuyor, tekrar sorulmuyor)\n")

    sira = 0
    rapor: list[tuple[str, int, dict, list[str]]] = []
    for grup_ad, noktalar in gruplar:
        sayac, eksikler, sira = _isit(grup_ad, noktalar, sira, toplam)
        rapor.append((grup_ad, len(noktalar), sayac, eksikler))

    print(f"{'=' * 78}")
    print(f"Toplam sure: {(time.time() - t_bas) / 60:.1f} dakika")
    # IKI KUME AYRI RAPORLANIR: hazir noktalardaki bir eksik listeyi gozden
    # gecirmemi gerektirir, tapu parselindeki bir eksik ise o parseli secen
    # kullanicinin karsisina cikar. Ortalama tek sayi ikisini de gizliyordu.
    for grup_ad, n, sayac, eksikler in rapor:
        print(f"\n{grup_ad.upper()} ({n} nokta)")
        for ad, s in sayac.items():
            print(f"  {ad:8s} {s}/{n} isitildi")
        print(f"  EKSIK KALAN: {len(eksikler)} (bunlar onbellege YAZILMADI, "
              f"script tekrar calistirilinca yeniden denenir)")
        for e in eksikler:
            print(f"    {e}")
    # Eksik katman olmasi scripti basarisiz saymaz: parsel katmani dis
    # sunucuya bagli ve o sunucu 429 dondurdugunde tekrar denemek gerekir.
    sys.exit(0)


if __name__ == "__main__":
    main()
