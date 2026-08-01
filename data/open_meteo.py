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

# Open-Meteo'nun past_days ust siniri 92. Sezon gunlugu icin 60 fazlasiyla
# yeter (iki aydan once sulanmis bir tarlanin su acigini hesaplamak zaten
# anlamsiz), ama siniri burada acikca yaziyoruz ki cagiran taraf sessizce
# kirpilmis bir pencereyle dogru sanilan bir toplam almasin.
GECMIS_GUN_TAVANI = 60

# TAHMIN SORGUSU: NOKTA BASINA TEK ISTEK + SUREC ICI ONBELLEK
#
# Olctuk: tarla takvimi sekmesi tek acilista tahmin ucuna DORT istek yolluyordu
# (sulama, karbon, iklim riski, sezon gunlugu) ve bunlardan ikisi -- sulama ile
# karbon -- birebir ayni parametrelerle soruyordu, cunku karbon ajani sulama
# planini yeniden hesapliyor. Render'in giden IP'si baska kiracilarla paylasimli
# oldugu icin bu yigin "Minutely API request limit exceeded" (HTTP 429) ile geri
# donuyor ve kartlar "hava verisi alinamadi" yaziyordu.
#
# Iki katmanli cozum:
#   1. Dort sorgu TEKE indirildi. Hepsi ayni ucun ayni gunluk degiskenlerini
#      istiyor, yalnizca pencereleri farkli. En genis pencereyi bir kez cekip
#      dilimliyoruz.
#   2. Sonuc surec icinde tutuluyor. Open-Meteo tahmin modelini saatte bir
#      guncelliyor; 30 dakikalik TTL veriyi bayatlatmaz ama ayni noktaya arka
#      arkaya bakan kullanici icin sifir istek demektir.
_TAHMIN_ONBELLEK: dict[tuple[float, float], tuple[float, dict]] = {}
_TAHMIN_TTL_S = 1800.0
_TAHMIN_TAVAN = 64        # 76 gun x 4 dizi x 64 nokta ~ 2 MB, 512 MB icinde ihmal
_TAHMIN_GUN = 16          # Open-Meteo ucretsiz tahmin ufku

# ARSIV SEZON PENCERESI: ayni gerekce, ayri sunucu.
# api.open-meteo.com ile archive-api.open-meteo.com'un kotalari AYRI tutuluyor;
# olctuk, ikisi ayni anda ama farkli limitlerle doldu (tahmin ucu "Daily",
# arsiv ucu "Hourly"). Bu yuzden arsiv tarafinin da kendi onbellegi var.
# TTL 6 saat: arsiv verisi 7 gun gecikmeli geliyor, yani gun icinde degismez.
SEZON_PENCERE_GUN = 400
_SEZON_ONBELLEK: dict[tuple[float, float], tuple[float, dict]] = {}
_SEZON_TTL_S = 21600.0
_SEZON_TAVAN = 32         # 400 gun x 2 dizi x 32 nokta ~ 2 MB

# ANLIK KAYIT (imaja gomulu yedek)
#
# Render'in diski kalici degil ve servis 15 dakika sonra uykuya geciyor, yani
# calisma aninda yazilan bir yedek yeniden baslatmada kayboluyor. Bu yuzden
# yedek DEPOYA konur: scripts/onbellek_isit.py bir tarihte cekip yazar, imaja
# gomulur, kota dolu oldugunda kullanilir.
#
# BU BIR TAHMIN YEDEGI, GUNCEL VERI DEGIL. Onun icin dosyada cekildigi tarih
# de duruyor ve arayuz o tarihi kullaniciya YAZIYOR. Etiketsiz gosterseydik
# eski bir tahmini bugunun sulama plani diye sunmus olurduk; bu, sayfayi bos
# birakmaktan daha kotu bir hata olurdu.
TAHMIN_YEDEK = Path(__file__).resolve().parent / "_onbellek" / "tahmin_yedek"


def _yedek_yolu(lat: float, lon: float) -> Path:
    return TAHMIN_YEDEK / f"{lat:.2f}_{lon:.2f}.json"


def yedek_yaz(lat: float, lon: float, daily: dict) -> Path:
    """Anlik tahmin penceresini tarihiyle birlikte diske yazar (isitma scripti)."""
    yol = _yedek_yolu(lat, lon)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(
        json.dumps({**daily, "_tarih": date.today().isoformat()}, separators=(",", ":")),
        encoding="utf-8",
    )
    return yol


def _yedek_oku(lat: float, lon: float) -> dict | None:
    """Gomulu anlik kaydi okur. Donen sozlukte `_tarih` alani KORUNUR."""
    yol = _yedek_yolu(lat, lon)
    if not yol.exists():
        return None
    try:
        kayit = json.loads(yol.read_text(encoding="utf-8"))
    except Exception:
        return None
    return kayit if kayit.get("time") else None


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
    bayat: dict | None = None
    if onb.exists():
        try:
            kayit = json.loads(onb.read_text(encoding="utf-8"))
            yas = (date.today() - date.fromisoformat(kayit["_tarih"])).days
            # ALAN KONTROLU: onbellek dosyasi eski SURUMDEN kalmis olabilir.
            # "yillik_ekstrem_min" sonradan eklendi; sadece tarihe bakip donseydik
            # eski kayitlar bu alan olmadan gelir, oneri motoru da onu None gorup
            # don elemesini SESSIZCE atlardi. Alan yoksa kayit bayattir.
            if "yillik_ekstrem_min" in kayit:
                temiz = {k: v for k, v in kayit.items() if k != "_tarih"}
                if yas <= ONBELLEK_TTL_GUN:
                    return temiz
                bayat = temiz
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
    try:
        daily = _arsiv_sor(params, timeout).get("daily", {})
    except Exception:
        # TTL DOLDU DIYE ONERIYI DUSURMEYELIM. 30 yillik normal 180 gunde
        # olculebilir sekilde degismez; yenilemenin amaci yeni yili eklemek,
        # elimizdekini gecersiz kilmak degil. Kota doluyken 181 gunluk normali
        # atip "urun onerisi uretilemez" demek, kullanicinin gordugu sonucu
        # veri kalitesiyle degil o anki istek yogunluguyla belirlerdi.
        if bayat is not None:
            return bayat
        raise

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


def _sezon_penceresi(lat: float, lon: float, timeout: int = 20) -> dict:
    """Bir nokta icin son SEZON_PENCERE_GUN gunun min/max sicakligi, tek sorguda.

    NEDEN SABIT PENCERE: get_season_temps'in penceresi biofix'e gore degisiyordu,
    yani ayni nokta icin farkli urunler farkli baslangic tarihi ureterek AYRI
    sorgular aciyordu (/zararli bir kez, /sor'un zararli niyeti bir kez daha).
    Pencereyi sabitleyip dilimlersek nokta basina tek sorgu kaliyor ve arsiv
    ucunun saatlik kotasi bir sayfa acilisinda dolmuyor.

    NEDEN 400 GUN: en erken biofix bile gecen sezonun icinde kaliyor; 400 gun
    bir tam yili artigiyla kapsiyor. Arsiv verisi zaten 7 gun gecikmeli ve
    gecmis gun bir daha degismiyor, o yuzden TTL uzun tutulabiliyor.
    """
    anahtar = (round(lat, 2), round(lon, 2))
    kayit = _SEZON_ONBELLEK.get(anahtar)
    if kayit is not None and (time.time() - kayit[0]) <= _SEZON_TTL_S:
        return kayit[1]

    end = date.today() - timedelta(days=7)   # arsiv gecikmesi
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": (end - timedelta(days=SEZON_PENCERE_GUN)).isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_min,temperature_2m_max",
        "timezone": "auto",
    }
    try:
        daily = _arsiv_sor(params, timeout).get("daily", {}) or {}
    except Exception:
        # Tahmin tarafiyla ayni gerekce: kotanin dolmasi GECMIS sicakligin
        # degistigi anlamina gelmiyor. Elimizdeki pencere zaten degismeyecek
        # gunlerden olusuyor, bayat kayit burada gercekten de dogru cevap.
        if kayit is not None:
            return kayit[1]
        raise

    if len(_SEZON_ONBELLEK) >= _SEZON_TAVAN:
        en_eski = min(_SEZON_ONBELLEK, key=lambda k: _SEZON_ONBELLEK[k][0])
        _SEZON_ONBELLEK.pop(en_eski, None)
    _SEZON_ONBELLEK[anahtar] = (time.time(), daily)
    return daily


def get_season_temps(
    lat: float, lon: float, start: date, timeout: int = 20
) -> dict:
    """Biofix'ten bugune gunluk min/max sicaklik serisi (GDD icin, archive API).

    Donen: {"tmin": [...], "tmax": [...], "gun": n}
    """
    end = date.today() - timedelta(days=7)   # arsiv gecikmesi
    if start > end:
        start = end - timedelta(days=30)
    daily = _sezon_penceresi(lat, lon, timeout)

    tarihler = daily.get("time") or []
    bas = 0
    for i, t in enumerate(tarihler):
        if t >= start.isoformat():
            bas = i
            break
    else:
        bas = len(tarihler)
    dilim = slice(bas, len(tarihler))
    tmins = [t for t in (daily.get("temperature_2m_min") or [])[dilim] if t is not None]
    tmaxs = [t for t in (daily.get("temperature_2m_max") or [])[dilim] if t is not None]
    n = min(len(tmins), len(tmaxs))
    return {"tmin": tmins[:n], "tmax": tmaxs[:n], "gun": n}


def _tahmin_penceresi(lat: float, lon: float, timeout: int = 20) -> dict:
    """Bir nokta icin gecmis + tahmin gunlerinin TAMAMINI tek istekte ceker.

    Donen: Open-Meteo'nun "daily" sozlugu (time, temperature_2m_min,
    temperature_2m_max, precipitation_sum, et0_fao_evapotranspiration).
    Ustteki uc fonksiyon bunun dilimidir; ayrica istek atmazlar.
    """
    anahtar = (round(lat, 2), round(lon, 2))
    kayit = _TAHMIN_ONBELLEK.get(anahtar)
    if kayit is not None and (time.time() - kayit[0]) <= _TAHMIN_TTL_S:
        return kayit[1]

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": ("temperature_2m_min,temperature_2m_max,"
                  "precipitation_sum,et0_fao_evapotranspiration"),
        "past_days": GECMIS_GUN_TAVANI,
        "forecast_days": _TAHMIN_GUN,
        "timezone": "auto",
    }
    try:
        resp = requests.get(FORECAST_URL, params=params, timeout=timeout)
        if resp.status_code in (429, 500, 502, 503, 504):
            raise RuntimeError(f"Open-Meteo {_sunucu_gerekcesi(resp)}")
        resp.raise_for_status()
        daily = resp.json().get("daily", {}) or {}
    except Exception:
        # SIRA: once surec ici bayat kayit, sonra imaja gomulu anlik kayit.
        # Bayat kayit donulur cunku kotanin dolmasi tahminin degistigi anlamina
        # gelmiyor; elimizdeki 40 dakikalik tahmin, "hava verisi alinamadi"
        # yazisindan olculebilir sekilde daha iyi. Ikisi de yoksa hata yukari
        # cikar, cunku o zaman gercekten soyleyecek bir seyimiz yok.
        if kayit is not None:
            return kayit[1]
        yedek = _yedek_oku(lat, lon)
        if yedek is not None:
            return yedek
        raise

    if len(_TAHMIN_ONBELLEK) >= _TAHMIN_TAVAN:
        en_eski = min(_TAHMIN_ONBELLEK, key=lambda k: _TAHMIN_ONBELLEK[k][0])
        _TAHMIN_ONBELLEK.pop(en_eski, None)
    _TAHMIN_ONBELLEK[anahtar] = (time.time(), daily)
    return daily


def _bugun_indeksi(tarihler: list[str]) -> int:
    """Pencerede bugunun indeksi. Gecmis ile tahmini burasi ayirir."""
    try:
        return tarihler.index(date.today().isoformat())
    except ValueError:
        # timezone=auto YEREL tarih dondurur; sunucunun gunu ile noktanin gunu
        # bir gun kayabiliyor. Pencerenin kurulusu sabit oldugu icin (past_days
        # kadar gecmis, sonra bugun) indeksi oradan turetmek guvenli.
        return min(GECMIS_GUN_TAVANI, max(0, len(tarihler) - _TAHMIN_GUN))


def get_forecast_series(lat: float, lon: float, days: int = 16, timeout: int = 20) -> dict:
    """Iklim riski icin gunluk min/max sicaklik + yagis tahmini.

    Donen: {"tmin": [...], "tmax": [...], "prec": [...], "gun": n}
    """
    daily = _tahmin_penceresi(lat, lon, timeout)
    i = _bugun_indeksi(daily.get("time") or [])
    dilim = slice(i, i + days)
    tmins = [t for t in (daily.get("temperature_2m_min") or [])[dilim] if t is not None]
    tmaxs = [t for t in (daily.get("temperature_2m_max") or [])[dilim] if t is not None]
    precs = [p for p in (daily.get("precipitation_sum") or [])[dilim] if p is not None]
    n = min(len(tmins), len(tmaxs))
    return {"tmin": tmins[:n], "tmax": tmaxs[:n], "prec": precs[:n], "gun": n,
            "kayit_tarihi": daily.get("_tarih")}


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
    daily = _tahmin_penceresi(lat, lon, timeout)
    i = _bugun_indeksi(daily.get("time") or [])
    dilim = slice(i, i + days)

    et0s = [e for e in (daily.get("et0_fao_evapotranspiration") or [])[dilim] if e is not None]
    rains = [r for r in (daily.get("precipitation_sum") or [])[dilim] if r is not None]

    return {
        "et0_mm_gun": round(sum(et0s) / len(et0s), 2) if et0s else None,
        "yagis_mm_donem": round(sum(rains), 1) if rains else 0.0,
        "gun": len(et0s),
        # Canli veri geldiyse None. Doluysa gosterilen sayilar bu tarihte
        # cekilmis tahminden geliyor demektir ve arayuz bunu yaziyor.
        "kayit_tarihi": daily.get("_tarih"),
    }


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
    daily = _tahmin_penceresi(lat, lon, timeout)
    i = _bugun_indeksi(daily.get("time") or [])
    # Bugun DAHIL: past_days yalnizca dunu ve oncesini verir, oysa sulamadan
    # bugune biriken acik bugunun ET0'ini da icermeli.
    dilim = slice(max(0, i - gecmis_gun), i + 1)

    tarihler = (daily.get("time") or [])[dilim]
    et0s = (daily.get("et0_fao_evapotranspiration") or [])[dilim]
    yagislar = (daily.get("precipitation_sum") or [])[dilim]

    t, e, y = [], [], []
    for i in range(min(len(tarihler), len(et0s), len(yagislar))):
        if et0s[i] is None or yagislar[i] is None:
            continue
        t.append(tarihler[i])
        e.append(float(et0s[i]))
        y.append(float(yagislar[i]))
    return {"tarih": t, "et0": e, "yagis": y, "kayit_tarihi": daily.get("_tarih")}
