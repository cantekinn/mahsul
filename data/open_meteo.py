"""Open-Meteo istemcisi: koordinattan iklim ozeti (ucretsiz, anahtarsiz).

Urun onerisi modeli sicaklik/nem/yagis ister. Bunlari son 1 yillik
gecmis veriden (archive API) ozetleyerek temsili deger uretiriz:
- temperature: yillik ortalama sicaklik (C)
- humidity: yillik ortalama bagil nem (%)
- rainfall: yillik toplam yagis (mm)
"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from core.schemas import ClimateData

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# 30 yillik normal sorgusu 11.000 gunluk kayit indirir ve Open-Meteo ucretsiz
# katmani bunu hizli tekrarlarken HTTP 429 ile reddediyor (olctuk: 5 nokta arka
# arkaya sorulunca 1. nokta bile 429 aldi). Iklim NORMALI tanimi geregi yavas
# degisen bir buyukluk: bir noktanin 30 yillik ortalamasi ertesi gun farkli
# cikmaz. Bu yuzden diske yaziyoruz. TTL 180 gun; yeni yil verisi eklendiginde
# normal yenilensin ama gunluk sorgu yuku olusmasin diye.
IKLIM_ONBELLEK = Path(__file__).resolve().parent / "_onbellek" / "iklim"
ONBELLEK_TTL_GUN = 180

# 429 GECICIDIR, TEK DENEMEDE PES ETMEK YANLIS SONUC URETIYOR.
# Olctuk: Manitoba (49.88, -97.15) icin API katmani HTTP 503 dondurdu, ayni
# sorgu 30 saniye sonra dogrudan yapilinca 2.08 s'de HTTP 200 verdi. Yani
# "iklim verisi alinamadi" hatasi gercek bir yoklugu degil, o anki istek
# yogunlugunu yansitiyordu. Ustel bekleme ile tekrar deniyoruz.
IKLIM_DENEME = 3
IKLIM_BEKLEME_S = 2.0     # 2, 4, 8 saniye


def _sunucu_gerekcesi(resp: requests.Response) -> str:
    """Open-Meteo hatanin SEBEBINI govdede yaziyor; onu ziyan etmeyelim.

    Olctuk: kota dolunca govde tam olarak sunu donuyor:
        {"error":true,"reason":"Hourly API request limit exceeded.
         Please try again in the next hour."}
    Sadece "HTTP 429" yazsaydik kullaniciya "servis bozuk" gibi gorunurdu.
    Oysa sunucu sorunun GECICI oldugunu ve NE KADAR surecegini soyluyor.
    Bu ikisi farkli seyler ve farkli davranis gerektiriyor.
    """
    try:
        sebep = resp.json().get("reason")
    except Exception:
        sebep = None
    return f"HTTP {resp.status_code}" + (f": {sebep}" if sebep else "")


def _arsiv_sor(params: dict, timeout: int) -> dict:
    """Arsiv API'sine 429/5xx durumunda ustel beklemeyle tekrar sorar."""
    son: Exception | None = None
    for deneme in range(IKLIM_DENEME):
        try:
            resp = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
            if resp.status_code in (429, 500, 502, 503, 504):
                son = RuntimeError(f"Open-Meteo {_sunucu_gerekcesi(resp)}")
                # SAATLIK KOTA DOLDUYSA TEKRAR DENEMEK ZARARLI. Bekleme
                # merdivenimiz en fazla 14 saniye; kota bir SAAT sonra
                # aciliyor. Denemeye devam etmek kullaniciyi 14 saniye bosuna
                # bekletir ve zaten dolu olan kotayi daha da doverdi. Olctuk:
                # 6 tur x 20 s araliklarla 7 dakika boyunca hep 429 geldi.
                if resp.status_code == 429:
                    raise son
            else:
                resp.raise_for_status()
                return resp.json()
        except requests.RequestException as exc:
            son = exc
        if deneme < IKLIM_DENEME - 1:
            time.sleep(IKLIM_BEKLEME_S * (2 ** deneme))
    raise son if son else RuntimeError("Open-Meteo yanit vermedi")


def get_climate(lat: float, lon: float, timeout: int = 20) -> ClimateData:
    """Verilen koordinat icin son ~1 yilin iklim ozetini dondurur."""
    end = date.today() - timedelta(days=7)   # arsiv verisi ~1 hafta gecikmeli
    start = end - timedelta(days=365)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,precipitation_sum",
        "hourly": "relative_humidity_2m",
        "timezone": "auto",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    temps = [t for t in daily.get("temperature_2m_mean", []) if t is not None]
    rains = [r for r in daily.get("precipitation_sum", []) if r is not None]
    hums = [h for h in data.get("hourly", {}).get("relative_humidity_2m", []) if h is not None]

    return ClimateData(
        temperature=round(sum(temps) / len(temps), 1) if temps else None,
        humidity=round(sum(hums) / len(hums), 1) if hums else None,
        rainfall=round(sum(rains), 1) if rains else None,
    )


def get_monthly_climate(lat: float, lon: float, yil: int = 30, timeout: int = 60) -> dict:
    """Aylik iklim normalleri. Kuresel urun onerisi icin ZORUNLU.

    NEDEN: get_climate() yillik ortalama sicaklik verir. EcoCrop esikleri ise
    YETISME DONEMI sicakligina gore tanimlidir. Olctuk: Iowa'nin yillik ortalamasi
    11.1 C ve bununla misir 91 urun icinde 64. sirada cikiyor. Oysa Iowa dunyanin
    misir merkezi. Sicak donem ortalamasiyla (22 C) misir 2. siraya cikiyor.
    Yani yillik ortalamayla urun onerisi yapmak olcuyle yanlis gosterildi.

    NEDEN 30 YIL: kisa pencere gurultulu. Olctuk (Antalya merkez, yillik yagis):
        5 yil -> 906 mm | 15 yil -> 1040 mm | 30 yil -> 1059 mm
    Yani sadece pencere secimi yuzunden %15 sapma. Bu sapma urun onerisini
    dogrudan bozuyordu (zeytinin ust yagis siniri 1200 mm). 30 yil WMO'nun
    iklim normali standardi ve olcumde EK MALIYETI YOK (5 yil 5.4 s, 30 yil 0.9 s;
    fark Open-Meteo onbelleginden geliyor). Uzun pencere ayrica mutlak minimumu
    daha guvenli veriyor (Iowa: 5 yilda -30.7, 30 yilda -34.2) ki cok yillik
    urunun don riski bununla elenir.

    Donen:
      ay_sicaklik     : 12 elemanli aylik ortalama sicaklik (C), 0=Ocak
      ay_min_sicaklik : 12 elemanli aylik ortalama GUNLUK MINIMUM (C) - don kontrolu
      ay_yagis        : 12 elemanli aylik ortalama toplam yagis (mm)
      yillik_yagis    : yillik ortalama toplam yagis (mm)
      mutlak_min      : donemde olculen en dusuk gunluk minimum (C) - cok yillik elemesi
      yil_sayisi      : gercekten kullanilan yil sayisi
    """
    onb = IKLIM_ONBELLEK / f"{lat:.2f}_{lon:.2f}_{yil}y.json"
    if onb.exists():
        try:
            kayit = json.loads(onb.read_text(encoding="utf-8"))
            yas = (date.today() - date.fromisoformat(kayit["_tarih"])).days
            # ALAN KONTROLU: onbellek dosyasi eski SURUMDEN kalmis olabilir.
            # "yillik_ekstrem_min" sonradan eklendi; sadece tarihe bakip donseydik
            # eski kayitlar bu alan olmadan gelir, oneri motoru da onu None gorup
            # don elemesini SESSIZCE atlardi. Alan yoksa kayit bayattir.
            if yas <= ONBELLEK_TTL_GUN and "yillik_ekstrem_min" in kayit:
                return {k: v for k, v in kayit.items() if k != "_tarih"}
        except Exception:
            pass   # bozuk onbellek sorun degil, yeniden sorulur

    end = date.today() - timedelta(days=7)
    start = end - timedelta(days=365 * yil)
    params = {
        "latitude": lat, "longitude": lon,
        "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,temperature_2m_min,precipitation_sum",
        "timezone": "auto",
    }
    daily = _arsiv_sor(params, timeout).get("daily", {})

    tarihler = daily.get("time", [])
    ortalar = daily.get("temperature_2m_mean", [])
    minler = daily.get("temperature_2m_min", [])
    yagislar = daily.get("precipitation_sum", [])

    sic: list[list[float]] = [[] for _ in range(12)]
    sic_min: list[list[float]] = [[] for _ in range(12)]
    yag: list[dict[int, float]] = [{} for _ in range(12)]   # ay -> {yil: toplam}
    mutlak_min: float | None = None
    yil_min: dict[int, float] = {}      # yil -> o yilin en dusuk gunluk minimumu
    yillar: set[int] = set()

    for i, t in enumerate(tarihler):
        y, ay = int(t[:4]), int(t[5:7]) - 1
        yillar.add(y)
        if i < len(ortalar) and ortalar[i] is not None:
            sic[ay].append(ortalar[i])
        if i < len(minler) and minler[i] is not None:
            sic_min[ay].append(minler[i])
            mutlak_min = minler[i] if mutlak_min is None else min(mutlak_min, minler[i])
            onceki = yil_min.get(y)
            yil_min[y] = minler[i] if onceki is None else min(onceki, minler[i])
        if i < len(yagislar) and yagislar[i] is not None:
            yag[ay][y] = yag[ay].get(y, 0.0) + yagislar[i]

    ay_sicaklik = [round(sum(v) / len(v), 1) if v else None for v in sic]
    ay_min = [round(sum(v) / len(v), 1) if v else None for v in sic_min]
    ay_yagis = [round(sum(d.values()) / len(d), 1) if d else None for d in yag]
    sonuc = {
        "ay_sicaklik": ay_sicaklik,
        "ay_min_sicaklik": ay_min,
        "ay_yagis": ay_yagis,
        "yillik_yagis": round(sum(v for v in ay_yagis if v is not None), 1),
        "mutlak_min": round(mutlak_min, 1) if mutlak_min is not None else None,
        # HER YILIN en soguk gecesinin ORTALAMASI. USDA dayaniklilik bolgesi
        # tam olarak boyle tanimlidir ve bahcecilik esikleri (bir turun "-25 C'ye
        # dayanir" denmesi) bu istatistige goredir.
        #
        # NEDEN AYRI BIR ALAN: eleme once mutlak_min ile yapiliyordu, yani 31
        # yilin REKOR gecesiyle. Olctuk (Bursa Hasanaga): rekor -13.5 C, ama
        # yillarin en soguk gecelerinin ortalamasi -8.0 C. Aradaki 5.5 C fark
        # enginari, zeytini ve incir gibi urunleri haksiz yere eliyordu. Rekor
        # gece 31 yilda bir yasanan bir olay; esikler ise ortalamaya gore
        # kalibre edilmis. Iki istatistigi karsilastirmak olcu hatasiydi.
        #
        # mutlak_min SILINMEDI: rekor soguk hala gercek bir risk ve kullaniciya
        # UYARI olarak gosteriliyor. Sadece artik ELEME onunla yapilmiyor.
        "yillik_ekstrem_min": (round(sum(yil_min.values()) / len(yil_min), 1)
                               if yil_min else None),
        "yil_sayisi": len(yillar),
    }
    onb.parent.mkdir(parents=True, exist_ok=True)
    onb.write_text(json.dumps({**sonuc, "_tarih": date.today().isoformat()}),
                   encoding="utf-8")
    return sonuc


def get_season_temps(
    lat: float, lon: float, start: date, timeout: int = 20
) -> dict:
    """Biofix'ten bugune gunluk min/max sicaklik serisi (GDD icin, archive API).

    Donen: {"tmin": [...], "tmax": [...], "gun": n}
    """
    end = date.today() - timedelta(days=7)   # arsiv gecikmesi
    if start > end:
        start = end - timedelta(days=30)
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_min,temperature_2m_max",
        "timezone": "auto",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    tmins = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    tmaxs = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    n = min(len(tmins), len(tmaxs))
    return {"tmin": tmins[:n], "tmax": tmaxs[:n], "gun": n}


def get_forecast_series(lat: float, lon: float, days: int = 16, timeout: int = 20) -> dict:
    """Iklim riski icin gunluk min/max sicaklik + yagis tahmini (forecast API).

    Donen: {"tmin": [...], "tmax": [...], "prec": [...], "gun": n}
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_min,temperature_2m_max,precipitation_sum",
        "forecast_days": days,
        "timezone": "auto",
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    tmins = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    tmaxs = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    precs = [p for p in daily.get("precipitation_sum", []) if p is not None]
    n = min(len(tmins), len(tmaxs))
    return {"tmin": tmins[:n], "tmax": tmaxs[:n], "prec": precs[:n], "gun": n}


def get_irrigation_inputs(lat: float, lon: float, days: int = 7, timeout: int = 20) -> dict:
    """Sulama plani icin yakin donem ET0 ve yagis (Open-Meteo forecast).

    Open-Meteo, FAO-56 Penman-Monteith referans terlemesini
    (et0_fao_evapotranspiration) dogrudan gunluk verir. Bunun ortalamasi ile
    beklenen yagis toplamini dondururuz.

    Donen:
      et0_mm_gun       : onumuzdeki `days` gunun ortalama ET0'i (mm/gun)
      yagis_mm_donem   : ayni donemin beklenen toplam yagisi (mm)
      gun              : kullanilan gun sayisi
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "et0_fao_evapotranspiration,precipitation_sum",
        "forecast_days": days,
        "timezone": "auto",
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})

    et0s = [e for e in daily.get("et0_fao_evapotranspiration", []) if e is not None]
    rains = [r for r in daily.get("precipitation_sum", []) if r is not None]

    return {
        "et0_mm_gun": round(sum(et0s) / len(et0s), 2) if et0s else None,
        "yagis_mm_donem": round(sum(rains), 1) if rains else 0.0,
        "gun": len(et0s),
    }


# Open-Meteo'nun past_days ust siniri 92. Sezon gunlugu icin 60 fazlasiyla
# yeter (iki aydan once sulanmis bir tarlanin su acigini hesaplamak zaten
# anlamsiz), ama siniri burada acikca yaziyoruz ki cagiran taraf sessizce
# kirpilmis bir pencereyle dogru sanilan bir toplam almasin.
GECMIS_GUN_TAVANI = 60


def get_gunluk_su_serisi(
    lat: float, lon: float, gecmis_gun: int = 30, timeout: int = 20
) -> dict:
    """Gecmis gunlerin GUN GUN ET0 ve yagisi (tarih etiketleriyle).

    get_irrigation_inputs'tan farki iki tane ve ikisi de sezon gunlugu icin
    zorunlu:
      1. GECMISE bakar (past_days), tahmine degil. Ciftci "en son ne zaman
         suladim" diyorsa cevap gecmis gunlerin gercek olcumunde.
      2. ORTALAMA DEGIL, DIZI dondurur. Ortalama alsaydik sulama tarihinden
         onceki gunler de toplama karisirdi; oysa acik yalnizca sulamadan
         SONRAKI gunlerde birikir. Tarih etiketi bu yuzden dondurulur:
         kesme noktasini cagiran taraf gunun kendisine bakarak koyar.

    Donen: {"tarih": ["2026-07-21", ...], "et0": [...], "yagis": [...]}
    Uc liste de ayni uzunluktadir; bir gunun et0'i veya yagisi eksikse O GUN
    hic dondurulmez (yarim gunu sifir saymak acigi oldugundan kucuk gosterir).
    """
    gecmis_gun = max(1, min(int(gecmis_gun), GECMIS_GUN_TAVANI))
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "et0_fao_evapotranspiration,precipitation_sum",
        "past_days": gecmis_gun,
        # 1: bugunu de kapsasin. past_days yalnizca dunu ve oncesini verir.
        "forecast_days": 1,
        "timezone": "auto",
    }
    resp = requests.get(FORECAST_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    daily = resp.json().get("daily", {})
    tarihler = daily.get("time", []) or []
    et0s = daily.get("et0_fao_evapotranspiration", []) or []
    yagislar = daily.get("precipitation_sum", []) or []

    t, e, y = [], [], []
    for i in range(min(len(tarihler), len(et0s), len(yagislar))):
        if et0s[i] is None or yagislar[i] is None:
            continue
        t.append(tarihler[i])
        e.append(float(et0s[i]))
        y.append(float(yagislar[i]))
    return {"tarih": t, "et0": e, "yagis": y}
