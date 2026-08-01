"""Dunyanin herhangi bir koordinati icin tarimsal konum ozeti (ucretsiz kaynaklar).

Bu modul projeyi Antalya kilidinden cikarir. Onceki akis MEGSIS/TKGM'ye bagliydi
ve yalnizca Turkiye'de calisiyordu; burada kaynaklarin hepsi kuresel.

KAYNAKLAR (hepsi anahtarsiz, olculerek dogrulandi):
  iklim     Open-Meteo archive      kuresel, hizli, okyanusta bile cevap veriyor
  yukselti  Open-Meteo elevation    kuresel (Everest 8343 m dogru geldi)
  yer adi   Nominatim (OSM)         kuresel; karada ad, denizde "Unable to geocode"
  toprak    SoilGrids (ISRIC)       kuresel AMA yavas ve yer yer bos
  parsel    Overpass (OSM)          kapsam bolgeye gore cok degisken

OLCULEN ZAYIFLIKLAR VE BURADAKI KARSILIKLARI
1) SoilGrids 15-82 saniye surebiliyor  -> disk onbellegi (ayni nokta bir daha
   sorulmaz) + tek istekte tum ozellikler.
2) SoilGrids bazi noktalarda null donuyor (Pencap, Nakuru, Sao Paulo olculdu)
   -> komsu noktalari deneme. Olcum: Nakuru 1. komsuda, Sao Paulo 5. komsuda
   bulundu; Pencap 6 komsuda da bos kaldi, yani her zaman cozmuyor.
3) Overpass 429/504 veriyor. ONEMLI DERS: ilk surumde bu hatayi bos listeye
   cevirmistik ve "bu bolgede parsel yok" diye raporluyorduk. Olcum bunun YANLIS
   oldugunu gosterdi: Iowa sorgusu tek basina 60 parsel dondururken arka arkaya
   calistirilinca 0 donuyordu. Artik 3 ayna sirayla deneniyor ve "sunucu cevap
   vermedi" ile "gercekten parsel yok" ayri ayri raporlaniyor (parsel_durum).
   Parsel yine de ZORUNLU DEGIL; bulunmazsa konum tam calisir.
4) ESA WorldCover icin anahtarsiz nokta API'si YOK (arastirildi; COG veya Earth
   Engine gerekiyor) -> arazi ortusu icin OSM landuse etiketi kullaniliyor.

TASARIM KURALI: hicbir kaynak tek basina akisi durduramaz. Her alan None olabilir,
`eksik` listesi neyin gelmedigini acikca soyler. Cikti "sessizce yanlis" olmaz.
"""
from __future__ import annotations

import json
import math
import random
import time
from datetime import date
from dataclasses import dataclass, field, asdict
from pathlib import Path

import requests

from core.config import ROOT_DIR
from core.schemas import ClimateData, SoilData
from data.soilgrids_wcs import wcs_surum_katmani, wcs_toprak_al

ONBELLEK_DIR = ROOT_DIR / "data" / "_onbellek"
UA = {"User-Agent": "tarim-asistani/1.0 (+https://github.com/cantekinn)"}

SOILGRIDS_URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Overpass halka acik sunuculari sik sik 429 (cok istek) ve 504 doner. Tek
# sunucuya guvenmek "bu bolgede parsel yok" gibi YANLIS bir sonuc uretiyordu
# (olculdu: ayni sorgu tek basina 60 parsel, arka arkaya calisinca 0). Bu yuzden
# birden fazla ayna sirayla denenir ve basarisizlik ACIKCA raporlanir.
# AYNA SECIMI OLCULEREK YAPILDI. Ucu ayni 3 noktayla (Iowa / Antalya / Riverina)
# sinandi ve SADECE kuresel kapsamli olanlar birakildi:
#   overpass-api.de   Iowa 6, Antalya 7   hizli (3-5 s) ama yogunlukta HTTP 429
#   maps.mail.ru      Iowa 6, Antalya 7   yavas (1-34 s) ama kapsami kuresel
#   overpass.osm.ch   Iowa 0, Antalya 0, Bern 30  -> YALNIZCA ISVICRE VERISI
#   kumi.systems / private.coffee / openstreetmap.ru  -> erisilemiyor (timeout)
#
# osm.ch'i listeden CIKARMAK zorunluydu: Isvicre disinda HTTP 200 ile BOS liste
# donuyor. Yedek olarak kullanilinca "sunucu mesgul" durumunu sessizce
# "burada parsel yok" yalanina ceviriyordu. Bir ayna ancak KURESEL ise yedek olabilir.
# Iki bagimsiz kuresel aynanin ayni sayiyi vermesi (Iowa 6, Antalya 7) sonucun
# gercek oldugunu, Riverina'daki 0'in da gercek bir bosluk oldugunu dogruluyor.
OVERPASS_AYNALAR = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
OVERPASS_TIMEOUT = 50       # maps.mail.ru olcumde 34 s surdu, pay birakildi
OVERPASS_DENEME = 2         # 429 alinca ayni sunucuyu bekleyip tekrar dene
PARSEL_BOS_TTL_GUN = 30     # bos sonucun onbellekte kalma suresi (gerekce parselleri_al)

# TOPLAM SURE BUTCESI. Tek tek zaman asimlari CARPARAK birikiyordu:
# 2 ayna x 2 deneme x 50 s = 200 s ve olcumde tam olarak bu yasandi
#   Riverina 200.6 s | Antalya 188.7 s | Nakuru 173.9 s
# Bu bir web servisi icin kullanilamaz; kullanici haritada bir noktaya tiklayip
# 3 dakika bekleyemez. Parsel katmani zaten ZORUNLU DEGIL (bulunamazsa konum tam
# calisir), o yuzden ona harcanacak toplam sureyi bastan sinirliyoruz. Butce
# dolunca durum "sure asildi" olur; bu "parsel yok" DEMEK DEGILDIR, aynen diger
# hata durumlari gibi "bilinmiyor" olarak raporlanir.
PARSEL_BUTCE_S = 25

# SOILGRIDS YAVAS AMA BOZUK DEGIL - OLCULDU.
# Once en kotu durum 7 komsu x 120 s = 846 saniyeydi. Olctuk, teorik degil:
# Winnipeg (49.88, -97.15) sorgusu 54 saniye surdu ve sonunda "toprak yok" dedi;
# oysa ayni koordinat 30 saniye sonra dogrudan sorulunca HTTP 200 ile pH dahil
# tum degerleri dondurdu. Yani yavaslik gecici yuktu, veri hep oradaydi.
# Sonra ayni sorguyu 6 kez ard arda olctuk (Nil deltasi, tek ozellik):
#   40.4 s zaman asimi | 37.5 s ok | 40.4 s zaman asimi | 27.2 s ok | 1.2 s ok | 22.8 s ok
# Cikarim: HTTP 429 yok, hata yok, sadece 1-40 saniye arasi cok degisken gecikme
# ve AYNI sorgu bir sonraki denemede basariya donuyor. Iki sonuc dogurur:
#   1) Basarisizlikta KOMSU NOKTAYA GECMEK ANLAMSIZ. Komsu da ayni sunucudadir;
#      sunucu yavassa 2 km oteyi sormak hicbir sey degistirmez. Komsu tarama
#      sadece sunucunun CEVAP VERIP "burada degerim yok" dedigi durum icindir.
#      Basarisizlikta AYNI noktayi tekrar sormak gerekir, olcum bunu destekliyor.
#   2) Toprak, parsel gibi YAVAS KATMANDIR ve ayni sekilde ayri istenmelidir.
#      Bu yuzden iki butce var: uzun butce toprak ozel olarak istendiginde,
#      kisa butce ise oneri gibi toprak olmadan da is goren akislarda kullanilir.
# ISTEK BASINA 25 SANIYE, gozlenen dagilima gore secildi. Basarili yanitlarda
# olculen sureler: 1.2, 9.2, 20.2, 21.7, 22.8, 27.2, 37.5 saniye. Basarisizlik
# ise "yavas yanit" degil ASILMA seklinde: istek hic donmuyor ve 120 saniyede
# bile bitmiyor (iki kez 120.4 ve 120.6 s zaman asimi olculdu). Yani 25 saniyeyi
# gecen bir istegin bitme ihtimali dusuk, oysa YENI bir istek hemen basarili
# olabiliyor. 25 s, olculen basarilarin 5/7'sini yakalar ve asilmis baglantiyi
# erken birakip butceyi ikinci bir denemeye ayirir.
# TEST EDILIP ELENEN ACIKLAMA: "gecikme istenen ozellik sayisiyla artiyor olabilir"
# diye dusunuldu, cunku 1 ozellik 9.2 s'de donerken 6 ozellik zaman asimina
# ugramisti. Olctuk ve YANLIS CIKTI: ayni saatte 1 ozellik iki kez 120 s'de
# donmedi, 6 ozellik 20.2 s'de dondu. Yani gecikme sorguya degil sunucunun o
# anki durumuna bagli; ozellikleri ayri isteklere bolmek fayda etmez.
SOILGRIDS_TIMEOUT = 25
SOILGRIDS_BUTCE_S = 60      # toprak ASIL istendiginde (kullanici bekliyor)
SOILGRIDS_HIZLI_BUTCE_S = 12   # yan katman oldugunda: alinirsa alinir, yoksa devam
TOPRAK_BOS_TTL_GUN = 30     # "burada toprak verisi yok" sonucunun omru

# SoilGrids ozellik -> (alan adi, bolme faktoru). Tek istekte hepsi cekilir.
_TOPRAK_PROPS = {
    "phh2o": ("ph", 10.0),
    "nitrogen": ("nitrogen", 100.0),
    "clay": ("clay", 10.0),
    "sand": ("sand", 10.0),
    "silt": ("silt", 10.0),
    "soc": ("organic_carbon", 10.0),
    "bdod": ("bulk_density", 100.0),
    "cec": ("cec", 10.0),
}

# SoilGrids bos donerse denenecek kaymalar (derece). Merkez once.
_KOMSU_KAYMALAR = [
    (0.0, 0.0), (0.02, 0.0), (0.0, 0.02), (-0.02, 0.0), (0.0, -0.02),
    (0.05, 0.05), (-0.05, -0.05),
]

# OSM landuse etiketi -> okunakli Turkce arazi ortusu
LANDUSE_TR = {
    "farmland": "Tarla",
    "orchard": "Meyve bahcesi",
    "vineyard": "Bag",
    "greenhouse_horticulture": "Sera",
    "meadow": "Cayir",
    "forest": "Orman",
    "residential": "Yerlesim",
}


@dataclass
class Parsel:
    """OSM'den gelen tarim alani. Kuresel karsiligi MEGSIS parselinin."""
    osm_id: int
    tur: str                      # farmland / orchard / vineyard ...
    tur_tr: str
    alan_m2: float | None = None
    merkez_lat: float | None = None
    merkez_lon: float | None = None
    ad: str | None = None
    sinir: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class KonumOzeti:
    """Bir koordinatin tarimsal kimlik karti."""
    lat: float
    lon: float
    yer_adi: str | None = None
    ulke: str | None = None
    karada: bool = True
    yukselti_m: float | None = None
    toprak: SoilData | None = None
    toprak_kaynak_mesafe_km: float | None = None   # komsudan alindiysa
    toprak_durum: str = "sorgulanmadi"   # "ok" ise toprak None olmasi gercek bosluk
    iklim: ClimateData | None = None
    parseller: list[Parsel] = field(default_factory=list)
    parsel_durum: str = "sorgulanmadi"   # "ok" ise bos liste gercekten "yok" demek
    eksik: list[str] = field(default_factory=list)  # gelmeyen katmanlar

    def sozluk(self) -> dict:
        d = asdict(self)
        d["toprak"] = self.toprak.model_dump() if self.toprak else None
        d["iklim"] = self.iklim.model_dump() if self.iklim else None
        return d


# --------------------------------------------------------------------------
# Onbellek: SoilGrids cok yavas oldugu icin sart
# --------------------------------------------------------------------------

def _onbellek_yolu(ad: str, lat: float, lon: float) -> Path:
    # ~1 km cozunurluk yeterli; toprak bu olcekte degismiyor
    return ONBELLEK_DIR / ad / f"{lat:.2f}_{lon:.2f}.json"


def _onbellekten(ad: str, lat: float, lon: float) -> dict | None:
    p = _onbellek_yolu(ad, lat, lon)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _onbellege(ad: str, lat: float, lon: float, veri: dict) -> None:
    p = _onbellek_yolu(ad, lat, lon)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


def hazir_katmanlar(lat: float, lon: float) -> list[str]:
    """Bu nokta icin onbellekte HANGI katmanlar var. AG ISTEGI YAPMAZ.

    NEDEN VAR: kisayol listesi "bu nokta hazir" diyor. Once bunu sadece yer
    adinin varligina bakarak soyluyordum ve YALAN SOYLUYORDU: uc noktada yer
    adi onbellekteydi ama iklim yoktu (Open-Meteo saatlik kotasi dolmustu),
    yani dugmeye basinca urun onerisi hic gelmiyordu. Ekranda "hazir" yazan
    bir dugmenin acilmamasi, bu projenin sekiz kez yasadigi sessiz hatanin
    tam olarak aynisi. Artik dort katmanin dordune de ayri ayri bakiliyor.
    """
    hazir = []
    if _onbellekten("yer", lat, lon):
        hazir.append("yer")
    # Iklim onbellegi open_meteo modulunde ve anahtarina yil sayisini da
    # katiyor; o yuzden ortak _onbellekten() ile okunamiyor.
    if (ONBELLEK_DIR / "iklim" / f"{lat:.2f}_{lon:.2f}_30y.json").exists():
        hazir.append("iklim")
    if _onbellekten("toprak", lat, lon):
        hazir.append("toprak")
    if _onbellekten("parsel", lat, lon):
        hazir.append("parsel")
    return hazir


def onbellekteki_yer_adi(lat: float, lon: float) -> tuple[str | None, str | None]:
    """Onbellekte yer adi VARSA verir, yoksa (None, None). AG ISTEGI YAPMAZ.

    Neden ayri islev: kisayol listesi acilista 38 nokta icin ad gosterecek.
    yer_adi_al() cagirsaydik, onbellekte olmayan her nokta icin Nominatim'e
    gidip acilisi kilitlerdi. Burada ad yoksa arayuz kendi kisayol etiketini
    gosterir, uydurma bir ad UYDURULMAZ.
    """
    kayit = _onbellekten("yer", lat, lon)
    if not kayit:
        return None, None
    return kayit.get("ad"), kayit.get("ulke")


def _mesafe_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine. Toprak verisinin kac km oteden alindigini durustce raporlamak icin."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# --------------------------------------------------------------------------
# Katmanlar
# --------------------------------------------------------------------------

def _soilgrids_ham(lat: float, lon: float,
                   timeout: int = SOILGRIDS_TIMEOUT) -> tuple[dict | None, str]:
    """Tek istekte tum toprak ozellikleri. Doner: (veri, durum).

    durum "ok"  -> veri geldi
    durum "bos" -> SUNUCU CEVAPLADI ama bu noktada degeri yok (gercek bosluk)
    digeri      -> sunucuya ulasilamadi, burada toprak olup olmadigi BILINMIYOR

    Bu ayrim sonradan eklendi ve gerekcesi olculmus bir hatadir: eski surumde
    her uc durum da None donuyordu, cagiran taraf ikisini ayirt edemiyor ve
    gecici bir arizayi "burada toprak verisi yok" diye onbellege yaziyordu.
    """
    params = [("lon", lon), ("lat", lat), ("depth", "0-5cm"), ("value", "mean")]
    params += [("property", p) for p in _TOPRAK_PROPS]
    try:
        r = requests.get(SOILGRIDS_URL, params=params, headers=UA, timeout=timeout)
    except Exception as exc:
        return None, type(exc).__name__
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    try:
        katmanlar = r.json().get("properties", {}).get("layers", [])
    except ValueError:
        # Overpass'ta da yasandi: HTTP 200 ama govde yarida kesilmis.
        return None, "govde kesik (JSON cozulemedi)"

    cikti: dict[str, float] = {}
    for kat in katmanlar:
        ad = kat.get("name")
        if ad not in _TOPRAK_PROPS:
            continue
        derinlikler = kat.get("depths") or []
        if not derinlikler:
            continue
        ham = derinlikler[0].get("values", {}).get("mean")
        if ham is None:
            continue
        alan, bolen = _TOPRAK_PROPS[ad]
        cikti[alan] = round(ham / bolen, 2)
    return (cikti, "ok") if cikti else (None, "bos")


def toprak_al_durum(lat: float, lon: float,
                    butce_s: float = SOILGRIDS_BUTCE_S,
                    ) -> tuple[SoilData | None, float | None, str]:
    """Toprak verisi + kac km oteden alindigi + durum.

    SoilGrids noktasal olarak bos donebiliyor (olculdu). O yuzden merkez bos
    cikarsa komsu noktalar denenir ve KULLANICIYA mesafe soylenir; sessizce
    baska bir yerin verisini sunmak yaniltici olurdu.

    durum "ok" ise sonuc KESINDIR: veri geldiyse veridir, gelmediyse SoilGrids
    bu noktada gercekten deger tutmuyordur. Baska bir durum ise sunucuya
    ulasilamamistir ve toprak "yok" degil BILINMIYOR'dur.

    BOS SONUC KALICI YAZILMAZ. Bu kural once parselde kondu, sonra ayni hatanin
    toprakta da yasandigi olculdu: Winnipeg icin gecici bir yavaslik yuzunden
    {"veri": null} yazilmisti ve o kayit kalici oldugu icin, sunucu duzeldikten
    sonra bile bu koordinat sonsuza kadar "toprak verisi yok" gorunecekti.
    Simdi bos sonuc ancak (a) sunucu her denemede CEVAP VERIP "degerim yok"
    dediyse ve (b) butce dolmadan tum komsular denendiyse yazilir, o zaman da
    tarihiyle yazilir ve TOPRAK_BOS_TTL_GUN sonra yeniden sorulur.
    """
    onb = _onbellekten("toprak", lat, lon)
    if onb is not None:
        if onb.get("veri"):
            return SoilData(**onb["veri"]), onb.get("mesafe_km"), "ok"
        yazim = onb.get("_tarih")
        if yazim and (date.today() - date.fromisoformat(yazim)).days <= TOPRAK_BOS_TTL_GUN:
            return None, None, "ok"

    # ONCE WCS, SONRA REST. Sira olcumle belirlendi, tercihle degil:
    #   WCS  (maps.isric.org): 9 noktanin 9'unda basarili, 0.88-2.48 s.
    #   REST (rest.isric.org): 6 sorgunun 6'sinda basarisiz (HTTP 503 / zaman
    #        asimi), ISRIC servisi askiya aldigini duyurdu.
    # Ikisi AYNI SoilGrids 2.0 rasterini okur; ayni pikselde alti ozelligin
    # altisinda da sapma sifir olculdu (scripts/test_wcs_toprak.py). Yani bu
    # bir "yaklasik yedek" degil, ayni verinin ayakta olan kapisi.
    toprak, mesafe, durum = wcs_toprak_al(lat, lon)
    if toprak is not None:
        _onbellege("toprak", lat, lon,
                   {"veri": toprak.model_dump(exclude_none=True),
                    "mesafe_km": mesafe, "kaynak": "wcs",
                    "_tarih": date.today().isoformat()})
        return toprak, mesafe, "ok"

    if durum == "bos":
        # Sunucu CEVAP VERDI ve 5 km yaricapta hicbir piksel deger tutmuyor
        # (deniz, kutup, kayalik). Bu kesin bir cevaptir; REST'i ayrica sormak
        # butceyi bosa harcar. Yine de tarihiyle yazilir ki kalici yalan olmasin.
        _onbellege("toprak", lat, lon,
                   {"veri": None, "mesafe_km": None, "kaynak": "wcs",
                    "_tarih": date.today().isoformat()})
        return None, None, "ok"
    wcs_durum = durum

    bitis = time.time() + butce_s
    son_durum = "bilinmiyor"
    tum_bos = True          # her deneme "sunucu cevapladi ama degeri yok" mu
    tamamlandi = False      # butce dolmadan tum komsular denendi mi
    i = 0
    while i < len(_KOMSU_KAYMALAR):
        kalan = bitis - time.time()
        if kalan <= 1:
            son_durum = f"süre aşıldı ({butce_s:.0f} s), son durum: {son_durum}"
            break
        dla, dlo = _KOMSU_KAYMALAR[i]
        veri, durum = _soilgrids_ham(lat + dla, lon + dlo,
                                     timeout=int(min(SOILGRIDS_TIMEOUT, kalan)))
        if veri:
            mesafe = _mesafe_km(lat, lon, lat + dla, lon + dlo) if i else 0.0
            _onbellege("toprak", lat, lon,
                       {"veri": veri, "mesafe_km": round(mesafe, 1),
                        "_tarih": date.today().isoformat()})
            return SoilData(**veri), round(mesafe, 1), "ok"
        son_durum = durum
        if durum == "bos":
            # Sunucu cevap verdi, bu noktada gercekten deger yok -> komsuya kay.
            i += 1
            if i == len(_KOMSU_KAYMALAR):
                tamamlandi = True
        else:
            # Sunucuya ulasilamadi. Komsuya gecmek fayda etmez (ayni sunucu),
            # AYNI noktayi tekrar sor. Butce dolunca dongu yukarida kirilir.
            tum_bos = False
        time.sleep(max(0.0, min(1.0, bitis - time.time())))

    # Buraya sadece WCS'e ULASILAMADIGI durumda gelinir (WCS "bos" dediyse
    # yukarida donuldu). Yani bos sonuc yine ancak REST her denemede CEVAP
    # VERIP "degerim yok" dediyse yazilir; sessizlik kanit sayilmaz.
    if tum_bos and tamamlandi:
        _onbellege("toprak", lat, lon,
                   {"veri": None, "mesafe_km": None, "_tarih": date.today().isoformat()})
        return None, None, "ok"
    if son_durum == "bilinmiyor":
        son_durum = f"WCS: {wcs_durum}"
    return None, None, son_durum


def surum_katmani_al(lat: float, lon: float) -> tuple[SoilData | None, str]:
    """Besin karnesi icin 0-30 cm agirlikli toprak. Onbellekli.

    Neden ayri onbellek: bu, /toprak'in verdigi 0-5 cm katmanindan BASKA bir
    olcumdur, ayni koordinatta iki sayi birden vardir ve ayni dosyaya yazmak
    birini otekinin uzerine yazardi. Uc derinlik cekildigi icin ilk sorgu ~5 s
    surer (olculdu: Karacabey 4.6 s, Harran 5.6 s); sonrasi diskten gelir.

    Bos sonuc kalici YAZILMAZ: toprak katmaninda ogrenilen kural (gecici
    arizanin sonsuza kadar "veri yok" olarak donmasi) burada da gecerli.
    """
    onb = _onbellekten("besin", lat, lon)
    if onb and onb.get("veri"):
        return SoilData(**onb["veri"]), "ok"

    toprak, durum = wcs_surum_katmani(lat, lon)
    if toprak is not None:
        _onbellege("besin", lat, lon,
                   {"veri": toprak.model_dump(exclude_none=True),
                    "_tarih": date.today().isoformat()})
    return toprak, durum


def toprak_al(lat: float, lon: float) -> tuple[SoilData | None, float | None]:
    """Geriye donuk uyumluluk sarmalayicisi (durum bilgisi gerekmeyen cagrilar)."""
    toprak, mesafe, _durum = toprak_al_durum(lat, lon)
    return toprak, mesafe


def yukselti_al(lat: float, lon: float) -> float | None:
    try:
        r = requests.get(ELEVATION_URL, params={"latitude": lat, "longitude": lon},
                         headers=UA, timeout=20)
        return float(r.json()["elevation"][0])
    except Exception:
        return None


def yer_adi_al(lat: float, lon: float) -> tuple[str | None, str | None, bool]:
    """(yer adi, ulke, karada mi). Nominatim denizde 'Unable to geocode' donuyor."""
    onb = _onbellekten("yer", lat, lon)
    if onb is not None:
        return onb.get("ad"), onb.get("ulke"), onb.get("karada", True)
    try:
        r = requests.get(NOMINATIM_URL, headers=UA, timeout=25,
                         params={"format": "json", "lat": lat, "lon": lon, "zoom": 10})
        j = r.json()
        if "error" in j:
            sonuc = (None, None, False)
        else:
            adres = j.get("address", {})
            sonuc = (j.get("display_name"), adres.get("country"), True)
    except Exception:
        return None, None, True  # bilinmiyor; karada varsay, akisi durdurma

    _onbellege("yer", lat, lon, {"ad": sonuc[0], "ulke": sonuc[1], "karada": sonuc[2]})
    return sonuc


def _poligon_alan_m2(noktalar: list[tuple[float, float]]) -> float | None:
    """Kucuk poligonlar icin duzlem yaklasimi (ayakkabi baglama formulu)."""
    if len(noktalar) < 3:
        return None
    lat0 = sum(p[0] for p in noktalar) / len(noktalar)
    m_lat = 111_320.0
    m_lon = 111_320.0 * math.cos(math.radians(lat0))
    xy = [(lon * m_lon, lat * m_lat) for lat, lon in noktalar]
    top = 0.0
    for i in range(len(xy)):
        x1, y1 = xy[i]
        x2, y2 = xy[(i + 1) % len(xy)]
        top += x1 * y2 - x2 * y1
    return abs(top) / 2.0


def _overpass_sor(sorgu: str) -> tuple[list[dict] | None, str]:
    """Aynalari sirayla dener. Doner: (elemanlar, durum).

    elemanlar None ise HICBIR sunucu cevap vermedi; bu "parsel yok" DEMEK DEGIL.
    Bu ayrimi yapmak sart: olcumde ayni sorgu tek basina 60 parsel dondururken
    arka arkaya calistirilinca 429 yiyip 0 donuyordu ve biz buna yanlislikla
    "bu bolge haritalanmamis" diyorduk.

    BOS SONUC TEK AYNAYA GUVENILMEZ. Dolu cevap kendini kanitlar (veri iste
    ortada). Bos cevap ise bir YOKLUK IDDIASIDIR ve sessiz arizadan ayirt
    edilemez: olcumde overpass.osm.ch Isvicre disindaki her sorguya HTTP 200 ile
    bos liste donduruyordu ve biz buna "bu bolge haritalanmamis" diyorduk. O ayna
    listeden cikarildi ama risk yapisaldir; herhangi bir ayna bolgesel olabilir.
    Bu yuzden bos cevap ikinci bir aynaya DOGRULATILIR:
      ikisi de bos            -> "ok", gercekten parsel yok
      ikincisi dolu           -> ilki yaniltiyordu, dolu cevap kullanilir
      ikincisi cevap veremedi -> "dogrulanamadi", yani BILINMIYOR ("yok" degil)
    """
    bitis = time.time() + PARSEL_BUTCE_S
    son_hata = "bilinmiyor"
    bos_diyen: str | None = None      # bos liste donduren ilk ayna
    for url in OVERPASS_AYNALAR:
        if bos_diyen == url:
            continue                  # zaten bos dedi, ayni cevabi tekrar sorma
        for deneme in range(OVERPASS_DENEME):
            # Kalan butce kadar bekle, daha fazla degil. Boylece toplam sure
            # ayna x deneme ile carpilarak 200 s'ye cikamaz.
            kalan = bitis - time.time()
            if kalan <= 1:
                return None, f"sure asildi ({PARSEL_BUTCE_S} s), son durum: {son_hata}"
            try:
                r = requests.post(url, data={"data": sorgu}, headers=UA,
                                  timeout=min(OVERPASS_TIMEOUT, kalan))
                if r.status_code == 200:
                    veri = r.json()
                    # Overpass, sorgu kendi calisma sinirini asarsa HTTP 200 ile
                    # EKSIK liste dondurur ve durumu sadece "remark" alanina yazar.
                    # Bu alani okumazsak yarim listeyi tam sanip "bolgede sadece
                    # 2 parsel var" deriz. Eksik liste = cevap alinamamis sayilir.
                    uyari = veri.get("remark")
                    if uyari:
                        son_hata = f"kismi sonuc: {uyari[:60]}"
                    else:
                        elemanlar = veri.get("elements", [])
                        if elemanlar:
                            return elemanlar, "ok"     # dolu cevap kendini kanitlar
                        if bos_diyen is None:
                            # Ilk "bos" cevabi. Yokluk iddiasi, dogrulanmasi gerek.
                            bos_diyen = url
                            son_hata = "bos cevap dogrulanmadi"
                            break                      # sonraki aynaya gec
                        return [], "ok"                # iki ayri ayna bos dedi
                else:
                    son_hata = f"HTTP {r.status_code}"
                    # 429 disindaki hatalarda beklemek ise yaramaz, ayna degistir
                    if r.status_code != 429:
                        break
            except ValueError:
                # Govde JSON olarak cozulemedi. Olctuk: sunucu yuk altinda HTTP 200
                # verip govdeyi ORTADAN KESIYOR (Nakuru sorgusu 5047 baytta kesildi,
                # gecerli JSON'un yarisi). Gecici bir durum, ayni aynayi tekrar
                # denemek ise yarar; bu yuzden aynayi hemen birakmiyoruz.
                son_hata = "govde kesik (JSON cozulemedi)"
            except Exception as exc:
                son_hata = type(exc).__name__
                break
            # Beklemek de butceden yer: kalan sureden fazla uyuma.
            if deneme < OVERPASS_DENEME - 1:
                time.sleep(max(0.0, min(5.0, bitis - time.time())))
    if bos_diyen is not None:
        # Bir ayna bos dedi ama hicbir ayna bunu dogrulayamadi. "Yok" DIYEMEYIZ.
        return None, "bos cevap dogrulanamadi (parsel olup olmadigi bilinmiyor)"
    return None, son_hata


def parselleri_al(lat: float, lon: float, yaricap_m: int = 2500,
                  limit: int = 40) -> tuple[list[Parsel], str]:
    """Yakindaki OSM tarim alanlari. Doner: (parseller, durum).

    durum "ok"   -> sunucu cevapladi; liste bossa gercekten parsel yok
    durum digeri -> sunucuya ulasilamadi; parsel olup olmadigi BILINMIYOR

    Sorgu bilerek hafif tutuldu (dar yaricap + cikti limiti); genis sorgu 504 aliyor.
    """
    # Onbellekte SADECE basarili sorgular tutulur. Basarisiz sorguyu onbellege
    # yazmak, gecici bir 429'u kalici "parsel yok" yalanina cevirirdi.
    #
    # BOS SONUC KALICI YAZILMAZ. Olctuk, bu gercekten basimiza geldi: eski
    # osm.ch aynasi Iowa'ya bos liste dondurmustu, bu "ok" sayilip onbellege
    # yazilmisti ve ayna listeden cikarildiktan SONRA bile test "Iowa: kayitli
    # parsel yok" diyordu. Oysa Iowa'da 6 parsel var. Yani tek bir gecici ariza,
    # onbellek yuzunden kalici bir yalana donusmustu. Dolu sonuc kalici tutulur
    # (veri kendini kanitlar), bos sonuc PARSEL_BOS_TTL_GUN sonra yeniden sorulur.
    onb = _onbellekten("parsel", lat, lon)
    if onb is not None:
        p_listesi = onb["parseller"]
        taze = True
        if not p_listesi:
            yazim = onb.get("_tarih")
            taze = bool(yazim) and (date.today() - date.fromisoformat(yazim)).days \
                <= PARSEL_BOS_TTL_GUN
        if taze:
            return [Parsel(**p) for p in p_listesi], "ok"

    turler = "farmland|orchard|vineyard|greenhouse_horticulture|meadow"
    sorgu = (f'[out:json][timeout:25];'
             f'way[landuse~"^({turler})$"](around:{yaricap_m},{lat},{lon});'
             f'out geom {limit};')
    elemanlar, durum = _overpass_sor(sorgu)
    if elemanlar is None:
        return [], durum

    parseller: list[Parsel] = []
    for e in elemanlar:
        geom = e.get("geometry") or []
        noktalar = [(g["lat"], g["lon"]) for g in geom]
        if not noktalar:
            continue
        etiket = e.get("tags", {})
        tur = etiket.get("landuse", "?")
        parseller.append(Parsel(
            osm_id=e.get("id", 0),
            tur=tur,
            tur_tr=LANDUSE_TR.get(tur, tur),
            alan_m2=_poligon_alan_m2(noktalar),
            merkez_lat=sum(p[0] for p in noktalar) / len(noktalar),
            merkez_lon=sum(p[1] for p in noktalar) / len(noktalar),
            ad=etiket.get("name"),
            sinir=noktalar,
        ))
    parseller.sort(key=lambda p: p.alan_m2 or 0, reverse=True)
    # Yazim tarihi bos sonucun TTL kontrolu icin gerekli (yukaridaki gerekce).
    _onbellege("parsel", lat, lon,
               {"parseller": [asdict(p) for p in parseller],
                "_tarih": date.today().isoformat()})
    return parseller, "ok"


# --------------------------------------------------------------------------
# Ana giris
# --------------------------------------------------------------------------

def konum_ozeti(lat: float, lon: float, parsel_ara: bool = True,
                toprak_ara: bool = True,
                toprak_butce_s: float = SOILGRIDS_BUTCE_S) -> KonumOzeti:
    """Bir koordinatin tam tarimsal ozeti. Hicbir katman akisi durdurmaz.

    parsel_ara / toprak_ara: bu iki katman YAVASTIR (parsel 25 s'ye, toprak
    60 s'ye kadar) ve ikisi de zorunlu degildir. Web servisinde ayri uc
    noktalardan istenirler, burada kapatilabilmeleri onun icin.
    """
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"Gecersiz koordinat: {lat}, {lon}")

    from data.open_meteo import get_monthly_climate  # dairesel import olmasin

    ozet = KonumOzeti(lat=lat, lon=lon)

    ozet.yer_adi, ozet.ulke, ozet.karada = yer_adi_al(lat, lon)
    if not ozet.karada:
        ozet.eksik.append("Bu koordinat denizde, tarimsal veri uretilmedi")
        return ozet

    ozet.yukselti_m = yukselti_al(lat, lon)
    if ozet.yukselti_m is None:
        ozet.eksik.append("yukselti")

    if toprak_ara:
        ozet.toprak, ozet.toprak_kaynak_mesafe_km, ozet.toprak_durum = \
            toprak_al_durum(lat, lon, butce_s=toprak_butce_s)
        if ozet.toprak is None:
            if ozet.toprak_durum == "ok":
                ozet.eksik.append("toprak (SoilGrids bu noktada deger tutmuyor)")
            else:
                # Sunucuya ulasilamadi. "Toprak verisi yok" DEMEK DEGIL.
                ozet.eksik.append(
                    f"toprak sorgusu yapilamadi (SoilGrids: {ozet.toprak_durum}); "
                    "buranin toprak ozellikleri bilinmiyor"
                )

    # Iklim: 30 YILLIK NORMAL kullaniliyor, 1 yillik ozet degil.
    # Iki gerekce var, ikisi de olculdu:
    #   TUTARLILIK: oneri motoru get_monthly_climate() ile calisiyor. Konum
    #     kartinda get_climate() (son 1 yil) gostermek ayni ekranda iki farkli
    #     yagis sayisi uretiyordu; Antalya icin 906 mm ile 1059 mm arasi %15 fark.
    #     Kullanici "hangisi dogru" diye soramamali, tek sayi olmali.
    #   MALIYET: get_monthly_climate diske onbelleklenir ve oneri zaten onu
    #     cagiriyor. Burada get_climate cagirmak, ayni koordinat icin Open-Meteo
    #     arsivine IKINCI bir agir istek demekti; olcumde tam da bu ikinci istek
    #     429'a takilip API'yi HTTP 503'e dusurdu.
    # Bedeli: bagil nem kaybolur (gunluk normalde nem alani yok). Nem zaten
    # oneri motoruna girmiyor, sadece Antalya akisindaki GBDT modeli kullaniyor
    # ve o kendi get_climate cagrisini yapmaya devam ediyor.
    try:
        n = get_monthly_climate(lat, lon)
        sic = [t for t in n["ay_sicaklik"] if t is not None]
        ozet.iklim = ClimateData(
            temperature=round(sum(sic) / len(sic), 1) if sic else None,
            humidity=None,
            rainfall=n.get("yillik_yagis"),
        )
    except Exception as exc:
        ozet.eksik.append(f"iklim alinamadi (Open-Meteo: {type(exc).__name__})")

    if parsel_ara:
        ozet.parseller, ozet.parsel_durum = parselleri_al(lat, lon)
        if ozet.parsel_durum != "ok":
            # Sunucu cevap vermedi. "Parsel yok" DEMEK DEGIL; oyle yazmak yalan olur.
            ozet.eksik.append(
                f"parsel sorgusu yapilamadi (Overpass: {ozet.parsel_durum}); "
                "burada parsel olup olmadigi bilinmiyor"
            )
        elif not ozet.parseller:
            ozet.eksik.append("kayitli parsel yok (OSM'de bu bolge haritalanmamis)")

    return ozet


# --------------------------------------------------------------------------
# Rastgele konum
# --------------------------------------------------------------------------

# Dunyanin baslica tarim havzalari: (ad, lat_min, lat_max, lon_min, lon_max).
# Tamamen rastgele koordinat secilirse ~%70 okyanus, ~%20 col/tundra cikar;
# kullaniciya bos ekran gosterir. Bu yuzden tarim yapilan kusaklardan seciyoruz.
TARIM_HAVZALARI = [
    ("Akdeniz havzasi", 35.0, 42.0, -6.0, 36.0),
    ("Bati Avrupa", 45.0, 54.0, -2.0, 16.0),
    ("ABD Ortabati", 38.0, 46.0, -100.0, -85.0),
    ("Kaliforniya vadisi", 35.0, 40.0, -122.0, -119.0),
    ("Brezilya guneyi", -30.0, -18.0, -55.0, -45.0),
    ("Arjantin Pampa", -38.0, -30.0, -64.0, -58.0),
    ("Hindistan kuzeyi", 24.0, 31.0, 74.0, 85.0),
    ("Cin dogusu", 30.0, 40.0, 112.0, 120.0),
    ("Dogu Afrika yaylalari", -3.0, 2.0, 34.0, 38.0),
    ("Guney Afrika", -30.0, -25.0, 25.0, 30.0),
    ("Avustralya guneydogu", -37.0, -33.0, 142.0, 148.0),
    ("Anadolu", 37.0, 41.0, 27.0, 42.0),
]


def rastgele_tarim_noktasi(deneme: int = 12, parsel_zorunlu: bool = False,
                           tohum: int | None = None,
                           parsel_ara: bool = True,
                           toprak_ara: bool = True) -> KonumOzeti:
    """Dunyanin rastgele bir tarim bolgesinden konum ozeti dondurur.

    parsel_zorunlu=True ise OSM'de parseli olan bir nokta bulunana kadar dener.
    Olculen gercek: bazi bolgelerde (orn. Sao Paulo) hic parsel yok, o yuzden
    varsayilan False; aksi halde arama bosuna uzardi.

    parsel_ara=False: web servisi icin. Onbellekte olmayan bir noktada parsel
    sorgusu PARSEL_BUTCE_S (25 s) surebiliyor ve burada 12 deneme yapiliyor,
    yani en kotu durumda 300 s. HTTP istegi bunu bekleyemez; parsel ayri uc
    noktadan istenir.
    """
    if parsel_zorunlu:
        parsel_ara = True      # parseli gormeden "parseli var" denemez
    rnd = random.Random(tohum)
    son: KonumOzeti | None = None
    for _ in range(deneme):
        ad, la1, la2, lo1, lo2 = rnd.choice(TARIM_HAVZALARI)
        lat = round(rnd.uniform(la1, la2), 5)
        lon = round(rnd.uniform(lo1, lo2), 5)
        ozet = konum_ozeti(lat, lon, parsel_ara=parsel_ara, toprak_ara=toprak_ara)
        if not ozet.karada:
            continue
        son = ozet
        if not parsel_zorunlu or ozet.parseller:
            return ozet
    if son is None:
        raise RuntimeError(f"{deneme} denemede karada nokta bulunamadi")
    return son
