"""Tarim Asistani HTTP servisi (FastAPI).

Calistirma:  py -m uvicorn api.main:app --reload --port 8000
Dokuman   :  http://127.0.0.1:8000/docs

TASARIM KARARLARI (olcume dayali, gerekceleri asagida):

1) YAVAS KATMANLAR (PARSEL VE TOPRAK) AYRI UC NOKTADIR.
   Olctuk: yer adi + yukselti + iklim katmanlari 1.4-5.1 s suruyor. Parsel
   sorgusu onbellekte yoksa Overpass butcesi kadar (25 s'ye kadar), SoilGrids
   ise 1-40 s arasi degisken (ayni sorgu 6 kez sorulunca: 40.4 zaman asimi,
   37.5, 40.4 zaman asimi, 27.2, 1.2, 22.8 saniye) surebiliyor. Hepsini tek
   yanitta birlestirmek tum ekrani en yavas katmanin hizina indirirdi; olcumde
   /konum boylece 46-49 saniye surdu.
   Bu yuzden /konum bu iki katmani BEKLEMEDEN doner; arayuz /toprak ve
   /parseller uc noktalarini ayrica ve sonradan cagirip ekrani doldurur.

2) UC NOKTALAR "async def" DEGIL "def".
   Icerideki her sey requests ile SENKRON HTTP yapiyor. async def icinde
   senkron bir istek olay dongusunu bloklar ve tek bir 25 saniyelik parsel
   sorgusu TUM sunucuyu durdururdu. Duz "def" kullanildiginda FastAPI islevi
   threadpool'a atar, diger istekler akmaya devam eder.

3) DIS SERVIS COKERSE BOS SONUC DONMEYIZ, HATA DONERIZ.
   Bu projede en cok zarar veren hata tipi tam olarak buydu: dis servis
   "basarili" derken eksik veri veriyor, biz de onu "veri yok" saniyoruz
   (Overpass 429 -> "parsel yok", EcoCrop bos KTMPR -> "dona dayanikli").
   Bu yuzden iklim verisi alinamazsa oneri uc noktasi bos liste degil HTTP 503
   dondurur. Bos liste "burada hicbir urun yetismez" demektir ve bu bir yalandir.
"""
from __future__ import annotations

import os
import time
from datetime import date

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from core.schemas import ClimateData, SoilData
from data.global_location import (
    SOILGRIDS_HIZLI_BUTCE_S,
    KonumOzeti,
    hazir_katmanlar,
    konum_ozeti,
    onbellekteki_yer_adi,
    parselleri_al,
    rastgele_tarim_noktasi,
    toprak_al_durum,
    yer_adi_al,
)
from data.one_cikan import ONE_CIKANLAR
from data.open_meteo import get_monthly_climate
from models.crop_reco.global_reco import AYLAR, bilgi_tabani, gruba_gore, urun_oner
from models.crop_reco.recommender import _texture_class
from models.disease.classifier import CROP_TR, label_display
from models.disease.classifier_onnx import (
    TeshisModelYok,
    is_available as teshis_hazir,
    predict as teshis_predict,
    status as teshis_durum,
)
from models.disease.tedavi import tedavi_bul

app = FastAPI(
    title="Tarım Asistanı API",
    description="Dünyanın herhangi bir koordinatı için toprak, iklim, parsel ve "
                "ürün önerisi. Tüm kaynaklar ücretsiz ve anahtarsızdır: "
                "SoilGrids (ISRIC), Open-Meteo, OpenStreetMap (Nominatim, Overpass), "
                "FAO EcoCrop.",
    version="0.1.0",
)

# Arayuz ayri porttan (React 5173 / Next 3000) geldigi icin tarayici CORS ister.
# Canli surumde ARAYUZ_KOKEN ile gercek alan adi verilir.
_KOKENLER = [k for k in os.getenv("ARAYUZ_KOKEN", "").split(",") if k] or [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:5173", "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_KOKENLER,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

LAT = Query(..., ge=-90, le=90, description="Enlem")
LON = Query(..., ge=-180, le=180, description="Boylam")


# --------------------------------------------------------------------------
# Yanit modelleri: arayuz tarafinin tipi /openapi.json'dan uretebilmesi icin
# --------------------------------------------------------------------------

class ParselYanit(BaseModel):
    osm_id: int
    tur: str
    tur_tr: str
    alan_m2: float | None = None
    alan_dekar: float | None = None
    merkez_lat: float | None = None
    merkez_lon: float | None = None
    ad: str | None = None
    sinir: list[tuple[float, float]] = Field(default_factory=list)


class ParsellerYanit(BaseModel):
    lat: float
    lon: float
    durum: str = Field(description='"ok" ise liste kesindir; boşsa gerçekten '
                                   'parsel yok. Başka bir değerse sunucuya '
                                   'ulaşılamadı, parsel olup olmadığı BİLİNMİYOR.')
    kesin: bool = Field(description='durum == "ok" mi. Arayüz boş listeyi '
                                    '"parsel yok" diye yazmadan önce buna bakmalı.')
    adet: int
    parseller: list[ParselYanit]
    sure_s: float


class ToprakYanit(BaseModel):
    lat: float
    lon: float
    durum: str = Field(description='"ok" ise sonuç kesindir. Başka bir değerse '
                                   'SoilGrids yanıt vermedi, toprak "yok" değil '
                                   'BİLİNMİYOR demektir.')
    kesin: bool
    toprak: SoilData | None = None
    kaynak_mesafe_km: float | None = Field(
        default=None,
        description="0 ise değer tam bu noktanın. Büyükse SoilGrids bu noktada "
                    "boştu ve değer bu kadar uzaktaki komşu noktadan alındı.")
    doku_sinifi: str | None = None
    sure_s: float


class KonumYanit(BaseModel):
    lat: float
    lon: float
    yer_adi: str | None = None
    ulke: str | None = None
    karada: bool = True
    yukselti_m: float | None = None
    toprak: SoilData | None = None
    toprak_kaynak_mesafe_km: float | None = Field(
        default=None,
        description="Toprak verisi tam noktadan gelmediyse kaç km uzaktan alındığı")
    toprak_durum: str = Field(
        default="sorgulanmadi",
        description='Bu uç noktada normalde "sorgulanmadi" olur: toprak yavaş '
                    'katmandır ve /toprak uç noktasından ayrıca istenir.')
    iklim: ClimateData | None = Field(
        default=None,
        description="30 yıllık normal. Öneri motorunun kullandığı sayının "
                    "aynısıdır; nem alanı bu kaynakta yoktur.")
    eksik: list[str] = Field(default_factory=list)
    sure_s: float


class OneriYanit(BaseModel):
    urun: str
    ad: str
    bilimsel_ad: str = ""
    grup: str = ""
    skor: float
    uygunluk: str
    cok_yillik: bool
    ekim_ayi: str | None = None
    hasat_ayi: str | None = None
    ekim_aylari: list[str] = Field(
        default_factory=list,
        description="İklim olarak ekilebilir bulunan TÜM aylar: en iyi ekim "
                    "ayının puanının %95'inden aşağı düşmeyen aylar. Çok "
                    "yıllıklarda boştur, çünkü ağaç ekilmez fidan dikilir ve "
                    "dikim zamanı EcoCrop'ta yoktur. Bu bir EKİM TAKVİMİ "
                    "DEĞİLDİR: yalnızca sıcaklık uygunluğudur, vernalizasyon "
                    "ve gün uzunluğu hesaba girmez.")
    merkezlik: float = Field(
        default=0.0,
        description="Ölçülen değerlerin ürünün optimum aralığının neresinde "
                    "durduğu: 1.0 tam ortası, 0.0 kenarı. PUANA DAHİL DEĞİLDİR; "
                    "EcoCrop optimum aralığın içini eşit derecede uygun sayar. "
                    "Aynı puanı alan ürünleri ayırt etmek içindir.")
    su_acigi_mm: int = 0
    uygunluk_gaez: float | None = Field(
        default=None,
        description="FAO GAEZ v4 Suitability Index (0-100), bu koordinatta bu "
                    "ürünün ne kadar iyi yetiştiğinin bölgesel ölçümü. Skor "
                    "buradan 0.7 ağırlıkla hesaba girer; EcoCrop trapezoidinin "
                    "sıkıştırdığı 90-100 aralığını bölgesel gerçeklikle açar. "
                    "None ise GAEZ'de bu ürüne eşleme yok veya konum GAEZ "
                    "yüksek çözünürlük bölgesi (20-48 E, 33-44 N) dışında.")
    faktorler: list[dict] = Field(default_factory=list)
    uyarilar: list[str] = Field(default_factory=list)
    sezon: str = ""
    notlar: str = ""


class IklimOzet(BaseModel):
    yillik_yagis_mm: float | None = None
    en_sicak_ay_c: float | None = None
    en_soguk_ay_c: float | None = None
    mutlak_min_c: float | None = None
    yil_sayisi: int = 0
    ay_sicaklik: list[float | None] = Field(default_factory=list)
    ay_yagis: list[float | None] = Field(default_factory=list)


class OneriKumesi(BaseModel):
    lat: float
    lon: float
    yer_adi: str | None = None
    ulke: str | None = None
    toprak: SoilData | None = None
    toprak_var: bool = Field(
        description="False ise puanlama SADECE iklime dayanır, pH ve doku "
                    "faktörleri hesaba girmemiştir.")
    toprak_durum: str = Field(
        description='Toprak yoksa nedeni: "ok" gerçekten veri yok, başka bir '
                    'değer SoilGrids\'e ulaşılamadı.')
    iklim: IklimOzet
    toplam_uygun: int = Field(description="Elenmeden kalan ürün sayısı")
    su_anki_ay: str = Field(
        description="Sunucunun bulunduğu takvim ayı. Arayüz 'şimdi ekilebilir' "
                    "ile 'mevsiminde ekilebilir' ayrımını buna göre yapar. "
                    "Sunucudan gelir çünkü ayrım bir veri sonucudur, kullanıcı "
                    "cihazının saatine bırakılmamalıdır.")
    oneriler: list[OneriYanit]
    sure_s: float


# --------------------------------------------------------------------------
# Yardimcilar
# --------------------------------------------------------------------------

def _iklim_ozet(iklim: dict) -> IklimOzet:
    sic = [t for t in iklim["ay_sicaklik"] if t is not None]
    return IklimOzet(
        yillik_yagis_mm=iklim.get("yillik_yagis"),
        en_sicak_ay_c=max(sic) if sic else None,
        en_soguk_ay_c=min(sic) if sic else None,
        mutlak_min_c=iklim.get("mutlak_min"),
        yil_sayisi=iklim.get("yil_sayisi", 0),
        ay_sicaklik=iklim["ay_sicaklik"],
        ay_yagis=iklim["ay_yagis"],
    )


class _Girdi(BaseModel):
    toprak: SoilData
    toprak_var: bool
    toprak_durum: str
    iklim: dict
    yer_adi: str | None = None
    ulke: str | None = None


def _girdi_topla(lat: float, lon: float) -> _Girdi:
    """Oneri motorunun ihtiyaci olan toprak + iklim + yer adi.

    Iklim ZORUNLUDUR: alinamazsa hata yukseltilir (bkz modul basligi, madde 3).
    Toprak ise opsiyoneldir: SoilGrids bazi karelerde deger tutmuyor, ama iklim
    tek basina da anlamli bir siralama uretir. Eksikligi yanitta toprak_var ve
    toprak_durum ile ACIKCA bildirilir, sessizce yutulmaz.
    """
    try:
        iklim = get_monthly_climate(lat, lon)
    except Exception as exc:
        # SUNUCUNUN KENDI GEREKCESI YAZILIR, istisna sinifinin adi degil.
        # Onceden "Open-Meteo: RuntimeError" yaziyordu ve bu kullaniciya hicbir
        # sey anlatmiyordu. Olctuk: gercek sebep "Hourly API request limit
        # exceeded. Please try again in the next hour." idi; yani servis bozuk
        # degil, kota dolmus ve bir saat sonra kendiliginden aciliyor. Bu ikisi
        # kullanici icin taban tabana zit iki durum.
        gerekce = str(exc) or type(exc).__name__
        raise HTTPException(
            status_code=503,
            detail=f"İklim verisi alınamadı ({gerekce}). İklim olmadan ürün "
                   f"önerisi üretilemez; boş liste döndürmek 'burada hiçbir "
                   f"ürün yetişmez' anlamına gelirdi.",
        ) from exc

    # Toprak icin KISA butce. Gerekce: pH ve doku puanlamada ikincil agirliktadir
    # (0.6 ve 0.4; sicaklik 1.0, yagis 0.9), yani toprak gelmezse siralama yine
    # anlamlidir. Buna karsilik SoilGrids'i tam butceyle beklemek onerileri
    # 60 saniyeye kadar geciktirebilir. Toprak gelmediyse yanitta toprak_var=False
    # ve toprak_durum ile bildirilir; arayuz /toprak uc noktasi dolunca oneriyi
    # tazeler. Sessizce "toprak yok" varsayilmaz.
    toprak, _mesafe, durum = toprak_al_durum(lat, lon, butce_s=SOILGRIDS_HIZLI_BUTCE_S)
    yer, ulke, _karada = yer_adi_al(lat, lon)
    return _Girdi(toprak=toprak or SoilData(), toprak_var=toprak is not None,
                  toprak_durum=durum, iklim=iklim, yer_adi=yer, ulke=ulke)


def _parsel_yanit(p) -> ParselYanit:
    return ParselYanit(
        osm_id=p.osm_id, tur=p.tur, tur_tr=p.tur_tr,
        alan_m2=round(p.alan_m2, 1) if p.alan_m2 else None,
        # Ciftci dekar konusur, metrekare degil. 1 dekar = 1000 m2.
        alan_dekar=round(p.alan_m2 / 1000, 2) if p.alan_m2 else None,
        merkez_lat=p.merkez_lat, merkez_lon=p.merkez_lon,
        ad=p.ad, sinir=p.sinir,
    )


def _konum_yanit(ozet: KonumOzeti, sure: float) -> KonumYanit:
    return KonumYanit(
        lat=ozet.lat, lon=ozet.lon, yer_adi=ozet.yer_adi, ulke=ozet.ulke,
        karada=ozet.karada, yukselti_m=ozet.yukselti_m, toprak=ozet.toprak,
        toprak_kaynak_mesafe_km=ozet.toprak_kaynak_mesafe_km,
        toprak_durum=ozet.toprak_durum,
        iklim=ozet.iklim, eksik=ozet.eksik, sure_s=round(sure, 2),
    )


# --------------------------------------------------------------------------
# Uc noktalar
# --------------------------------------------------------------------------

@app.get("/saglik", tags=["servis"], summary="Servis ayakta mı")
def saglik() -> dict:
    kb = bilgi_tabani()
    return {
        "durum": "ayakta",
        "urun_sayisi": len(kb),
        "cok_yillik_sayisi": sum(1 for u in kb.values() if u.get("cok_yillik")),
    }


@app.get("/konum", response_model=KonumYanit, tags=["konum"],
         summary="Koordinatın tarımsal kimlik kartı (parsel hariç)")
def konum(lat: float = LAT, lon: float = LON) -> KonumYanit:
    """Yer adı, ülke, yükselti ve 30 yıllık iklim normali.

    Toprak ve parsel BİLEREK dahil edilmez, ayrı uç noktalardadır (bkz modül
    başlığı, madde 1). Hiçbir katman akışı durdurmaz; gelmeyen katmanlar
    `eksik` listesinde isimleriyle bildirilir, sessizce boş geçilmez.
    """
    t0 = time.time()
    try:
        ozet = konum_ozeti(lat, lon, parsel_ara=False, toprak_ara=False)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _konum_yanit(ozet, time.time() - t0)


@app.get("/toprak", response_model=ToprakYanit, tags=["konum"],
         summary="Toprak özellikleri (SoilGrids, ISRIC)")
def toprak(lat: float = LAT, lon: float = LON) -> ToprakYanit:
    """Ayrı uç noktadır çünkü SoilGrids gecikmesi ölçümde 1-40 saniye arası.

    `durum` alanını okumadan boş toprağı yorumlamayın: "ok" değilse bu
    "burada toprak verisi yok" DEĞİL, "sunucuya ulaşılamadı" demektir.
    Sonuç bir kez alındığında diske yazılır, aynı 1 km hücresi bir daha
    beklemez.
    """
    t0 = time.time()
    veri, mesafe, durum = toprak_al_durum(lat, lon)
    return ToprakYanit(
        lat=lat, lon=lon, durum=durum, kesin=(durum == "ok"),
        toprak=veri, kaynak_mesafe_km=mesafe,
        doku_sinifi=_texture_class(veri) if veri else None,
        sure_s=round(time.time() - t0, 2),
    )


@app.get("/parseller", response_model=ParsellerYanit, tags=["konum"],
         summary="Yakındaki tarım parselleri (OpenStreetMap)")
def parseller(
    lat: float = LAT,
    lon: float = LON,
    yaricap_m: int = Query(2500, ge=200, le=10000,
                           description="Arama yarıçapı. Geniş yarıçap Overpass'ta "
                                       "504 aldığı için üst sınır 10 km."),
    limit: int = Query(40, ge=1, le=200),
) -> ParsellerYanit:
    """Ayrı uç noktadır çünkü önbellekte yoksa 25 saniyeye kadar sürebilir.

    `durum` alanını okumadan boş listeyi yorumlamayın: "ok" değilse liste boş
    olsa bile bu "parsel yok" demek DEĞİLDİR, "sunucuya ulaşılamadı" demektir.
    """
    t0 = time.time()
    liste, durum = parselleri_al(lat, lon, yaricap_m=yaricap_m, limit=limit)
    return ParsellerYanit(
        lat=lat, lon=lon, durum=durum, kesin=(durum == "ok"),
        adet=len(liste), parseller=[_parsel_yanit(p) for p in liste],
        sure_s=round(time.time() - t0, 2),
    )


@app.get("/oneri", response_model=OneriKumesi, tags=["öneri"],
         summary="Bu koordinatta ne yetişir (FAO EcoCrop)")
def oneri(
    lat: float = LAT,
    lon: float = LON,
    adet: int = Query(20, ge=1, le=200, description="Kaç ürün dönsün"),
    grup: str | None = Query(None, description="Tek bir ürün grubuyla sınırla "
                                               "(tahıl, sebze, meyve ...)"),
) -> OneriKumesi:
    """Sıralama 30 yıllık iklim normali + SoilGrids toprağı ile hesaplanır.

    Puan bir UYGUNLUK puanıdır, karlılık değildir: pazar fiyatı, sözleşmeli
    tarım ve sulama altyapısı EcoCrop'ta yoktur. "Burada ne yetişir" sorusunu
    yanıtlar, "burada en çok ne kazandırır" sorusunu değil.
    """
    t0 = time.time()
    g = _girdi_topla(lat, lon)

    hepsi = urun_oner(g.toprak, g.iklim, adet=10_000, lat=lat, lon=lon)
    secili = [r for r in hepsi if r["grup"] == grup] if grup else hepsi

    return OneriKumesi(
        lat=lat, lon=lon, yer_adi=g.yer_adi, ulke=g.ulke,
        toprak=g.toprak if g.toprak_var else None, toprak_var=g.toprak_var,
        toprak_durum=g.toprak_durum,
        iklim=_iklim_ozet(g.iklim),
        toplam_uygun=len(secili),
        su_anki_ay=AYLAR[date.today().month - 1],
        oneriler=[OneriYanit(**r) for r in secili[:adet]],
        sure_s=round(time.time() - t0, 2),
    )


@app.get("/oneri/gruplar", tags=["öneri"],
         summary="Her ürün grubundan en iyi N ürün")
def oneri_gruplar(
    lat: float = LAT,
    lon: float = LON,
    grup_basina: int = Query(3, ge=1, le=20),
) -> dict:
    """Sadece tepe listeyi göstermek çiftçiyi tek gruba boğuyor (hepsi meyve
    çıkabiliyor). Gerçek seçenek sunmak için gruplar ayrı ayrı döner.
    """
    t0 = time.time()
    g = _girdi_topla(lat, lon)
    gruplar = gruba_gore(g.toprak, g.iklim, grup_basina=grup_basina, lat=lat, lon=lon)
    return {
        "lat": lat, "lon": lon, "yer_adi": g.yer_adi, "ulke": g.ulke,
        "toprak_var": g.toprak_var, "toprak_durum": g.toprak_durum,
        "iklim": _iklim_ozet(g.iklim).model_dump(),
        "gruplar": {g: [OneriYanit(**r).model_dump() for r in l]
                    for g, l in gruplar.items()},
        "sure_s": round(time.time() - t0, 2),
    }


@app.get("/rastgele", response_model=KonumYanit, tags=["konum"],
         summary="Dünyanın rastgele bir tarım bölgesinden konum")
def rastgele(
    tohum: int | None = Query(None, description="Aynı noktayı tekrar üretmek için"),
    deneme: int = Query(12, ge=1, le=30),
) -> KonumYanit:
    """Tamamen rastgele koordinat ~%70 okyanus çıkardığı için seçim dünyanın
    başlıca tarım havzalarıyla sınırlıdır.

    Toprak ve parsel aranmaz: 12 deneme x (25 s parsel + 60 s toprak) bütçesi en
    kötü durumda 17 dakika ederdi. Nokta döndükten sonra /toprak ve /parseller
    ayrıca çağrılır.
    """
    t0 = time.time()
    try:
        ozet = rastgele_tarim_noktasi(deneme=deneme, tohum=tohum,
                                      parsel_ara=False, toprak_ara=False)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _konum_yanit(ozet, time.time() - t0)


class KisayolYanit(BaseModel):
    kisayol_ad: str = Field(
        description="Listeyi hazırlarken düştüğüm not. VERİ DEĞİLDİR, sadece "
                    "düğmenin üstünde yazan etikettir.")
    yer_adi: str | None = Field(
        default=None,
        description="OpenStreetMap'ten gelen gerçek yer adı. Önbellekte yoksa "
                    "null döner; uydurulmaz. Arayüz null ise kisayol_ad yazar.")
    ulke: str | None = None
    lat: float
    lon: float
    hazir_katmanlar: list[str] = Field(
        description='Önbellekte gerçekten bulunan katmanlar: "yer", "iklim", '
                    '"toprak", "parsel". Eksik olan katman düğmeye basınca '
                    "canlı sorgulanır, yani o katman yavaş açılır.")
    isitildi: bool = Field(
        description='Dördü de hazır mı. False ise düğme YİNE ÇALIŞIR, sadece '
                    "eksik katmanlar beklenir. Bu alan yer adının varlığına "
                    "değil dört katmanın hepsine bakar.")


@app.get("/kisayollar", response_model=list[KisayolYanit], tags=["konum"],
         summary="Önbelleği hazır olan hızlı erişim noktaları")
def kisayollar() -> list[KisayolYanit]:
    """Ücretsiz barındırmada disk kalıcı olmadığı için bu noktaların önbelleği
    depoya gömülüdür ve kutudan çıkar çıkmaz hazır gelir.

    BU LİSTE UYGULAMAYI HIZLANDIRMAZ. Önbellek anahtarı koordinatı yaklaşık
    1 km'lik hücreye yuvarlar; dünyanın kara yüzeyi ~149 milyon km2. Birkaç
    düzine nokta rastgele bir tıklamayı yakalamaz. Sadece BURADAKİ noktalar
    anında gelir. Bu yüzden arayüzde "popüler" ya da "önerilen" diye değil,
    hızlı erişim kısayolu olarak sunulur.

    Ağ isteği yapmaz: yer adı yalnızca önbellekte varsa doldurulur.
    """
    liste: list[KisayolYanit] = []
    for notum, lat, lon in ONE_CIKANLAR:
        ad, ulke = onbellekteki_yer_adi(lat, lon)
        hazir = hazir_katmanlar(lat, lon)
        liste.append(KisayolYanit(
            kisayol_ad=notum, yer_adi=ad, ulke=ulke, lat=lat, lon=lon,
            hazir_katmanlar=hazir,
            # DORT KATMANIN DORDU. Yer adinin varligina bakmak yetmiyordu:
            # yer adi onbellekte olup iklimi olmayan noktalarda "hazir"
            # yazip acilmiyordu.
            isitildi=len(hazir) == 4,
        ))
    return liste


@app.get("/urunler", tags=["öneri"], summary="Bilgi tabanındaki tüm ürünler")
def urunler() -> dict:
    """Arayüzdeki grup filtresi ve ürün arama kutusu bunu kullanır.

    `don_dinlenme_kaynak` alanı kasıtlı olarak dışarı verilir: kış dayanıklılığı
    değerlerinin bir kısmı EcoCrop'ta boş olduğu için elle tamamlandı ve hangi
    değerin nereden geldiği gizlenmemelidir.
    """
    kb = bilgi_tabani()
    liste = [{
        "urun": k,
        "ad": u["ad"],
        "bilimsel_ad": u.get("bilimsel_ad", ""),
        "grup": u.get("grup", ""),
        "cok_yillik": bool(u.get("cok_yillik")),
        "sicaklik": u["sicaklik"],
        "yagis_mm": u["yagis_mm"],
        "ph": u["ph"],
        "don_dinlenme_c": u.get("don_dinlenme_c"),
        "don_dinlenme_kaynak": u.get("don_dinlenme_kaynak"),
    } for k, u in sorted(kb.items(), key=lambda x: x[1]["ad"])]
    gruplar = sorted({u["grup"] for u in liste if u["grup"]})
    return {"adet": len(liste), "gruplar": gruplar, "urunler": liste}


# --------------------------------------------------------------------------
# Hastalik teshis (yaprak fotografi -> etiket + tedavi)
# --------------------------------------------------------------------------
# ONNX FP32 model (77 MB) + onnxruntime. Torch canliya girmez. Model dosyasi
# yoksa (gelistirici surumu, model henuz commit edilmemis) uc nokta 503 doner;
# 500 degil, cunku eksik dosya sunucu hatasi degil kurulum eksigi.

MAX_TESHIS_BYTES = 6 * 1024 * 1024  # 6 MB. Mobil kamera JPEG'i 2-4 MB, yer var.


class TopKMadde(BaseModel):
    etiket: str = Field(..., description="Model etiketi, ornek 'domates_erken_yaniklik'.")
    guven: float = Field(..., ge=0.0, le=1.0)


class TedaviKaydi(BaseModel):
    ad: str
    konak: list[str] = []
    belirti: str = ""
    dogal: str = ""
    kimyasal: str = ""
    korunma: str = ""


class TeshisYanit(BaseModel):
    """Yaprak fotografindan hastalik teshis sonucu.

    seviye anlami:
      - kesin: yuksek guven + margin (dogrudan tedavi one cikar)
      - olasi: orta guven veya cekismeli iki sinif (kullaniciya alternatif goster)
      - belirsiz: guven cok dusuk (yeni foto iste)
      - tanimsiz: model 'diger' dedi (hedef urunlerden biri degil)
    """
    etiket: str = Field(..., description="Model etiketi (ASCII, snake_case).")
    etiket_tr: str = Field(..., description="Turkce ad, kullanicida gosterilir.")
    guven: float = Field(..., ge=0.0, le=1.0)
    margin: float = Field(..., description="Top1 - Top2 guven farki.")
    seviye: str = Field(..., description="kesin | olasi | belirsiz | tanimsiz")
    belirsiz: bool
    sebep: str | None = Field(None, description="hedef_disi | cekismeli | orta_guven | guven_dusuk")
    urun: str | None = Field(None, description="Tahmin edilen urun grubu (ornek 'domates').")
    urun_tr: str | None
    urun_guven: float
    topk: list[TopKMadde]
    tedavi: TedaviKaydi | None = Field(None, description="treatments.yaml kaydi. Saglikli/tanimsiz icin null.")
    uyari: str | None = Field(None, description="Seviyeye gore kullaniciya mesaj.")


def _uyari_metni(seviye: str, sebep: str | None) -> str | None:
    """Seviye + sebebe gore kisa mesaj. Sabit metinler; i18n yok (TR tek dil)."""
    if seviye == "kesin":
        return None
    if seviye == "olasi":
        if sebep == "cekismeli":
            return "İki hastalık benzer görünüyor. Alt seçenekleri de kontrol edin."
        return "Orta güven. Farklı bir yapraktan ikinci bir fotoğraf çekmeniz önerilir."
    if seviye == "belirsiz":
        return "Güven düşük. Yaprağı ışıkta ve yakından, tek yaprağa odaklanarak yeniden çekin."
    if seviye == "tanimsiz":
        return "Model bu görüntüyü desteklenen ürünlerden biri olarak tanımadı. Desteklenen ürünler: " + ", ".join(sorted(CROP_TR.values())) + "."
    return None


@app.post("/teshis", response_model=TeshisYanit, tags=["teshis"],
          summary="Yaprak fotoğrafından hastalık teşhisi (ONNX)")
async def teshis(dosya: UploadFile = File(..., description="Yaprak fotoğrafı (JPG/PNG).")) -> TeshisYanit:
    """Yaprak fotoğrafı yükle, hastalık etiketi + tedavi kaydı al.

    Boyut sınırı 6 MB, MIME tipi image/* olmalıdır. Yanıt sözleşmesi TeshisYanit.
    """
    # 1) MIME kontrolu. UploadFile.content_type "image/jpeg", "image/png" gibi.
    #    Bosluk / farkli tip gelirse 415 doner (400 degil; icerik tipi hatasi).
    ct = (dosya.content_type or "").lower()
    if not ct.startswith("image/"):
        raise HTTPException(415, f"Görüntü dosyası bekleniyor, alınan: {ct or 'bilinmiyor'}")

    # 2) Model hazir mi? Dosya veya onnxruntime yoksa 503. Kullaniciya net mesaj.
    if not teshis_hazir():
        raise HTTPException(503, f"Teşhis modeli hazır değil: {teshis_durum()}")

    # 3) Baytlari oku. UploadFile.read() bellekten olsa da tamamini yukleyip
    #    boyut sinirina uymayan istegi kestik: UploadFile.file.seek(0, 2)
    #    ile once size'i alabilirdik ama SpooledTemporaryFile'da her zaman
    #    calismiyor; okuma sonrasi len() kontrolu 6 MB tavani icin yeterli.
    veri = await dosya.read()
    if len(veri) > MAX_TESHIS_BYTES:
        raise HTTPException(
            413, f"Dosya çok büyük: {len(veri)/1024/1024:.1f} MB (üst sınır 6 MB)"
        )
    if not veri:
        raise HTTPException(400, "Dosya boş")

    # 4) Cikarim. Model bozuksa (dosya var ama okunamaz) TeshisModelYok atar,
    #    Pillow gecerli imaj degilse UnidentifiedImageError -> 400'e cevrilir.
    try:
        sonuc = teshis_predict(veri)
    except TeshisModelYok as e:
        raise HTTPException(503, f"Teşhis modeli çalışmadı: {e}") from e
    except Exception as e:
        # PIL UnidentifiedImageError, decode hatasi vb. 400 kullanici hatasi.
        raise HTTPException(400, f"Görüntü çözülemedi: {type(e).__name__}: {e}") from e

    # 5) Zenginlestir: TR ad, urun TR, tedavi kaydi, uyari.
    tedavi_dict = tedavi_bul(sonuc["etiket"])
    return TeshisYanit(
        etiket=sonuc["etiket"],
        etiket_tr=label_display(sonuc["etiket"]),
        guven=sonuc["guven"],
        margin=sonuc["margin"],
        seviye=sonuc["seviye"],
        belirsiz=sonuc["belirsiz"],
        sebep=sonuc["sebep"],
        urun=sonuc["urun"],
        urun_tr=CROP_TR.get(sonuc["urun"]) if sonuc["urun"] else None,
        urun_guven=sonuc["urun_guven"],
        topk=[TopKMadde(**m) for m in sonuc["topk"]],
        tedavi=TedaviKaydi(**tedavi_dict) if tedavi_dict else None,
        uyari=_uyari_metni(sonuc["seviye"], sonuc["sebep"]),
    )


# --------------------------------------------------------------------------
# Arayuzu AYNI servisten sunmak
# --------------------------------------------------------------------------
# NEDEN: arayuzu ayri bir yere koyarsak (Pages, Netlify, Vercel) tarayici
# baska kokene istek atar ve CORS listesini elle guncel tutmak gerekir.
# Bu proje icin gereksiz bir kirilma noktasi: ikinci hesap, ikinci dagitim
# adimi ve her alan adi degisiminde sessizce bozulan bir arayuz. Ayni
# servisten sunuldugunda koken tek oldugu icin CORS hic devreye girmez.
#
# CORS ayari YINE DE DURUYOR: gelistirmede Vite 5173'te ayri calisiyor ve
# derlenmis dosya yok. Yani bu mount gelistirmede devre disi kalir.
#
# html=True: React tek sayfa uygulamasi. Kullanici /?lat=..&lon=.. adresini
# paylasip yeniledigi anda sunucuya o yol soruluyor; html=True olmasaydi 404
# donerdi ve "paylasilabilir sonuc" ozelligi kagit uzerinde kalirdi.
_ARAYUZ = Path(__file__).resolve().parent.parent / "web" / "dist"
if (_ARAYUZ / "index.html").exists():
    # Mount EN SONA yazilir. Starlette yollari kayit sirasina gore dener;
    # once yazilsaydi "/" altindaki her sey statik dosyaya gider, API uc
    # noktalari hic calismazdi.
    app.mount("/", StaticFiles(directory=_ARAYUZ, html=True), name="arayuz")
