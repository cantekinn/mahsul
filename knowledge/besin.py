"""Toprak besin karnesi: olculen degerlerden ne cikarilabilir, ne cikarilamaz.

BU MODUL GUBRE DOZU YAZMAZ. Sebebi teknik: bir azot dozu, urunun kaldirdigi
azot ile topragin verdigi azotun FARKIDIR. Kaldirma miktari urun ve hedef
verime bagli bir tablo ister, topragin verdigi azot ise mineralizasyon hizini
olcen bir inkubasyon denemesi ister. Ikisi de elimizde YOK. Elde olmayan iki
sayidan cikarma yapip sonucu "kg/da" diye yazmak, ciftcinin tarlasina gercek
gubre atmasina sebep olurdu; o yuzden yazilmiyor ve NEDEN yazilmadigi
kullaniciya soyleniyor.

Yazilan sey su: topragin olculen hali, o olcumlerden KESIN cikan sonuclar
(organik madde, azot stogu, C/N, pH'in kilitledigi elementler, tutma
kapasitesi) ve olculemeyenler icin hangi laboratuvar testinin istenecegi.

SAYILARIN KAYNAGI (uc kategori, karistirilmamali):

1) OLCULEN  - SoilGrids 2.0 rasterinden gelir. Bu modul I/O yapmaz; cagiran
   taraf 0-30 cm kalinlik agirlikli degerleri verir (data/soilgrids_wcs.py
   wcs_surum_katmani). Derinlik onemli: 0-5 cm katmani organik karbonu Turk
   tarim topraklarinda 1.79-1.80 kat fazla gosteriyor (olculdu, bkz. o dosya).

2) HESAPLANAN - burada aritmetikle uretilir, ara adimlar test dosyasinda elle
   dogrulanir (tests/test_besin.py).

3) ESIK      - literaturden gelen sinif sinirlaridir, olcum degildir. Her
   birinin kaynagi asagida sabitin yaninda yazili. Esikler karar verdirir ama
   sayi uretmez; bir esigi degistirmek "orta" yazan yeri "iyi" yapar, hicbir
   hesabi bozmaz.
"""
from __future__ import annotations


class BesinVeriYok(Exception):
    """Karne icin gereken olcum yok.

    fao56.KcYok ile ayni sebeple var: eksik olcumun yerine makul gorunen bir
    varsayilan koymak (orn. yigin yogunlugu 1.4) sonucu HESAP gibi gosterir.
    Hesap olmayan seyin hesap gibi gorunmesi bu projede yasak.
    """


# --- Esikler ve donusum sabitleri -----------------------------------------

# Van Bemmelen carpani: organik maddenin kutlece %58'i karbondur, 100/58 = 1.724.
# Toprak analiz raporlarinin organik madde satiri bu carpanla uretilir.
SOM_CARPANI = 1.724

# Organik madde (%) siniflari. Turkiye'deki toprak analiz raporlarinda
# kullanilan siniflandirma. ESIKTIR, olcum degil.
OM_SINIFLARI = ((1.0, "çok az"), (2.0, "az"), (3.0, "orta"), (4.0, "iyi"))

# Katyon degisim kapasitesi, cmol(c)/kg. Toprak etudu siniflari.
# Karsilastirma icin: 50 onbellek noktasinda olculen dagilim
# min 7.1 / ortanca 23.7 / maks 40.3.
KDK_SINIFLARI = ((12.0, "düşük"), (25.0, "orta"))

# pH siniflari (su ile 1:1 suspansiyon, SoilGrids phh2o ile ayni yontem).
PH_SINIFLARI = ((5.5, "kuvvetli asit"), (6.5, "hafif asit"),
                (7.5, "nötr"), (8.5, "hafif alkali"))

# C/N esikleri.
#   24 : TUREVDIR, tablo degil. Ayristirici mikroorganizmalarin govdesinde
#        yaklasik 8 karbona 1 azot dusuyor ve tukettikleri karbonun ancak
#        ucte birini govdeye cevirip gerisini solunumla harciyorlar. Yani bir
#        birim azotu baglamak icin 8 / (1/3) = 24 birim karbon gerekiyor. Bunun
#        uzerindeki malzeme, azotini kendi ayristirmasina yetiremedigi icin
#        topraktaki mineral azoti CEKER (immobilizasyon).
#    8 / 15 : olculen bandin kenarlari. 50 kuresel noktada olculen C/N dagilimi
#        min 6.21 / p25 8.63 / ortanca 12.01 / p75 13.52 / maks 18.00 idi; yani
#        tarim topraklarinin govdesi 8-15 arasinda ve immobilizasyon esigi olan
#        24'e hicbir nokta yaklasmadi.
CN_HIZLI = 8.0
CN_YAVAS = 15.0
CN_IMMOBILIZASYON = 24.0

# Bir dekar = 1000 m2. Yigin yogunlugu g/cm3 = t/m3 oldugu icin
# kutle (t) = 1000 m2 x derinlik(m) x yogunluk(t/m3).
DEKAR_M2 = 1000.0


# --- Tek tek hesaplar ------------------------------------------------------

def organik_madde(organik_karbon_g_kg: float) -> float:
    """Organik madde yuzdesi.

    soc g/kg -> %C: 10'a bolunur (1 g/kg = %0.1). Sonra Van Bemmelen carpani.
    Ornek: 23.28 g/kg -> 2.328 %C -> 4.01 % organik madde.
    """
    if organik_karbon_g_kg is None or organik_karbon_g_kg <= 0:
        raise BesinVeriYok("organik karbon olcumu yok")
    return organik_karbon_g_kg / 10.0 * SOM_CARPANI


def azot_stogu_kg_da(azot_g_kg: float, yigin_yogunlugu: float,
                     derinlik_cm: float = 30.0) -> float:
    """Belirtilen derinlikteki TOPLAM azot, kg/dekar.

    kutle(kg) = 1000 m2 x (derinlik_cm/100) m x yogunluk(t/m3) x 1000 kg/t
    azot(kg)  = kutle(kg) x azot(g/kg) / 1000

    Ornek (Bursa Karacabey, olculen): 1.96 g/kg, 1.38 g/cm3, 30 cm
      kutle = 1000 x 0.30 x 1.38 x 1000 = 414 000 kg
      azot  = 414 000 x 1.96 / 1000     = 811.4 kg N/da

    DIKKAT: bu TOPLAM azottur, alinabilir azot DEGILDIR. Toplam azotun asagi
    yukari tamami organik baglidir ve bitkiye ancak mineralize oldukca gecer.
    O gecis hizi bu olcumlerden hesaplanamaz (inkubasyon denemesi ister), bu
    yuzden karne "su kadarini bu yil kullanabilirsin" demez.
    """
    if azot_g_kg is None or azot_g_kg <= 0:
        raise BesinVeriYok("azot olcumu yok")
    if yigin_yogunlugu is None or yigin_yogunlugu <= 0:
        raise BesinVeriYok("yigin yogunlugu olcumu yok")
    kutle_kg = DEKAR_M2 * (derinlik_cm / 100.0) * yigin_yogunlugu * 1000.0
    return kutle_kg * azot_g_kg / 1000.0


def karbon_azot(organik_karbon_g_kg: float, azot_g_kg: float) -> float:
    """C/N orani. Ikisi de g/kg oldugu icin sonuc birimsizdir."""
    if not organik_karbon_g_kg or not azot_g_kg:
        raise BesinVeriYok("C/N icin organik karbon ve azot olcumu gerekli")
    return organik_karbon_g_kg / azot_g_kg


def _sinif(deger: float, siniflar: tuple, ust: str) -> str:
    for sinir, ad in siniflar:
        if deger < sinir:
            return ad
    return ust


def kilitli_elementler(ph: float) -> list[dict]:
    """Bu pH'ta bitkinin TOPRAKTA VAR OLANI alamadigi elementler.

    Eksiklik ile alinamazlik ayri seylerdir ve karistirilmasi pahaliya patlar:
    element toprakta yeterliyken pH yuzunden cozunmuyorsa gubre atmak parayi
    ve azaltim potansiyelini bosa harcar, cozum kireclemek veya asitlendirmek
    ya da yapraktan vermektir.

    Iliskinin kaynagi Truog'un (1946) element alinabilirligi diyagramidir;
    yonu ve esikleri toprak kimyasinda yerlesiktir: asit toprakta fosfor demir
    ve aluminyum fosfatlari olarak, kirecli toprakta kalsiyum fosfat olarak
    coker; demir, cinko ve mangan pH yukseldikce cozunurlugunu kaybeder.
    """
    if ph is None:
        raise BesinVeriYok("pH olcumu yok")
    kilit: list[dict] = []
    if ph < 5.5:
        kilit.append({"element": "Fosfor",
                      "sebep": "Asit toprakta demir ve alüminyum fosfatı olarak bağlanır"})
        kilit.append({"element": "Molibden",
                      "sebep": "Asit toprakta çözünürlüğü düşer"})
        kilit.append({"element": "Kalsiyum ve magnezyum",
                      "sebep": "Asit toprakta yıkanma ile uzaklaşmış olur"})
    if ph > 7.5:
        kilit.append({"element": "Fosfor",
                      "sebep": "Kireçli toprakta kalsiyum fosfat olarak çöker"})
        kilit.append({"element": "Demir",
                      "sebep": "Yüksek pH'ta çözünmez, yapraklarda kloroz görülür"})
        kilit.append({"element": "Çinko",
                      "sebep": "Yüksek pH'ta alınabilirliği belirgin düşer"})
        kilit.append({"element": "Mangan",
                      "sebep": "Yüksek pH'ta çözünürlüğü düşer"})
    return kilit


def laboratuvar_testleri(ph: float) -> list[dict]:
    """Olculemeyen elementler icin hangi test istenmeli.

    SoilGrids fosfor ve potasyum vermez; uydudan da olculemez, cunku ikisi de
    topragin kimyasal ekstraksiyonuyla belirlenir. Karnenin bu bolumu bir
    eksigi gizlemek yerine ciftciyi dogru teste yonlendirir.

    FOSFOR TESTININ SECIMI OLCULEN pH'A BAGLIDIR ve bu gercek bir karardir:
    Bray-1 ekstraksiyonu asit kullanir, kirecli toprakta kirec bu asidi
    notrlestirdigi icin sonuc oldugundan DUSUK cikar ve ciftci var olan fosforu
    yokmus sanip gereksiz gubre atar. Kirecli/alkali topraklarda bikarbonat
    esasli Olsen yontemi kullanilir.
    """
    if ph is None:
        raise BesinVeriYok("pH olcumu yok")
    fosfor = ("Olsen (0.5 M sodyum bikarbonat)" if ph >= 7.0
              else "Bray-1 (veya Mehlich-3)")
    gerekce = ("Toprak alkali; Bray-1 asidi kireç tarafından nötrlenir ve "
               "fosforu olduğundan düşük gösterir." if ph >= 7.0
               else "Toprak asit-nötr; Bray-1 bu aralıkta güvenilirdir.")
    return [
        {"element": "Fosfor", "test": fosfor, "gerekce": gerekce},
        {"element": "Potasyum", "test": "1 N amonyum asetat (pH 7)",
         "gerekce": "Değişebilir potasyum uydu verisinden ölçülemez."},
        {"element": "Tuzluluk (EC)", "test": "Saturasyon ekstraktında EC",
         "gerekce": "Tuzluluk ve sodiklik ancak ekstrakt ölçümüyle bilinir."},
    ]


# --- Karne -----------------------------------------------------------------

def besin_karnesi(toprak, urun_kaydi: dict | None = None,
                  derinlik_cm: float = 30.0) -> dict:
    """Olculen toprak degerlerinden besin karnesi.

    toprak: SoilData benzeri nesne (ph, nitrogen, organic_carbon, bulk_density,
            cec, sand alanlari okunur). 0-30 cm agirlikli olmasi beklenir.
    urun_kaydi: crop_params_global.yaml kaydi (ph araligi ve verimlilik alani
            kullanilir). None ise urune ozel bolum uretilmez.

    Her bolum bagimsiz olarak "hesaplanamadi" olabilir ve sebebi yazilir;
    tek bir eksik olcum tum karneyi dusurmez.
    """
    o = lambda ad: getattr(toprak, ad, None)  # noqa: E731
    karne: dict = {"olculen": {}, "bolumler": [], "eksik": []}

    for ad, etiket, birim in (("ph", "pH", ""),
                              ("nitrogen", "Azot", "g/kg"),
                              ("organic_carbon", "Organik karbon", "g/kg"),
                              ("bulk_density", "Yığın yoğunluğu", "g/cm3"),
                              ("cec", "Katyon değişim kapasitesi", "cmol/kg"),
                              ("clay", "Kil", "%"), ("sand", "Kum", "%")):
        if o(ad) is not None:
            karne["olculen"][ad] = {"ad": etiket, "deger": o(ad), "birim": birim}

    # Organik madde
    try:
        om = organik_madde(o("organic_carbon"))
        karne["bolumler"].append({
            "anahtar": "organik_madde", "baslik": "Organik madde",
            "deger": round(om, 2), "birim": "%",
            "sinif": _sinif(om, OM_SINIFLARI, "yüksek"),
            "aciklama": "Organik karbon ölçümünden Van Bemmelen çarpanı (1.724) "
                        f"ile hesaplandı. Derinlik 0-{derinlik_cm:.0f} cm.",
        })
    except BesinVeriYok as e:
        karne["eksik"].append({"anahtar": "organik_madde", "sebep": str(e)})

    # Toplam azot stogu
    try:
        stok = azot_stogu_kg_da(o("nitrogen"), o("bulk_density"), derinlik_cm)
        karne["bolumler"].append({
            "anahtar": "azot_stok", "baslik": "Toplam azot stoku",
            "deger": round(stok, 1), "birim": "kg/da", "sinif": None,
            "aciklama": f"0-{derinlik_cm:.0f} cm derinlikteki toplam azot. "
                        "Bunun neredeyse tamamı organik bağlıdır; bitkiye "
                        "ancak mineralize oldukça geçer. Yıllık ne kadarının "
                        "açığa çıkacağı bu ölçümlerden hesaplanamaz.",
        })
    except BesinVeriYok as e:
        karne["eksik"].append({"anahtar": "azot_stok", "sebep": str(e)})

    # C/N
    try:
        cn = karbon_azot(o("organic_carbon"), o("nitrogen"))
        if cn >= CN_IMMOBILIZASYON:
            sinif, yorum = "immobilizasyon", (
                "Ayrıştırıcılar kendi ihtiyaçları için topraktaki mineral azotu "
                "çeker; ekim döneminde bitki azotsuz kalabilir.")
        elif cn > CN_YAVAS:
            sinif, yorum = "yavaş", (
                "Organik azot yavaş açığa çıkıyor; sezon başında bitkinin "
                "ihtiyacı toprağın verdiğinden önce gelir.")
        elif cn < CN_HIZLI:
            sinif, yorum = "hızlı", (
                "Azot hızlı açığa çıkıyor; tek seferde verilen azotun bir kısmı "
                "bitki almadan yıkanabilir.")
        else:
            sinif, yorum = "dengeli", (
                "Tarım topraklarının olağan aralığında; azot salınımı ile "
                "bitkinin talebi kabaca örtüşür.")
        karne["bolumler"].append({
            "anahtar": "karbon_azot", "baslik": "C/N oranı",
            "deger": round(cn, 1), "birim": "", "sinif": sinif,
            "aciklama": yorum,
        })
    except BesinVeriYok as e:
        karne["eksik"].append({"anahtar": "karbon_azot", "sebep": str(e)})

    # Tutma kapasitesi
    if o("cec") is not None:
        kdk_sinif = _sinif(o("cec"), KDK_SINIFLARI, "yüksek")
        yorum = {
            "düşük": "Toprak besini az tutuyor; azot ve potasyum tek seferde "
                     "verilirse yıkanır, bölerek vermek gerekir.",
            "orta": "Besin tutma kapasitesi orta düzeyde.",
            "yüksek": "Toprak besini iyi tutuyor; yıkanma riski düşük.",
        }[kdk_sinif]
        karne["bolumler"].append({
            "anahtar": "kdk", "baslik": "Besin tutma kapasitesi (KDK)",
            "deger": o("cec"), "birim": "cmol/kg", "sinif": kdk_sinif,
            "aciklama": yorum,
        })
    else:
        karne["eksik"].append({"anahtar": "kdk", "sebep": "KDK olcumu yok"})

    # pH ve kilitlenen elementler
    try:
        kilit = kilitli_elementler(o("ph"))
        karne["bolumler"].append({
            "anahtar": "ph", "baslik": "Toprak reaksiyonu (pH)",
            "deger": o("ph"), "birim": "",
            "sinif": _sinif(o("ph"), PH_SINIFLARI, "kuvvetli alkali"),
            "aciklama": ("Bu pH'ta alınabilirliği kısıtlanan element yok."
                         if not kilit else
                         "Aşağıdaki elementler toprakta bulunsa bile bu pH'ta "
                         "bitkinin alabileceği biçimde değil."),
        })
        karne["kilitli"] = kilit
        karne["laboratuvar"] = laboratuvar_testleri(o("ph"))
    except BesinVeriYok as e:
        karne["eksik"].append({"anahtar": "ph", "sebep": str(e)})
        karne["kilitli"] = []
        karne["laboratuvar"] = []

    if urun_kaydi:
        karne["urun"] = _urun_bolumu(toprak, urun_kaydi, karne)
    return karne


def _urun_bolumu(toprak, urun: dict, karne: dict) -> dict:
    """Secilen urunun istegi ile olculen topragin karsilastirmasi."""
    o = lambda ad: getattr(toprak, ad, None)  # noqa: E731
    notlar: list[str] = []
    ph_araligi = urun.get("ph") or {}
    ph = o("ph")

    if ph is not None and ph_araligi:
        if ph < ph_araligi.get("min", -99) or ph > ph_araligi.get("max", 99):
            notlar.append(
                f"Ölçülen pH {ph}, bu ürünün yaşayabildiği aralığın "
                f"({ph_araligi['min']}-{ph_araligi['max']}) dışında.")
        elif ph < ph_araligi.get("opt_min", -99):
            notlar.append(
                f"Ölçülen pH {ph}, ürünün en verimli aralığının "
                f"({ph_araligi['opt_min']}-{ph_araligi['opt_max']}) altında.")
        elif ph > ph_araligi.get("opt_max", 99):
            notlar.append(
                f"Ölçülen pH {ph}, ürünün en verimli aralığının "
                f"({ph_araligi['opt_min']}-{ph_araligi['opt_max']}) üstünde.")

    # EcoCrop FER alani: urunun toprak verimlilik ihtiyaci.
    verimlilik = urun.get("verimlilik")
    if verimlilik == "high":
        om = next((b for b in karne["bolumler"] if b["anahtar"] == "organik_madde"), None)
        kdk = next((b for b in karne["bolumler"] if b["anahtar"] == "kdk"), None)
        if om and om["sinif"] in ("çok az", "az"):
            notlar.append(
                f"Bu ürünün toprak verimliliği ihtiyacı yüksek, ölçülen organik "
                f"madde ise {om['sinif']} ({om['deger']} %).")
        if kdk and kdk["sinif"] == "düşük":
            notlar.append(
                "Verimlilik ihtiyacı yüksek bir ürün, besini az tutan bir "
                "toprakta: gübreyi bölerek vermek şart.")

    return {
        "ad": urun.get("ad"),
        "verimlilik": verimlilik,
        "ph_araligi": ph_araligi or None,
        "notlar": notlar,
    }
