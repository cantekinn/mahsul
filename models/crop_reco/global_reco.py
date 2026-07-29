"""Kuresel urun oneri motoru: EcoCrop yontemiyle EKIM PENCERESI taramasi.

NEDEN AYRI MODUL (recommender.py duruyor):
recommender.py Sprint 1'de Antalya icin yazildi ve tek bir yillik ortalama
sicaklikla puanliyor. Bu, kuresel olcekte OLCEREK yanlis bulundu:
    Iowa yillik ortalama 11.1 C -> misir 91 urun icinde 64. sirada
    Iowa sicak donem  22.0 C    -> misir 2. sirada
Iowa dunyanin misir merkezi. Yani yillik ortalamayla oneri yapilamaz.
Eski motor Antalya akisinda calismaya devam ediyor, bu modul onun yerine
kuresel akista kullanilir.

YONTEM (FAO EcoCrop / Recocrop uygulamasiyla ayni):
  Tek yillik urun:
    - Urun dongusu GMIN..GMAX gun; aya cevrilir (>=1 ay).
    - 12 ekim ayinin HEPSI denenir. Her pencere icin:
        sicaklik = pencere aylarinin ortalamasi   (donemsel)
        don      = pencerenin en soguk ayindaki ortalama gunluk minimum
    - Pencere skorlari icinde EN IYISI alinir; o ay "onerilen ekim ayi" olur.
  Cok yillik urun (agac, bag, cay):
    - Ekim ayi secemez, yil boyu tarladadir: pencere = 12 ay.
    - Kis dayanikliligi ayri kontrol edilir (KTMPR vs olculen mutlak minimum).

YAGIS NEDEN YILLIK (once yanlis yapildi, olcumle duzeltildi):
Ilk surumde yagisi de yetisme penceresinde topladim. Sonuc bozuktu: her yerde
listeyi cok yillik urunler kapliyordu (Iowa'da misir 58 urun icinde 52.).
Sebep: cok yillik urunun penceresi 12 ay oldugu icin yagis toplami buyuk, kisa
donguluk tek yilliklarinki kucuk kaliyordu. EcoCrop'un R degerlerine baktim:
    hurma  100-400 mm    (col vahasi, YILLIK ~50-200 mm)
    kahve  1400-2300 mm  (kahve bolgeleri YILLIK 1200-2000 mm)
    celtik 1500-2000 mm  ama dongusu sadece 80-180 gun
Celtigin 4 aylik doneminde 2000 mm yagmasi mumkun degil. Yani EcoCrop'un R alani
YILLIK yagistir. Artik yagis faktoru yillik toplamla puanlanir; boylece tek
yillik ve cok yillik urunler ayni olcekte yarisir.

KIS SOGUGU IHTIYACI (bizim eklememiz, EcoCrop'ta alan yok):
EcoCrop'ta "chilling requirement" yok. Bu yuzden ilk olcumde ekvatordaki Nakuru'ya
elma ve kiraz 100 puan verildi; oysa bu agaclar kis dinlenmesi (soguklama) almadan
duzgun meyve vermez. Uyari olarak eklendi, ayrinti: SOGUKLAMA_ESIK.

Don kontrolu EcoCrop'ta ELEYICIDIR (skor sifir). Burada da oyle: buzda olen bir
urune "uygun" demek kullaniciyi zarara sokar.

Toprak (pH, doku) yil boyunca degismez, pencereden bagimsiz uygulanir.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import yaml

from core.schemas import SoilData
from models.crop_reco.recommender import _texture_class, _trapezoid

_KB_PATH = Path(__file__).resolve().parent.parent.parent / "knowledge" / "crop_params_global.yaml"

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# Faktor agirliklari. Sicaklik ve yagis en belirleyici; toprak ikincil cunku
# gubre/kirec ile duzeltilebilir, iklim duzeltilemez.
AGIRLIK = {"sicaklik": 1.0, "yagis": 0.9, "ph": 0.6, "doku": 0.4}

# Soguklama (chilling) kontrolu - BIZIM KURALIMIZ, EcoCrop'ta boyle bir alan yok.
# Dayanak: ilik iklim meyveciligi literaturunde soguklama "7 C altinda gecirilen
# saat" ile olculur; elma/kiraz/armut gibi turler 800-1200 saat ister. Aylik
# normalden saat hesaplanamaz, bu yuzden pratik vekil olcu kullaniyoruz:
#   - Tur kis dinlenmesi olan bir ilik iklim turu mu?  -> KTMPR <= -10 C
#     (elma -30, uzum -20, armut/kiraz benzeri; zeytin -10, muz +1 disarida kalir)
#   - O yerde gercekten kis oluyor mu? -> en soguk ayin ortalamasi < 10 C
# Ikisi celisiyorsa urun ELENMEZ, sadece UYARI verilir: soguklama eksikligi
# urunu oldurmez, verimi dusurur. Bu ayrimi yapmak dogruluk acisindan onemli.
SOGUKLAMA_KTMPR_ESIK = -10.0
SOGUKLAMA_AY_ESIK = 10.0

# SULAMA: su AZLIGI giderilebilir, su FAZLALIGI giderilemez.
# EcoCrop yagmura dayali (rainfed) potansiyeli olcer. Olctuk, bu varsayim testte
# dogrudan hataya donusuyor:
#   Pencap yillik yagis 783 mm, celtigin EcoCrop alt siniri 1500 mm -> uyum 0.00,
#   celtik 88 urun icinde 81. sirada. Oysa Pencap dunyanin en buyuk celtik
#   bolgelerinden biri; fark tamamen kanal ve kuyu sulamasindan geliyor.
# Bu yuzden su acigini SIFIRLAYICI degil, MALIYETLI sayiyoruz ve acigi mm olarak
# raporluyoruz. Ciftci "burada celtik olmaz" yerine "burada celtik ancak 717 mm
# sulama ile olur" bilgisini alir; bu hem dogru hem karar verdiren bilgidir.
# Ust siniri neden 1500 mm: Akdeniz'de narenciye/pamuk gibi sulanan urunlerin
# yillik uygulanan su miktari tipik olarak 500-800 mm'dir, yani 500 mm acik
# rutin tarimdir. 1500 mm acik ise suyun neredeyse tamami disaridan demektir
# (col tarimi); orada uygunlugun sifira inmesi dogrudur. Aradaki gecis dogrusal.
# Fazla yagis tarafina DOKUNMUYORUZ: kok curuklugu, mantar hastaligi ve hasat
# engeli sulama gibi bir muslukla kapatilamaz, bu yuzden orada trapez aynen kalir.
SULAMA_TAVAN_MM = 1500.0

# pH BELIRSIZLIGI: tek bir tahmin degerini kesin esik testi gibi kullanmak yanlis.
# Olctuk, sonuc uc noktada birden ayni sekilde kirildi:
#   Antalya domates : olculen pH 7.6, EcoCrop ust siniri 7.5 -> uyum 0.00, 53. sira
#   Nakuru cay      : olculen pH 6.3, EcoCrop ust siniri 6.0 -> uyum 0.00, 89. sira
# Antalya'nin bir numarali urunu domates, Nakuru'nunki cay. 0.1 pH farkiyla urunu
# tamamen elemek olcumun tasiyamayacagi bir kesinlik iddiasidir: SoilGrids pH'yi
# olcmez, uydu ve arazi degiskenlerinden TAHMIN eder ve yayinlanan hata payi
# 0.5 pH birimi mertebesindedir. Yani 7.6 okumasi gercekte 7.1-8.1 arasidir.
# Dogru yaklasim: trapezi tek noktada degil, belirsizlik araliginda ortalamak.
# Bunu sadece pH'ye uyguluyoruz. Sicaklik ve yagis boyle degil: onlar olculmus
# istasyon verisinden turetilir ve zaten 30 yil ortalamasidir, goreli hatasi cok
# daha kucuktur; oraya yapay yumusatma eklemek gercek bir sinirlamayi gizlerdi.
PH_HATA_PAYI = 0.5
PH_ORNEK = 5          # -0.5, -0.25, 0, +0.25, +0.5

# SINIRLAYICI FAKTOR (Liebig minimum yasasi): faktorleri ARITMETIK ortalarsak
# bir faktoru cok kotu olan urun yine yuksek puan alir. Olctuk, sonuc siralamayi
# kullanilamaz hale getiriyordu: Riverina'da 85 uygun urunun ust 40'i 90-100
# arasinda sikisti, arpa 94.1 puanla 50. sirada kaldi. Yani "94 puan" hicbir sey
# soylemiyordu. Ornek: Antalya zeytini yagista 0.16 aliyor (yillik 1118 mm,
# urunun ust siniri 1200 mm) ama diger uc faktor iyi oldugu icin aritmetik
# ortalama 62.3 veriyor; oysa tek basina su fazlasi o bahceyi bitirir.
# Agronomide bitkinin verimini EN ZAYIF faktor belirler, ortalama degil.
# Bu yuzden AGIRLIKLI GEOMETRIK ortalama kullaniyoruz: bir faktor dustukce
# skoru orantisiz cezalandirir, hepsi iyiyse aritmetikle ayni sonucu verir.
# Neden saf MINIMUM degil (Recocrop oyle yapar): minimum diger faktorlerin
# bilgisini tamamen atar ve ayni darbogazi paylasan onlarca urunu yine tam
# esitler; bizim asmaya calistigimiz sorun tam olarak buydu.
# Bir faktor 0 ise skor 0'dir; bu kasitlidir, EcoCrop'un mutlak sinirinin
# disina cikmak "bu urun burada yetismez" demektir.


@lru_cache(maxsize=1)
def bilgi_tabani() -> dict:
    with _KB_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _merkezlik(x: float, band: dict) -> float:
    """Deger optimum bandin NERESINDE: tam ortasi 1.0, band kenari 0.0, disi 0.0.

    NEDEN GEREKLI: trapez fonksiyonun optimum araligi DUZLUKTUR, iceride her yer
    1.0 verir. Olctuk: Antalya'da 91 urunun 34'u tam 100.0 puanla esitlendi, yani
    siralama alfabetik/rastgele hale geldi ve ciftciye "hangisi daha iyi" sorusunun
    cevabi verilemedi. Ornek: domatesin optimum sicakligi 20-27 C. Antalya donem
    ortalamasi 24.4 C (tam orta, merkezlik 0.94) ile 20.1 C (kenar, merkezlik 0.03)
    ayni 1.0 uyumu aliyor; oysa ikincisi sinirda.

    Bunu SKORA KATMIYORUZ. EcoCrop'un tanimi geregi optimum bandin ici esit derecede
    uygundur; skoru degistirmek modeli kaynagindan saptirir. Sadece IKINCIL SIRALAMA
    anahtari olarak kullaniyoruz: esit skorlu urunler arasinda bandin ortasinda
    olan one gecer. Skorun anlami bozulmaz, siralama bilgilendirici olur.
    """
    omin, omax = band["opt_min"], band["opt_max"]
    if omin is None or omax is None:
        return 0.0
    if x < omin or x > omax:
        return 0.0
    yari = (omax - omin) / 2
    if yari <= 0:
        return 1.0
    return 1.0 - abs(x - (omin + omax) / 2) / yari


def _geometrik(puanlar: list[tuple[float, float]]) -> float:
    """Agirlikli geometrik ortalama (Liebig minimum yasasi, gerekce yukarida).

    Eksik veri cezalandirmaz: sadece verili faktorler listeye girer, agirlik da
    onlar uzerinden normalize edilir.
    """
    top_a = sum(a for _, a in puanlar)
    if top_a <= 0:
        return 0.0
    if any(m <= 0 for m, _ in puanlar):
        return 0.0     # bir faktor mutlak sinirin disinda -> urun burada yetismez
    return math.exp(sum(a * math.log(m) for m, a in puanlar) / top_a)


def _ph_uyum(ph: float, band: dict) -> float:
    """pH uyumu, olcum belirsizligi uzerinden ortalanmis (bkz PH_HATA_PAYI)."""
    adim = 2 * PH_HATA_PAYI / (PH_ORNEK - 1)
    ornekler = [ph - PH_HATA_PAYI + i * adim for i in range(PH_ORNEK)]
    return sum(_trapezoid(p, band) for p in ornekler) / PH_ORNEK


def _pencere(basla: int, uzunluk: int) -> list[int]:
    """Yil sonundan basa donen ay indeksleri (Kasim ekimi Subat'ta biter)."""
    return [(basla + i) % 12 for i in range(uzunluk)]


def _dongu_ay(urun: dict) -> int:
    """Urun dongusunu aya cevirir, 1..12 arasina sikistirir."""
    d = urun.get("dongu_gun") or {}
    gun = d.get("min") or 90
    return max(1, min(12, round(gun / 30)))


def _skor_pencere(urun: dict, aylar: list[int], iklim: dict,
                  soil: SoilData) -> tuple[float, float, list[dict], str | None, float]:
    """Pencere icin (skor, merkezlik, faktorler, eleme_sebebi, su_acigi_mm).

    merkezlik skora KATILMAZ, sadece esit skorlulari siralamak icindir (bkz _merkezlik).
    """
    ay_sic = iklim["ay_sicaklik"]
    ay_min = iklim["ay_min_sicaklik"]

    sicaklar = [ay_sic[a] for a in aylar if ay_sic[a] is not None]
    if not sicaklar:
        return 0.0, 0.0, [], "iklim verisi eksik", 0.0

    faktorler: list[dict] = []
    # (uyum, agirlik) ciftleri; skor agirlikli GEOMETRIK ortalamayla hesaplanir.
    puanlar: list[tuple[float, float]] = []
    mrk_a = mrk_s = 0.0

    t_ort = sum(sicaklar) / len(sicaklar)
    m = _trapezoid(t_ort, urun["sicaklik"])
    puanlar.append((m, AGIRLIK["sicaklik"]))
    mrk_a += AGIRLIK["sicaklik"]; mrk_s += AGIRLIK["sicaklik"] * _merkezlik(t_ort, urun["sicaklik"])
    faktorler.append({"faktor": "Dönem sıcaklığı", "deger": round(t_ort, 1),
                      "birim": "C", "uyum": round(m, 2)})

    # Yagis YILLIK toplamdir (pencereye bagli degil) - gerekce modul basliginda.
    su_acigi = 0.0
    r_yil = iklim.get("yillik_yagis")
    if r_yil is not None:
        bant = urun["yagis_mm"]
        yagmur = _trapezoid(r_yil, bant)
        # Optimumun ALTINDA kalan kisim sulama ile kapatilir (bkz SULAMA_TAVAN_MM).
        su_acigi = max(0.0, bant["opt_min"] - r_yil)
        sulu = max(0.0, 1.0 - su_acigi / SULAMA_TAVAN_MM) if su_acigi > 0 else yagmur
        m = max(yagmur, sulu)      # sulama asla yagmurdan kotu bir sonuc vermez
        puanlar.append((m, AGIRLIK["yagis"]))
        mrk_a += AGIRLIK["yagis"]; mrk_s += AGIRLIK["yagis"] * _merkezlik(r_yil, bant)
        faktorler.append({"faktor": "Yıllık yağış", "deger": round(r_yil, 0),
                          "birim": "mm", "uyum": round(m, 2)})

    if soil.ph is not None:
        m = _ph_uyum(soil.ph, urun["ph"])
        puanlar.append((m, AGIRLIK["ph"]))
        mrk_a += AGIRLIK["ph"]; mrk_s += AGIRLIK["ph"] * _merkezlik(soil.ph, urun["ph"])
        faktorler.append({"faktor": "Toprak pH", "deger": soil.ph,
                          "birim": "", "uyum": round(m, 2)})

    doku = _texture_class(soil)
    tercih = urun.get("doku") or []
    if doku and tercih:
        m = 1.0 if doku in tercih else 0.4
        puanlar.append((m, AGIRLIK["doku"]))
        mrk_a += AGIRLIK["doku"]; mrk_s += AGIRLIK["doku"] * m
        faktorler.append({"faktor": "Toprak dokusu", "deger": doku,
                          "birim": "", "uyum": round(m, 2)})

    # Don elemesi: pencerenin en soguk ayindaki ortalama gunluk minimum
    don_esik = urun.get("don_buyume_c")
    eleme = None
    if don_esik is not None:
        minler = [ay_min[a] for a in aylar if ay_min[a] is not None]
        if minler and min(minler) < don_esik:
            eleme = (f"{AYLAR[aylar[minler.index(min(minler))]]} ayında ortalama "
                     f"en düşük {min(minler):.1f} C, ürünün dayanma sınırı "
                     f"{don_esik:.0f} C")

    return (_geometrik(puanlar) * 100, mrk_s / mrk_a if mrk_a else 0.0,
            faktorler, eleme, su_acigi)


def _etiket(skor: float) -> str:
    if skor >= 75:
        return "Çok uygun"
    if skor >= 55:
        return "Uygun"
    if skor >= 35:
        return "Sınırlı uygun"
    return "Uygun değil"


def urun_oner(soil: SoilData, iklim: dict, adet: int = 10,
              elenenleri_dahil_et: bool = False) -> list[dict]:
    """Konumun aylik iklimine ve toprakina gore urunleri sirali dondurur.

    iklim: data.open_meteo.get_monthly_climate() ciktisi.
    Her oge: urun, ad, grup, skor, uygunluk, ekim_ayi, hasat_ayi, faktorler,
             uyari (varsa), cok_yillik, notlar
    """
    kb = bilgi_tabani()
    sonuc: list[dict] = []

    for anahtar, urun in kb.items():
        cok_yillik = bool(urun.get("cok_yillik"))

        if cok_yillik:
            # Cok yillik urun ekim ayi secmez ama yilin 12 ayi da BUYUMEZ.
            # Sicakligi yillik ortalamayla puanlamak Akdeniz ve iliman iklimde
            # agaclari haksiz yere dusuruyordu (Antalya zeytini yillik 19.4 C ile
            # 0.96 aliyor, oysa buyume donemi Nisan-Ekim ortalamasi ~24 C ve tam
            # optimumda). EcoCrop'un TMIN'i "altinda buyume durur" esigidir; bu
            # yuzden aktif buyume aylari = ortalama sicakligi TMIN'in ustunde
            # olan aylar. Hic yoksa urun zaten o yerde buyuyemez.
            tmin = urun["sicaklik"]["min"]
            aktif = [a for a in range(12)
                     if iklim["ay_sicaklik"][a] is not None
                     and iklim["ay_sicaklik"][a] >= tmin]
            adaylar = [(0, aktif or list(range(12)))]
        else:
            uz = _dongu_ay(urun)
            adaylar = [(b, _pencere(b, uz)) for b in range(12)]

        en_iyi = None
        for basla, aylar in adaylar:
            skor, merkez, faktorler, don, acik = _skor_pencere(urun, aylar, iklim, soil)
            if don is not None:
                skor = 0.0          # EcoCrop'ta don eleyicidir
            # Esit skorlu pencereler arasinda bandin ortasinda olani sec: 12 ekim
            # ayinin bircogu ayni 100.0'i verdiginde aksi halde hep Ocak seciliyordu.
            if en_iyi is None or (skor, merkez) > (en_iyi[0], en_iyi[1]):
                en_iyi = (skor, merkez, faktorler, don, acik, basla, aylar)
        if en_iyi is None:
            continue
        skor, merkez, faktorler, don, su_acigi, basla, aylar = en_iyi

        uyarilar: list[str] = []
        if don:
            uyarilar.append(f"Don riski: {don}")
        if su_acigi > 0:
            uyarilar.append(
                # 1 mm yagis = 1 litre/m2 = 1 m3 = 1 ton su, dekar (1000 m2) basina.
                f"Sulama gerekir: yıllık yağış ürünün istediğinin {su_acigi:.0f} mm "
                f"altında, yani dekara {su_acigi:.0f} ton su/yıl."
            )

        # Cok yillik urunun kisi tarlada gecirmesi gerekir; olculen mutlak
        # minimum, kis dayanma sinirinin altindaysa urun o yerde yasayamaz.
        kis_esik = urun.get("don_dinlenme_c")
        mutlak = iklim.get("mutlak_min")
        if cok_yillik and kis_esik is not None and mutlak is not None and mutlak < kis_esik:
            skor = 0.0
            uyarilar.append(
                f"Kış dayanıklılığı yetersiz: ölçülen en düşük {mutlak:.1f} C, "
                f"ürünün sınırı {kis_esik:.0f} C. Örtü altı olmadan yaşamaz."
            )

        # Soguklama: ilik iklim meyvesi ise ve o yerde kis yoksa uyar (elemez).
        if cok_yillik and kis_esik is not None and kis_esik <= SOGUKLAMA_KTMPR_ESIK:
            aylik = [t for t in iklim["ay_sicaklik"] if t is not None]
            if aylik and min(aylik) >= SOGUKLAMA_AY_ESIK:
                uyarilar.append(
                    f"Soğuklama yetersiz olabilir: en soğuk ay ortalaması "
                    f"{min(aylik):.1f} C. Bu tür kış dinlenmesi ister; iklim uygun "
                    f"görünse de çiçeklenme ve verim düzensiz olur."
                )

        if skor <= 0 and not elenenleri_dahil_et:
            continue

        sonuc.append({
            "urun": anahtar,
            "ad": urun["ad"],
            "bilimsel_ad": urun.get("bilimsel_ad", ""),
            "grup": urun.get("grup", ""),
            "skor": round(skor, 1),
            # Skorun anlami degismesin diye ayri alan; sadece siralama icin.
            "merkezlik": round(merkez, 3),
            "su_acigi_mm": round(su_acigi),
            "uygunluk": _etiket(skor),
            "cok_yillik": cok_yillik,
            "ekim_ayi": None if cok_yillik else AYLAR[basla],
            "hasat_ayi": None if cok_yillik else AYLAR[aylar[-1]],
            "faktorler": faktorler,
            "uyarilar": uyarilar,
            "sezon": urun.get("sezon", ""),
            "notlar": urun.get("notlar", ""),
        })

    # Once skor, esitlikte merkezlik. Bkz _merkezlik: trapez duzlugu yuzunden
    # tek basina skorla siralamak onlarca urunu ayni yere koyuyor.
    sonuc.sort(key=lambda r: (r["skor"], r["merkezlik"]), reverse=True)
    return sonuc[:adet]


def gruba_gore(soil: SoilData, iklim: dict, grup_basina: int = 3) -> dict[str, list[dict]]:
    """Her urun grubundan en iyi N urun. Arayuzde cesitlilik icin.

    Sadece tepe listeyi gostermek tek bir gruba bogar (orn. hepsi meyve cikar);
    ciftciye gercek secenek sunmak icin gruplar ayri ayri dondurulur.
    """
    hepsi = urun_oner(soil, iklim, adet=10_000)
    gruplar: dict[str, list[dict]] = {}
    for r in hepsi:
        g = r["grup"] or "diğer"
        if len(gruplar.setdefault(g, [])) < grup_basina:
            gruplar[g].append(r)
    return gruplar
