"""FAO EcoCrop veritabanindan kuresel urun bilgi tabani uretir.

NEDEN: elde 6 urun vardi (domates, biber, patates, narenciye, zeytin, muz) ve
hepsi Antalya icin secilmisti. Iowa'ya "domates yetistir" demek anlamsiz.
Kuresel iddia icin kuresel urun listesi gerekiyor.

NEDEN ECOCROP: parametreleri UYDURMUYORUZ. FAO EcoCrop 2568 turun sicaklik,
yagis ve pH esiklerini tam bizim trapez modelimizin sekliyle veriyor:
    TMIN  < TOPMN .. TOPMX <  TMAX    (mutlak min, ideal aralik, mutlak max)
    RMIN  < ROPMN .. ROPMX <  RMAX
    PHMIN < PHOPMN.. PHOPMX< PHMAX
Yani knowledge/crop_params.yaml'daki {min, opt_min, opt_max, max} yapisi ile
bire bir esleser. Bizim katkimiz SECIM (hangi urunler) ve Turkce adlandirma.

Kaynak : https://github.com/OpenCLIM/ecocrop  (EcoCrop_DB.csv)
Lisans : FAO EcoCrop, kamuya acik; atif knowledge/KAYNAK_ecocrop.md dosyasinda.

Calistirma: py -m scripts.build_crop_kb
"""
from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KAYNAK = ROOT / "data" / "_kaynak" / "EcoCrop_DB.csv"
CIKTI = ROOT / "knowledge" / "crop_params_global.yaml"
ATIF = ROOT / "knowledge" / "KAYNAK_ecocrop.md"
INDIR_URL = "https://raw.githubusercontent.com/OpenCLIM/ecocrop/main/EcoCrop_DB.csv"

# --------------------------------------------------------------------------
# SECIM: kuresel olarak onemli, gercekten yetistirilen urunler.
# bilimsel_ad -> (anahtar, Turkce ad, grup)
# Bilimsel adlarin hepsi EcoCrop_DB.csv'de bulundugu DOGRULANDI.
# --------------------------------------------------------------------------
SECIM: dict[str, tuple[str, str, str]] = {
    # Tahillar
    "Triticum aestivum": ("bugday", "Buğday", "tahıl"),
    "Zea mays": ("misir", "Mısır", "tahıl"),
    "Oryza sativa": ("celtik", "Çeltik (pirinç)", "tahıl"),
    "Hordeum vulgare": ("arpa", "Arpa", "tahıl"),
    "Avena sativa": ("yulaf", "Yulaf", "tahıl"),
    "Secale cereale": ("cavdar", "Çavdar", "tahıl"),
    "Sorghum bicolor": ("sorgum", "Sorgum", "tahıl"),
    "Pennisetum glaucum": ("inci_dari", "İnci darı", "tahıl"),
    "Panicum miliaceum": ("dari", "Darı", "tahıl"),
    "Eleusine coracana ssp. coracana": ("parmak_dari", "Parmak darı", "tahıl"),
    "Fagopyrum esculentum": ("karabugday", "Karabuğday", "tahıl"),
    "Chenopodium quinoa": ("kinoa", "Kinoa", "tahıl"),
    # Baklagiller
    "Glycine max": ("soya", "Soya fasulyesi", "baklagil"),
    "Phaseolus vulgaris": ("fasulye", "Fasulye", "baklagil"),
    "Cicer arietinum": ("nohut", "Nohut", "baklagil"),
    "Lens culinaris": ("mercimek", "Mercimek", "baklagil"),
    "Pisum sativum": ("bezelye", "Bezelye", "baklagil"),
    "Vicia faba": ("bakla", "Bakla", "baklagil"),
    "Vigna unguiculata": ("borulce", "Börülce", "baklagil"),
    "Vigna radiata": ("mas_fasulyesi", "Maş fasulyesi", "baklagil"),
    "Cajanus cajan": ("guvercin_bezelyesi", "Güvercin bezelyesi", "baklagil"),
    "Arachis hypogaea": ("yer_fistigi", "Yer fıstığı", "baklagil"),
    "Medicago sativa": ("yonca", "Yonca", "yem bitkisi"),
    # Kok ve yumru
    "Solanum tuberosum": ("patates", "Patates", "kök/yumru"),
    "Ipomoea batatas": ("tatli_patates", "Tatlı patates", "kök/yumru"),
    "Manihot esculenta": ("manyok", "Manyok (kasava)", "kök/yumru"),
    "Dioscorea alata": ("yam", "Yam", "kök/yumru"),
    "Colocasia esculenta": ("taro", "Taro (gölevez)", "kök/yumru"),
    "Beta vulgaris": ("seker_pancari", "Şeker pancarı", "kök/yumru"),
    "Daucus carota": ("havuc", "Havuç", "kök/yumru"),
    "Raphanus sativus": ("turp", "Turp", "kök/yumru"),
    # Sebzeler
    "Lycopersicon esculentum": ("domates", "Domates", "sebze"),
    "Capsicum annuum": ("biber", "Biber", "sebze"),
    "Solanum melongena": ("patlican", "Patlıcan", "sebze"),
    "Cucumis sativus": ("salatalik", "Salatalık", "sebze"),
    "Cucurbita pepo": ("kabak", "Kabak", "sebze"),
    "Citrullus lanatus": ("karpuz", "Karpuz", "sebze"),
    "Cucumis melo": ("kavun", "Kavun", "sebze"),
    "Allium cepa": ("sogan", "Soğan", "sebze"),
    "Allium sativum": ("sarimsak", "Sarımsak", "sebze"),
    "Brassica oleracea var. capitata": ("lahana", "Lahana", "sebze"),
    "Brassica oleracea var. botrytis": ("karnabahar", "Karnabahar", "sebze"),
    "Brassica oleracea var. italica": ("brokoli", "Brokoli", "sebze"),
    "Lactuca sativa var. capitata": ("marul", "Marul", "sebze"),
    "Spinacia oleracea": ("ispanak", "Ispanak", "sebze"),
    "Abelmoschus esculentus": ("bamya", "Bamya", "sebze"),
    # Meyveler
    "Vitis vinifera": ("uzum", "Üzüm", "meyve"),
    "Olea europaea": ("zeytin", "Zeytin", "meyve"),
    "Citrus sinensis": ("portakal", "Portakal", "meyve"),
    "Citrus limon": ("limon", "Limon", "meyve"),
    "Citrus reticulata": ("mandalina", "Mandalina", "meyve"),
    "Malus domestica": ("elma", "Elma", "meyve"),
    "Pyrus communis": ("armut", "Armut", "meyve"),
    "Prunus persica": ("seftali", "Şeftali", "meyve"),
    "Prunus armeniaca": ("kayisi", "Kayısı", "meyve"),
    "Prunus avium": ("kiraz", "Kiraz", "meyve"),
    "Prunus cerasus": ("visne", "Vişne", "meyve"),
    "Prunus domestica": ("erik", "Erik", "meyve"),
    "Ficus carica": ("incir", "İncir", "meyve"),
    "Punica granatum": ("nar", "Nar", "meyve"),
    # "Musa sapientum" kaydi EcoCrop'ta tamamen bos (T/R/pH hepsi NA); yenilebilir
    # muzlarin (AAA) ana atasi olan Musa acuminata kullaniliyor.
    "Musa acuminata": ("muz", "Muz", "meyve"),
    "Mangifera indica": ("mango", "Mango", "meyve"),
    "Persea americana": ("avokado", "Avokado", "meyve"),
    "Ananas comosus": ("ananas", "Ananas", "meyve"),
    "Carica papaya": ("papaya", "Papaya", "meyve"),
    "Fragaria vesca": ("cilek", "Çilek", "meyve"),
    "Vaccinium corymbosum": ("yabanmersini", "Yaban mersini", "meyve"),
    "Rubus idaeus ssp. idaeus": ("ahududu", "Ahududu", "meyve"),
    "Ribes nigrum": ("frenk_uzumu", "Siyah frenk üzümü", "meyve"),
    "Actinidia chinensis": ("kivi", "Kivi", "meyve"),
    "Phoenix dactylifera": ("hurma", "Hurma", "meyve"),
    # Sert kabuklular
    "Juglans regia": ("ceviz", "Ceviz", "sert kabuklu"),
    "Corylus avellana": ("findik", "Fındık", "sert kabuklu"),
    "Pistacia vera": ("antep_fistigi", "Antep fıstığı", "sert kabuklu"),
    "Prunus amygdalus": ("badem", "Badem", "sert kabuklu"),
    "Castanea sativa": ("kestane", "Kestane", "sert kabuklu"),
    "Ceratonia siliqua": ("kecibonuzu", "Keçiboynuzu", "sert kabuklu"),
    # Yag bitkileri
    "Helianthus annuus": ("aycicegi", "Ayçiçeği", "yağ bitkisi"),
    "Brassica napus": ("kanola", "Kanola (kolza)", "yağ bitkisi"),
    "Sesamum indicum": ("susam", "Susam", "yağ bitkisi"),
    "Carthamus tinctorius": ("aspir", "Aspir", "yağ bitkisi"),
    "Linum usitatissimum": ("keten", "Keten", "yağ bitkisi"),
    "Elaeis guineensis": ("yag_palmiyesi", "Yağ palmiyesi", "yağ bitkisi"),
    "Cocos nucifera": ("hindistan_cevizi", "Hindistan cevizi", "yağ bitkisi"),
    # Endustriyel ve icecek
    "Saccharum officinarum": ("seker_kamisi", "Şeker kamışı", "endüstriyel"),
    "Gossypium hirsutum": ("pamuk", "Pamuk", "endüstriyel"),
    "Nicotiana tabacum": ("tutun", "Tütün", "endüstriyel"),
    "Coffea arabica": ("kahve", "Kahve (arabika)", "içecek"),
    "Camellia sinensis": ("cay", "Çay", "içecek"),
    "Theobroma cacao": ("kakao", "Kakao", "içecek"),
    "Humulus lupulus": ("serbetciotu", "Şerbetçiotu", "endüstriyel"),
    # ----------------------------------------------------------------------
    # 2026-07 EKLEMESI. Kullanici kendi koyunu (Bursa Hasanaga) sordu ve orada
    # yaygin olan ENGINAR listede hic cikmadi. Sebep model degildi: enginar
    # (Cynara scolymus) EcoCrop'ta VAR, bizim secim listemizde YOKTU. Yani
    # model enginari "uygun degil" demiyordu, varligindan haberi yoktu.
    #
    # Bu vesileyle EcoCrop'ta bulunup listemizde olmayan yaygin turleri taradik.
    # Asagidakilerin hepsinin TMIN/TMAX/RMIN/RMAX/PHMIN/PHMAX bantlari EcoCrop'ta
    # DOLU; bant eksigi olanlar (musmula, bogurtlen, sudan otu) BILEREK alinmadi,
    # cunku bant eksik olunca urun yaniltici puan alir.
    #
    # HASHAS (Papaver somniferum) ve KENEVIR (Cannabis sativa) bantlari tam
    # oldugu halde BILEREK alinmadi: ikisi de Turkiye'de ekimi izne tabi. Bir
    # ciftciye lisans sartini soylemeden "bunu ek" demek onu hukuki sikintiya
    # sokar. Uyari metniyle birlikte eklenebilirler, sessizce eklenemezler.
    # Sebze
    "Cynara scolymus": ("enginar", "Enginar", "sebze"),
    "Apium graveolens": ("kereviz", "Kereviz", "sebze"),
    "Beta vulgaris var. cicla": ("pazi", "Pazı", "sebze"),
    "Cichorium intybus": ("hindiba", "Hindiba", "sebze"),
    "Asparagus officinalis": ("kuskonmaz", "Kuşkonmaz", "sebze"),
    "Foeniculum vulgare": ("rezene", "Rezene", "sebze"),
    "Pastinaca sativa": ("yaban_havucu", "Yaban havucu", "kök/yumru"),
    # Baharat ve tibbi bitkiler: kucuk alanda yuksek katma deger urettikleri
    # icin kucuk ciftci acisindan onemli, ayri grup olarak gosteriliyor.
    "Petroselinum crispum": ("maydanoz", "Maydanoz", "baharat/tıbbi"),
    "Anethum graveolens": ("dereotu", "Dereotu", "baharat/tıbbi"),
    "Coriandrum sativum": ("kisnis", "Kişniş", "baharat/tıbbi"),
    "Cuminum cyminum": ("kimyon", "Kimyon", "baharat/tıbbi"),
    "Trigonella foenum-graecum": ("cemen", "Çemen otu", "baharat/tıbbi"),
    "Mentha piperita": ("nane", "Nane", "baharat/tıbbi"),
    "Ocimum basilicum": ("reyhan", "Reyhan (fesleğen)", "baharat/tıbbi"),
    "Origanum vulgare": ("kekik", "Kekik", "baharat/tıbbi"),
    "Lavandula angustifolia": ("lavanta", "Lavanta", "baharat/tıbbi"),
    # Meyve
    "Cydonia oblonga": ("ayva", "Ayva", "meyve"),
    "Morus alba": ("dut", "Dut", "meyve"),
    "Diospyros kaki": ("trabzon_hurmasi", "Trabzon hurması", "meyve"),
    "Ribes uva-crispa": ("bektasi_uzumu", "Bektaşi üzümü", "meyve"),
    # Baklagil ve yem
    "Lupinus albus": ("aci_bakla", "Acı bakla (termiye)", "baklagil"),
    "Trifolium pratense": ("ucgul", "Üçgül (kırmızı yonca)", "yem bitkisi"),
    "Lolium perenne": ("ingiliz_cimi", "İngiliz çimi", "yem bitkisi"),
    "Vicia sativa ssp. nigra": ("fig", "Fiğ", "yem bitkisi"),
}

# EcoCrop TEXT (optimal toprak dokusu) -> bizim USDA sinifi adlarimiz.
# recommender._texture_class su siniflari uretir: kil, killi_tin, tin,
# siltli_tin, kumlu_tin, kum. EcoCrop yalnizca kaba 3 kategori verir.
DOKU_ESLEME = {
    "heavy": ["kil", "killi_tin"],
    "medium": ["tin", "siltli_tin", "killi_tin"],
    "light": ["kumlu_tin", "kum"],
    "organic": [],   # SoilGrids dokusundan cikarilamaz, atlanir
}


def _sayi(deger: str) -> float | None:
    d = (deger or "").strip()
    if d in ("", "NA"):
        return None
    try:
        return float(d)
    except ValueError:
        return None


def _bant(r: dict, mn: str, omn: str, omx: str, mx: str) -> dict | None:
    """EcoCrop dortlusunu trapez banda cevirir. Sirasi bozuksa None doner."""
    v = [_sayi(r[k]) for k in (mn, omn, omx, mx)]
    if any(x is None for x in v):
        return None
    lo, a, b, hi = v
    # Trapez matematigi lo < a <= b < hi sart. Aksi halde _trapezoid sifira boler.
    if not (lo < a <= b < hi):
        return None
    return {"min": lo, "opt_min": a, "opt_max": b, "max": hi}


def _doku(r: dict) -> list[str]:
    cikti: list[str] = []
    for parca in (r.get("TEXT") or "").split(","):
        for s in DOKU_ESLEME.get(parca.strip().lower(), []):
            if s not in cikti:
                cikti.append(s)
    return cikti


def _sezon(r: dict) -> str:
    """GMIN/GMAX = urun donguSU (gun). Bize ekim-hasat suresini verir."""
    gmin, gmax = _sayi(r.get("GMIN", "")), _sayi(r.get("GMAX", ""))
    if gmin is None or gmax is None:
        return ""
    if gmin >= 365:
        return "Çok yıllık"
    if gmin == gmax:
        return f"Yaklaşık {gmin:.0f} günlük dönem"
    return f"{gmin:.0f}-{gmax:.0f} günlük yetişme dönemi"


def _dongu(r: dict) -> tuple[int, int] | None:
    """(GMIN, GMAX) gun. Ekim penceresi taramasinda kac ay surdugu icin sart."""
    gmin, gmax = _sayi(r.get("GMIN", "")), _sayi(r.get("GMAX", ""))
    if gmin is None or gmax is None or gmax <= 0:
        return None
    return int(gmin), int(gmax)


def _cok_yillik(r: dict) -> bool:
    """LISPA alanindan cok yillik mi. 'annual, perennial' ise tek yillik sayilir.

    Gerekce: ikisi de mumkunse urun pratikte tek yillik olarak ekilebilir, yani
    kisi tarlada gecirmek zorunda degildir. Boyle sayarak fazla eleme yapmayiz.
    """
    lispa = (r.get("LISPA") or "").lower()
    return "perennial" in lispa and "annual" not in lispa


# EKSIK KIS DAYANIKLILIGI TAMAMLAMASI - EcoCrop'tan DEGIL, elle eklendi.
#
# NEDEN GEREKLI: cok yillik 43 urunun 10'unda EcoCrop'un KTMPR alani da KTMP alani
# da bos. Oneri motoru cok yilliklari kis dayanikliligina gore eliyor; verisi
# olmayan urun bu elemeden SESSIZCE muaf kaliyordu. Olctuk, sonuc tehlikeliydi:
# Antalya'da (olculen mutlak minimum -2.3 C) ANANAS 97.3 puanla 3. sirada cikti.
# Ananas donda olur. Bu, ciftciye para kaybettirecek bir oneridir; veri eksikligi
# "sinir yok" diye yorumlanamaz.
#
# NEDEN ELLE DEGER: ayni bosluk mandalinada da var ve mandalina Antalya'nin ana
# urunu. Kaba bir kural (orn. "TMIN >= 10 ise tropik say, ele") ananasi dogru
# eler ama mandalinayi da yanlislikla eler; cunku mandalina TMIN'i yuksek olmasina
# ragmen -8 C'ye dayanan en dayanikli narenciyedir. Yani bu bosluk formulle
# kapatilamaz, tur bazinda bilgi gerekir.
#
# Degerler bahcecilik literaturunde yerlesik, korumasiz ve olgun bitki icin
# bilinen don esikleridir. EcoCrop kaynakli OLMADIKLARI icin ayri tutuluyor ve
# uretilen YAML'de kaynagi "elle" olarak isaretleniyor.
KIS_DAYANIMI_ELLE: dict[str, float] = {
    "mas_fasulyesi":      2.0,    # Vigna radiata, don dayanimi yok
    "guvercin_bezelyesi": 0.0,    # Cajanus cajan, don bitkiyi oldurur
    "taro":               0.0,    # Colocasia, yumru donarsa curur
    "mandalina":         -8.0,    # Citrus reticulata, en dayanikli yaygin narenciye
    "ananas":             0.0,    # Ananas comosus, don olduruculdur
    "cilek":            -10.0,    # Fragaria, taci kar altinda kisi gecirir
    "kestane":          -25.0,    # Castanea sativa, soguk iklim agaci
    "yag_palmiyesi":      2.0,    # Elaeis guineensis, kesin tropik
    "kahve":              0.0,    # Coffea arabica, don mahsulu bitirir
    "serbetciotu":      -20.0,    # Humulus lupulus, kok govdesi cok dayanikli
    "dut":              -30.0,    # Morus alba, EcoCrop'ta KTMP ve KTMPR ikisi de NA
}


# ECOCROP'UN KTMPR ALANI YANLIS OLAN TURLER - olculdu, dogrulandi, duzeltildi.
#
# YUKARIDAKI tablodan FARKI: orada EcoCrop alani BOSTU, burada DOLU AMA YANLIS.
#
# NASIL FARK EDILDI: kullanici Bursa Hasanaga koyunu sordu, model seftaliyi
# "Uygun degil" diye eledi. Bursa Turkiye'nin seftali merkezi. Elemenin gerekcesi
# "olculen en dusuk -13.5 C, urunun siniri -5 C" idi.
#
# NEDEN YANLIS OLDUGU KESIN: EcoCrop'un ham CSV'sinde Prunus persica icin
# KTMP = -5 ve KTMPR = -5, yani IKI ALAN AYNI. Oysa elmada -2 / -30, uzumde
# -3 / -20, armutta -9 / -34. Yani EcoCrop bu turlerde kis dinlenmesi alanini
# ayrica doldurmamis, cicek donu degerini oraya kopyalamis. Kopyalanan sayilar
# da tam olarak cicek donu araligina denk geliyor: Michigan State Extension
# tam cicek doneminde -2.2 C'de %10, -4.4 C'de %90 cicek kaybi bildiriyor;
# YAML'daki kiraz -3 ve seftali -5 bu araligin icinde.
#
# NEDEN OTOMATIK KURAL YAZILMADI: "KTMP ile KTMPR birbirine yakinsa bozuktur"
# kuralini denedik, muzu (1/1), papayayi (-1/-1), mangoyu (0/-1) da isaretledi.
# Oysa tropik bitkide iki alanin esit olmasi DOGRUDUR, cunku kis dinlenmesi yok.
# Ayrim tur bilgisi ister; zeytin -10, incir -12, nar -10, kivi -9 dogrudur ve
# hicbir formul bunlari asagidaki listeden ayiramaz.
#
# DEGERLER NEREDEN: Michigan State Extension'in kis dayanikliligi siralamasi
# "armut > elma > kayisi > visne > kiraz > erik > seftali". Siralamanin iki ucu
# EcoCrop'ta zaten DOGRU (armut -34, elma -30); aradakiler bu iki capa arasina,
# siralamayi bozmadan yerlestirildi. Ayni kaynak Michigan'da seftali bahcelerinin
# -22 F (-30 C) ile zarar gordugunu bildiriyor.
#
# HASSASIYET UYARISI: 1 C'lik kesinlik iddiasi yoktur ve gerekli de degildir.
# Bu esik, olculen MUTLAK MINIMUM ile karsilastirilan bir eleme siniridir;
# onemli olan sayinin -5 mi yoksa -25 mi oldugudur, -25 mi -27 mi degil.
KIS_DAYANIMI_DUZELTME: dict[str, float] = {
    "kayisi":  -29.0,   # Prunus armeniaca, siralamada elmadan (-30) hemen sonra
    "visne":   -28.0,   # Prunus cerasus, kirazdan dayanikli
    "kiraz":   -27.0,   # Prunus avium
    "erik":    -26.0,   # Prunus domestica
    "seftali": -25.0,   # Prunus persica, siralamanin en dayaniksizi
    "findik":  -25.0,   # Corylus avellana, Karadeniz kiyisinin yerli agaci
    "badem":   -18.0,   # Prunus dulcis, siralamada yok; seftaliden dayaniksiz

    # OTSU COK YILLIKLAR - ayni alan, ayni bicimde bozuk.
    # Bunlar kisi toprak ALTINDA (tac, rizom, kok) gecirir; toprak alti hava
    # sicakligindan cok daha ilimandir. EcoCrop bu turlerde de KTMPR'ye yaprak
    # dokusunun oldugu sicakligi yazmis. Olctuk: EcoCrop'a gore kuskonmaz -5
    # C'de olur, oysa Almanya ve Michigan'in ana kuskonmaz bolgelerinde kis
    # sicakligi rutin olarak -15 C'nin altina iner.
    #
    # LIFO ALANIYLA OTOMATIKLESTIRILEMEDI: EcoCrop'un "herb" sinifinda ANANAS da
    # var. Ananas otsudur ama buyume noktasi toprak ustundedir ve donda olur;
    # "otsu ise elemeden muaf tut" kurali ananasi Antalya'ya geri onerirdi.
    "kuskonmaz": -30.0,  # Asparagus officinalis, tac toprak altinda
    "nane":      -30.0,  # Mentha piperita, rizomla kislar
    "kekik":     -25.0,  # Origanum vulgare
    "hindiba":   -25.0,  # Cichorium intybus, kaziksi kok
    "rezene":    -15.0,  # Foeniculum vulgare
    "maydanoz":  -10.0,  # Petroselinum crispum, iki yillik, kisi tarlada gecirir
    # EcoCrop'ta KTMPR = +1, KTMP = 0. Yani "dinlenmede olum siniri, buyumedeki
    # sinirdan SICAK". Bitki dinlenmedeyken daima daha dayaniklidir; bu deger
    # icsel olarak celiskili, dolayisiyla kullanilamaz.
    "enginar":   -10.0,  # Cynara scolymus, tac malc ile korunur
    # EcoCrop'ta KTMP = -20, KTMPR = -15; yine ters. Ikisinden SOGUK olani
    # aliyoruz, yani deger yine EcoCrop'un kendi verisinden geliyor.
    "lavanta":   -20.0,  # Lavandula angustifolia
}


def _verimlilik(r: dict) -> str | None:
    """EcoCrop FER alani: urunun toprak verimlilik ihtiyaci (low/moderate/high).

    Ingilizce anahtar olarak birakilir; Turkcelestirme sunum katmaninin isi ve
    besin karnesi bu degeri KARSILASTIRMA icin kullaniyor, gostermek icin degil.
    """
    fer = (r.get("FER") or "").strip()
    return fer if fer in ("low", "moderate", "high") else None


def _notlar(r: dict, grup: str) -> str:
    p = [f"Grup: {grup}."]
    ktmp = _sayi(r.get("KTMP", ""))
    if ktmp is not None:
        p.append(f"Erken gelişme/çiçek döneminde {ktmp:.0f} C altı don zararı yapar.")
    ktmpr = _sayi(r.get("KTMPR", ""))
    if ktmpr is not None and _cok_yillik(r):
        p.append(f"Kış dinlenmesinde dayanabildiği en düşük sıcaklık {ktmpr:.0f} C.")
    fer = (r.get("FER") or "").strip()
    if fer and fer != "NA":
        tr = {"low": "düşük", "moderate": "orta", "high": "yüksek"}.get(fer, fer)
        p.append(f"Toprak verimlilik ihtiyacı: {tr}.")
    sal = (r.get("SAL") or "").strip()
    if sal.startswith("low"):
        p.append("Tuzluluğa duyarlı.")
    elif sal.startswith("medium") or sal.startswith("high"):
        p.append("Tuzluluğa dayanıklı.")
    return " ".join(p)


def _yaz_yaml(kayitlar: dict[str, dict]) -> str:
    """Elle YAML yazariz: yorum satirlarini ve alan sirasini korumak icin."""
    sat = [
        "# KURESEL urun bilgi tabani - OTOMATIK URETILDI, ELLE DUZENLEME.",
        "# Ureten : scripts/build_crop_kb.py",
        "# Kaynak : FAO EcoCrop (github.com/OpenCLIM/ecocrop, EcoCrop_DB.csv)",
        "#",
        "# Sayilarin hicbiri tahmin degildir; dogrudan EcoCrop alanlarindan gelir:",
        "#   sicaklik <- TMIN/TOPMN/TOPMX/TMAX   (C, yetisme donemi)",
        "#   yagis_mm <- RMIN/ROPMN/ROPMX/RMAX   (mm, yillik)",
        "#   ph       <- PHMIN/PHOPMN/PHOPMX/PHMAX",
        "#   doku     <- TEXT (heavy/medium/light -> USDA siniflarimiz)",
        "#   sezon    <- GMIN/GMAX (urun dongusu, gun)",
        "#",
        "# DIKKAT: EcoCrop sicakligi YETISME DONEMI ortalamasidir, yillik ortalama",
        "# degildir. Oneri motoru bu yuzden yillik ortalamayi degil sicak donem",
        "# ortalamasini kullanmalidir; aksi halde tek yillik urunler haksiz yere",
        "# elenir. Ayrinti: models/crop_reco/recommender.py",
        "",
    ]
    for anahtar, k in kayitlar.items():
        sat.append(f"{anahtar}:")
        sat.append(f'  ad: "{k["ad"]}"')
        sat.append(f'  bilimsel_ad: "{k["bilimsel_ad"]}"')
        sat.append(f'  grup: "{k["grup"]}"')
        for alan in ("ph", "sicaklik", "yagis_mm"):
            b = k.get(alan)
            if b:
                sat.append(f"  {alan}: {{min: {b['min']:g}, opt_min: {b['opt_min']:g}, "
                           f"opt_max: {b['opt_max']:g}, max: {b['max']:g}}}")
        if k["doku"]:
            sat.append("  doku: [" + ", ".join(k["doku"]) + "]")
        if k["dongu"]:
            sat.append(f"  dongu_gun: {{min: {k['dongu'][0]}, max: {k['dongu'][1]}}}")
        sat.append(f"  cok_yillik: {'true' if k['cok_yillik'] else 'false'}")
        if k["don_buyume"] is not None:
            sat.append(f"  don_buyume_c: {k['don_buyume']:g}")
        if k["don_dinlenme"] is not None:
            sat.append(f"  don_dinlenme_c: {k['don_dinlenme']:g}")
            # Kaynak seffafligi: hangi deger EcoCrop'tan, hangisi elle eklendi.
            sat.append(f'  don_dinlenme_kaynak: "{k["don_kaynak"]}"')
        if k["verimlilik"]:
            # notlar icinde zaten cumle olarak geciyor, ama besin karnesi bunu
            # KARAR icin kullaniyor. Metinden ayiklamak, cumle bir gun yeniden
            # yazildiginda sessizce bozulacak bir bagimlilik olurdu.
            sat.append(f'  verimlilik: "{k["verimlilik"]}"')
        if k["sezon"]:
            sat.append(f'  sezon: "{k["sezon"]}"')
        sat.append(f'  notlar: "{k["notlar"]}"')
        sat.append("")
    return "\n".join(sat)


def main() -> None:
    if not KAYNAK.exists():
        KAYNAK.parent.mkdir(parents=True, exist_ok=True)
        print(f"EcoCrop indiriliyor: {INDIR_URL}")
        istek = urllib.request.Request(INDIR_URL, headers={"User-Agent": "agri-app"})
        with urllib.request.urlopen(istek, timeout=180) as fh:
            KAYNAK.write_bytes(fh.read())

    metin = KAYNAK.read_text(encoding="utf-8", errors="replace")
    satirlar = {r["ScientificName"].strip(): r
                for r in csv.DictReader(io.StringIO(metin))}

    kayitlar: dict[str, dict] = {}
    eksik_tur: list[str] = []
    eksik_bant: list[str] = []

    for bilimsel, (anahtar, ad, grup) in SECIM.items():
        r = satirlar.get(bilimsel)
        if r is None:
            eksik_tur.append(bilimsel)
            continue
        ph = _bant(r, "PHMIN", "PHOPMN", "PHOPMX", "PHMAX")
        sic = _bant(r, "TMIN", "TOPMN", "TOPMX", "TMAX")
        yag = _bant(r, "RMIN", "ROPMN", "ROPMX", "RMAX")
        if sic is None or yag is None or ph is None:
            # Skorlamanin uc ana ayagi; biri yoksa urun yaniltici puan alir.
            bos = [n for n, b in (("pH", ph), ("sicaklik", sic), ("yagis", yag)) if b is None]
            eksik_bant.append(f"{ad} ({bilimsel}): {', '.join(bos)}")
            continue
        dongu = _dongu(r)
        # "is not None" sart: KTMPR degeri 0 olan urunler var (kahve, taro gibi)
        # ve "or" ile yazarsak 0 yanlislikla "veri yok" sayilirdi.
        ktmpr = _sayi(r.get("KTMPR", ""))
        elle = KIS_DAYANIMI_ELLE.get(anahtar)
        duzeltme = KIS_DAYANIMI_DUZELTME.get(anahtar)
        kayitlar[anahtar] = {
            "ad": ad, "bilimsel_ad": bilimsel, "grup": grup,
            "ph": ph, "sicaklik": sic, "yagis_mm": yag,
            "doku": _doku(r),
            "dongu": dongu,
            # Cok yillik ayrimi LISPA'dan gelir, GMIN'den DEGIL. Ilk denememde
            # "GMIN >= 365" kullandim ve elma tek yillik cikti (GMIN=180, cunku
            # GMIN meyve dongusudur, agacin omru degil). LISPA dogru alan.
            "cok_yillik": _cok_yillik(r),
            # KTMP  = erken buyume/cicek doneminde oldurucu sicaklik (elma -2)
            # KTMPR = kis dinlenme doneminde oldurucu sicaklik  (elma -30)
            # Ikisi cok farkli seyler; ayri tutulmasi sart. Cok yillik urun kisi
            # tarlada gecirdigi icin KTMPR onun icin eleyici, tek yilliklar icinse
            # KTMP ekim penceresini belirler.
            "don_buyume": _sayi(r.get("KTMP", "")),
            # EcoCrop bos biraktiysa elle tamamlanan tablodan al (bkz KIS_DAYANIMI_ELLE).
            # Bos birakmak "sinirsiz dayanikli" anlamina geliyordu ve olcumde
            # Antalya'ya ananas onerdirdi.
            # Oncelik: duzeltme > ecocrop > elle. Duzeltme en ustte, cunku
            # EcoCrop'un o alani DOLU ama yanlis (bkz KIS_DAYANIMI_DUZELTME);
            # "ktmpr varsa onu kullan" deseydik hata YAML'a gecmeye devam ederdi.
            "don_dinlenme": (duzeltme if duzeltme is not None
                             else (ktmpr if ktmpr is not None else elle)),
            "don_kaynak": ("duzeltme" if duzeltme is not None
                           else ("ecocrop" if ktmpr is not None
                                 else ("elle" if elle is not None else None))),
            "sezon": _sezon(r), "notlar": _notlar(r, grup),
            "verimlilik": _verimlilik(r),
        }

    # Sozlukteki bir anahtar hicbir urune denk gelmediyse (yazim hatasi, urun
    # listeden cikarilmis) duzeltme SESSIZCE uygulanmamis olur ve seftali yine
    # elenir. Sessiz kalmasindansa gurultu cikarsin.
    for tablo_ad, tablo in (("KIS_DAYANIMI_DUZELTME", KIS_DAYANIMI_DUZELTME),
                            ("KIS_DAYANIMI_ELLE", KIS_DAYANIMI_ELLE)):
        bosa = sorted(set(tablo) - set(kayitlar))
        if bosa:
            raise SystemExit(
                f"{tablo_ad} icindeki su anahtarlar hicbir urune denk gelmedi: "
                f"{', '.join(bosa)}. Yazim hatasi olabilir ya da urun bilgi "
                f"tabanindan cikarilmis olabilir; duzeltme uygulanmadan YAML "
                f"yazilmaz.")

    # Cok yillik urunun kis dayanikliligi YOKSA oneri motoru onu don elemesinden
    # SESSIZCE muaf tutar ve urun her yerde yuksek puan alir. Iki kere basimiza
    # geldi: once ananas Antalya'da 3. sirada cikti, sonra DUT Bursa'da 100 aldi
    # (EcoCrop'ta KTMP ve KTMPR ikisi de NA). Ikisinde de hata sessizdi; sayilar
    # makul gorundugu icin bakarken fark edilmedi. Artik uretim duruyor.
    kis_yok = sorted(k["ad"] for k in kayitlar.values()
                     if k["cok_yillik"] and k["don_dinlenme"] is None)
    if kis_yok:
        raise SystemExit(
            f"Su cok yillik urunlerde kis dayanikliligi yok: {', '.join(kis_yok)}. "
            f"Bos birakmak 'sinirsiz dayanikli' anlamina gelir ve urun don "
            f"elemesinden muaf kalir. KIS_DAYANIMI_ELLE tablosuna ekleyin.")

    CIKTI.write_text(_yaz_yaml(kayitlar), encoding="utf-8")
    ATIF.write_text(
        "# Urun parametrelerinin kaynagi\n\n"
        "`knowledge/crop_params_global.yaml` icindeki sicaklik, yagis, pH ve doku\n"
        "esikleri **FAO EcoCrop** veritabanindan otomatik uretilmistir.\n\n"
        "- Veri: EcoCrop_DB.csv, https://github.com/OpenCLIM/ecocrop\n"
        "- Kurum: FAO (Birlesmis Milletler Gida ve Tarim Orgutu), 2568 tur\n"
        "- EcoCrop 2015'te durduruldu, veri GAEZ v4 portali uzerinden yasiyor\n\n"
        f"Bu dosyada {len(kayitlar)} urun var. Secim ve Turkce adlandirma bize aittir.\n"
        "Sicaklik, yagis, pH ve doku sayilari EcoCrop'tan geldigi gibidir.\n\n"
        "## Kis dayanikligi (`don_dinlenme_c`) bir istisnadir\n\n"
        "Her kaydin yaninda `don_dinlenme_kaynak` alani vardir ve uc deger alir:\n\n"
        "- `ecocrop` : dogrudan EcoCrop KTMPR alanindan.\n"
        "- `elle`    : EcoCrop'ta bu alan BOSTU. Bos birakmak \"sinirsiz dayanikli\"\n"
        "  anlamina geliyordu; olctugumuzde Antalya'ya ananas onerildi.\n"
        "- `duzeltme`: EcoCrop'ta alan DOLU ama YANLIS. Yaprak doken ilıman iklim\n"
        "  meyvelerinde (Prunus turleri, findik) EcoCrop kis dinlenmesi alanina\n"
        "  cicek donu degerini kopyalamis: Prunus persica icin KTMP ve KTMPR ikisi\n"
        "  de -5. Karsilastirma icin elma -2/-30, armut -9/-34. Duzeltilmis degerler\n"
        "  Michigan State Extension'in kis dayanikligi siralamasina dayanir ve\n"
        "  EcoCrop'un dogru oldugu iki uca (armut -34, elma -30) gore yerlestirilmistir.\n\n"
        "Yani sayilarin cogunlugu EcoCrop'tan gelir, ama HEPSI degil. Hangisinin\n"
        "nereden geldigi YAML'da her urun icin ayri ayri yazilidir.\n\n"
        "Yeniden uretmek icin: `py -m scripts.build_crop_kb`\n",
        encoding="utf-8")

    print(f"{len(kayitlar)} urun yazildi -> {CIKTI.relative_to(ROOT)}")
    gruplar: dict[str, int] = {}
    for k in kayitlar.values():
        gruplar[k["grup"]] = gruplar.get(k["grup"], 0) + 1
    for g, n in sorted(gruplar.items(), key=lambda kv: -kv[1]):
        print(f"  {g:14s} {n}")
    if eksik_tur:
        print(f"\nEcoCrop'ta BULUNAMAYAN tur ({len(eksik_tur)}): {eksik_tur}")
    if eksik_bant:
        print(f"\nBANDI EKSIK oldugu icin ATLANAN ({len(eksik_bant)}):")
        for s in eksik_bant:
            print(f"  {s}")
    print(f"\nAtif dosyasi: {ATIF.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
