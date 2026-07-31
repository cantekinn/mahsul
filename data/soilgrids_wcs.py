"""SoilGrids topragi icin IKINCI KAPI: WCS (maps.isric.org).

NEDEN VAR
=========
Projenin toprak verisi rest.isric.org uzerinden aliniyordu. ISRIC bu servisi
askiya aldi; olctuk: uc kitadan alti sorgunun altisi da basarisiz (0.4-0.7 s
icinde nginx'ten HTTP 503 ya da 30 s zaman asimi). Tek kapiya bagli kalmak,
projede daha once yedi kez yasanan hatayi tekrarlamak olurdu: dis servis
susunca biz "burada toprak yok" saniyoruz.

AYNI VERI, FARKLI KAPI. maps.isric.org ayakta (GetCapabilities 3.5 s'de HTTP
200 dondu) ve arkasinda AYNI SoilGrids 2.0 rasterlari var. Yani bu bir "baska
kaynaktan tahmin" degil, ayni olcumun ikinci erisim yolu.

NEDEN DAHA ONCE KULLANILMADI
============================
SoilGrids rasterlarinin oz koordinat sistemi Interrupted Goode Homolosine
(EPSG:152160). WMS GetFeatureInfo'yu EPSG:4326 ile denedik ve "Search returned
no results" dondu; sorun servis degil, koordinat sistemiydi. Cozum enlem-boylami
Homolosine'e cevirip WCS'ten piksel istemek (pyproj gerekiyor).

DEGER OLCEGI REST ILE AYNIDIR: pH x10, kil/kum/silt g/kg (yani x10 = %),
organik karbon dg/kg, azot cg/kg. Bu yuzden global_location icindeki mevcut
bolme faktorleri aynen gecerlidir.

NODATA: mapserv gecersiz pikseli 0 dondurur. 0 bir pH ya da 0 kil orani
gercekci degildir, bu yuzden 0 "olcum yok" sayilir. Kritik: 0'i gercek deger
sanmak "pH 0, hicbir sey yetismez" gibi bir yalan uretirdi.
"""
from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests
from PIL import Image
from pyproj import Transformer

from core.schemas import SoilData

WCS_URL = "https://maps.isric.org/mapserv"
IGH = "+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs"
WCS_TIMEOUT = 20

# SoilGrids ozellik -> (SoilData alani, bolme faktoru). REST ile ayni olcek.
WCS_PROPS = {
    "phh2o": ("ph", 10.0),
    "nitrogen": ("nitrogen", 100.0),
    "clay": ("clay", 10.0),
    "sand": ("sand", 10.0),
    "silt": ("silt", 10.0),
    "soc": ("organic_carbon", 10.0),
    "bdod": ("bulk_density", 100.0),   # cg/cm3 -> g/cm3
    "cec": ("cec", 10.0),              # mmol(c)/kg -> cmol(c)/kg
}

# Aranacak pencere yaricaplari (metre). Once tam piksel (250 m cozunurluk),
# deger yoksa genisleyerek komsuluga bakilir. REST surumu de ayni mantikla
# 0.02 derece (~2.2 km) kayiyordu; buradaki 1375 m ve 5125 m ona denk gelir.
YARICAPLAR = [125, 1375, 5125]

_TR = Transformer.from_crs("EPSG:4326", IGH, always_xy=True)


def _pencere(prop: str, x: float, y: float, yaricap: int,
             timeout: int, derinlik: str = "0-5cm") -> tuple[np.ndarray | None, str]:
    """Tek ozellik icin Homolosine metre kutusunu GeoTIFF olarak ceker."""
    params = {
        "map": f"/map/{prop}.map",
        "SERVICE": "WCS", "VERSION": "2.0.1", "REQUEST": "GetCoverage",
        "COVERAGEID": f"{prop}_{derinlik}_mean", "FORMAT": "image/tiff",
        "SUBSET": [f"X({x - yaricap},{x + yaricap})",
                   f"Y({y - yaricap},{y + yaricap})"],
        "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/152160",
    }
    try:
        r = requests.get(WCS_URL, params=params, timeout=timeout)
    except Exception as exc:
        return None, type(exc).__name__
    if not r.headers.get("content-type", "").startswith("image"):
        # Govde XML hata belgesidir; sunucu cevap verdi ama goruntu vermedi.
        return None, f"HTTP {r.status_code} (goruntu degil)"
    try:
        return np.array(Image.open(io.BytesIO(r.content))), "ok"
    except Exception as exc:
        return None, f"tiff cozulemedi ({type(exc).__name__})"


def _en_yakin_gecerli(dizi: np.ndarray) -> tuple[float, float] | None:
    """Pencerenin MERKEZINE en yakin gecerli pikseli ve uzakligini (m) verir.

    Neden medyan degil: bu bir NOKTA sorgusudur, alan ortalamasi degil. Olctuk:
    medyan alindiginda, nokta piksel sinirina denk geldigi icin 2x2 piksel donen
    bir noktada REST ile fark cikti (kil 32.9 yerine 32.8, organik karbon 23.9
    yerine 23.2). En yakin pikseli secince fark sifirlandi. Toprak kisa mesafede
    degisir, komsu pikseli ortalamak degeri sulandirir.
    """
    gecerli = dizi > 0
    if not gecerli.any():
        return None
    sat, sut = np.indices(dizi.shape)
    # Piksel merkezleri dizi merkezine gore; cozunurluk 250 m.
    dy = (sat - (dizi.shape[0] - 1) / 2) * 250.0
    dx = (sut - (dizi.shape[1] - 1) / 2) * 250.0
    uzak = np.where(gecerli, np.hypot(dx, dy), np.inf)
    i = int(np.argmin(uzak))
    return float(dizi.flat[i]), float(uzak.flat[i])


def _ozellik_degeri(prop: str, x: float, y: float, timeout: int,
                    derinlik: str = "0-5cm") -> tuple[float | None, float, str]:
    """Deger bulunana kadar pencereyi buyutur. (deger, uzaklik_m, durum)."""
    son = "bilinmiyor"
    for yaricap in YARICAPLAR:
        dizi, durum = _pencere(prop, x, y, yaricap, timeout, derinlik)
        if dizi is None:
            son = durum
            continue
        bulunan = _en_yakin_gecerli(dizi)
        if bulunan is not None:
            return bulunan[0], bulunan[1], "ok"
        son = "bos"
    return None, 0.0, son


def wcs_toprak_al(lat: float, lon: float, timeout: int = WCS_TIMEOUT,
                  ) -> tuple[SoilData | None, float | None, str]:
    """Noktanin toprak ozelliklerini WCS'ten alir.

    Doner: (toprak, kaynak_mesafe_km, durum)
      durum "ok"   -> sonuc kesin.
      durum "bos"  -> sunucu cevap verdi, bu noktada gercekten deger yok.
      digeri       -> sunucuya ulasilamadi, toprak "yok" degil BILINMIYOR.

    Bu uc durum ayrimi REST surumundekiyle ayni ve ayni sebeple var: cagiran
    taraf gecici arizayi "veri yok" diye onbellege yazmasin.
    """
    x, y = _TR.transform(lon, lat)

    # Alti ozellik birbirinden bagimsiz; sirayla sorulursa sure alti katina
    # cikar. Es zamanli sorulunca toplam sure en yavas ozelligin suresi olur.
    with ThreadPoolExecutor(max_workers=len(WCS_PROPS)) as havuz:
        sonuclar = list(havuz.map(
            lambda p: (p, *_ozellik_degeri(p, x, y, timeout)), WCS_PROPS))

    cikti: dict[str, float] = {}
    en_uzak = 0.0
    ulasilamadi = ""
    for prop, deger, uzaklik, durum in sonuclar:
        if deger is None:
            if durum not in ("bos", "ok"):
                ulasilamadi = durum
            continue
        alan, bolen = WCS_PROPS[prop]
        cikti[alan] = round(deger / bolen, 2)
        en_uzak = max(en_uzak, uzaklik)

    if cikti:
        # Deger noktanin kendi pikselinden mi geldi, kac km oteden mi geldi:
        # arayuze durust olarak bunu bildiririz.
        return SoilData(**cikti), round(en_uzak / 1000, 1), "ok"
    if ulasilamadi:
        return None, None, ulasilamadi
    return None, None, "bos"


# --- Surum katmani (0-30 cm) ----------------------------------------------
#
# NEDEN AYRI BIR CEKIM: uygulamanin geri kalani 0-5 cm ile calisiyor ve urun
# onerisi icin bu yeterli. Besin karnesi ise ciftcinin SURDUGU katmani sormak
# zorunda; laboratuvar analiz raporlari da 0-20/0-30 cm derinlikten alinan
# ornekle yapilir.
#
# FARK OLCULDU, TAHMIN EDILMEDI. Uc Turk tarim noktasinda organik karbonun
# 0-5 cm degeri, 0-30 cm agirlikli ortalamasinin kati olarak:
#     Bursa Karacabey   41.70 -> 23.28 g/kg   kat 1.79
#     Ankara Polatli    39.70 -> 22.13 g/kg   kat 1.79
#     Sanliurfa Harran  18.40 -> 10.22 g/kg   kat 1.80
# Yani yuzey katmani organik maddeyi neredeyse IKI KAT fazla gosteriyor. Bu
# sapmayi 1.79'luk bir duzeltme katsayisiyla kapatmak uc noktaya egri uydurmak
# olurdu; onun yerine uc derinligin ucu de cekilip kalinlikla agirliklandirilir,
# yani sonuc yaklastirma degil dogrudan hesaptir.
DERINLIKLER = (("0-5cm", 5), ("5-15cm", 10), ("15-30cm", 15))


def wcs_surum_katmani(lat: float, lon: float, timeout: int = WCS_TIMEOUT,
                      ) -> tuple[SoilData | None, str]:
    """0-30 cm kalinlik agirlikli toprak ozellikleri.

    Bir ozellik icin uc derinligin BIRI bile gelmezse o ozellik hic
    dondurulmez. Eksik katmani ortalamaya katmamak "iki katmanin ortalamasi"
    demek olurdu ve alan adi hala 0-30 cm oldugu icin bunu kimse fark etmezdi.
    """
    x, y = _TR.transform(lon, lat)
    isler = [(p, d, k) for p in WCS_PROPS for d, k in DERINLIKLER]

    with ThreadPoolExecutor(max_workers=6) as havuz:
        sonuclar = list(havuz.map(
            lambda i: (i[0], i[2], _ozellik_degeri(i[0], x, y, timeout, i[1])[0]),
            isler))

    toplam: dict[str, list[tuple[float, int]]] = {}
    for prop, kalinlik, deger in sonuclar:
        if deger is not None:
            toplam.setdefault(prop, []).append((deger, kalinlik))

    cikti: dict[str, float] = {}
    for prop, parcalar in toplam.items():
        if len(parcalar) != len(DERINLIKLER):
            continue
        alan, bolen = WCS_PROPS[prop]
        agirlikli = sum(d * k for d, k in parcalar) / sum(k for _, k in parcalar)
        cikti[alan] = round(agirlikli / bolen, 2)

    if not cikti:
        return None, "bos"
    return SoilData(**cikti), "ok"
