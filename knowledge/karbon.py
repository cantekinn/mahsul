"""Tarla karbon ayak izi (Sprint 3): IPCC 2019 Tier 1 sera gazi envanteri.

Sprint 2 sonunda karbon ajani `_stub("carbon", "[stub] ... Sprint 3'te gelecek")`
idi. Bu modul o stub'in yerini alan hesap cekirdegidir.

NE HESAPLIYOR
Bir parselin bir sezonluk dogrudan/dolayli sera gazi salimini kg CO2e olarak
dort kalemde verir:
  1. Azotlu gubreden DOGRUDAN N2O      (IPCC 2019 Vol4 Ch11, EF1)
  2. Azotlu gubreden DOLAYLI N2O       (volatilizasyon EF4 + yikanma EF5)
  3. Gubre URETIMI (upstream)          (amonyak sentezi, tarlada degil fabrikada)
  4. Dizel yakit                       (IPCC 2006 Vol2 Ch3 varsayilan)
  5. Sulama pompasi elektrigi          (hidrolik is / verim x sebeke faktoru)

NE HESAPLAMIYOR (bilerek, cunku girdisi yok)
- Toprak organik karbon stok degisimi: arazi kullanim gecmisi gerekir, tek
  noktadan bilinemez.
- Ure hidrolizinden CO2: gubrenin ure mi amonyum nitrat mi oldugu sorulmuyor;
  N cinsinden calisiyoruz. Ure kullanan tarlada ek ~0.73 kg CO2/kg N vardir.
- Kireclemeden CO2, ani kaliniti, pestisit uretimi, makine imalati.
Bu kalemler yanita "kapsam_disi" olarak yazilir; sessizce sifir sayilmaz.

NEDEN "gosterge" BAYRAGI VAR
Gubre ve yakit miktarini ciftciden baskasi bilemez. Girilmezse tablodaki
varsayilan kullanilir ve sonuc gosterge isaretlenir; bu, models/crop_reco/
gbdt.py'deki ayni desendir. Varsayilan uretilmis bir "gercek" gibi
sunulmaz.
"""
from __future__ import annotations

# --- Sabitler: her birinin yaninda kaynagi ---------------------------------

# IPCC AR6 (2021) Tablo 7.15, 100 yillik kuresel isinma potansiyeli.
# AR4'te 298, AR5'te 265 idi; AR6 degeri 273. Sayi degisince sonuc degisir,
# bu yuzden hangi raporun kullanildigi yanitta da yaziyor.
GWP_N2O = 273.0

# N2O-N -> N2O molekul agirligi donusumu (44/28). IPCC formullerinde N2O-N
# cinsinden hesaplanir, raporlama N2O cinsindendir.
_N_TO_N2O = 44.0 / 28.0

# IPCC 2019 Refinement, Vol 4 Ch 11, Tablo 11.1.
# EF1 iklime gore ayrisir (islak 0.016, kurak 0.005). Burada TOPLU deger
# kullaniliyor: iklim ayrimi icin yillik yagis/PET orani gerekir, onu 7 gunluk
# tahmin penceresinden uretmek olcumu degil tahmini tahmine dayandirmak olurdu.
EF1_DOGRUDAN = 0.010          # kg N2O-N / kg uygulanan N

# IPCC 2019, Tablo 11.3: sentetik gubrenin NH3/NOx olarak ucan orani.
FRAC_GASF = 0.11              # kg N ucan / kg N uygulanan
EF4_VOLATILIZASYON = 0.010    # kg N2O-N / kg ucan N

# IPCC 2019, Tablo 11.3: yikanma/akis orani (yagis > buharlasma olan yerlerde).
FRAC_LEACH = 0.24             # kg N yikanan / kg N uygulanan
EF5_YIKANMA = 0.011           # kg N2O-N / kg yikanan N

# Gubre uretimi (cradle-to-gate). Amonyak sentezi dogal gaz yakar; bu salim
# tarlada degil fabrikada olur ama urunun ayak izine girer.
# Deger: ure ve amonyum nitratin agirlikli kuresel ortalamasi.
EF_GUBRE_URETIM = 5.5         # kg CO2e / kg N

# IPCC 2006 Vol 2 Ch 3, Tablo 3.3.1 (dizel: 74.1 kg CO2/GJ),
# net kalorifik deger 43.0 GJ/t, yogunluk 0.832 kg/L:
#   74.1 x 0.0430 x 0.832 = 2.651
EF_DIZEL = 2.65               # kg CO2 / litre

# Turkiye sebeke elektrigi salim faktoru (uretim agirlikli ortalama).
EF_ELEKTRIK = 0.45            # kg CO2e / kWh

# Pompa hidroligi. E = rho x g x H x V / (3.6e6 x eta)
_RHO = 1000.0                 # kg/m3
_G = 9.81                     # m/s2
VERIM_POMPA = 0.60            # pompa x motor toplam verimi (saha kosulu)

# Sulama yontemine gore uygulama verimi (FAO-56 Tablo 20 tipik degerleri).
# Net su ihtiyaci bu verime BOLUNUR: salma sulamada tarlaya daha cok su
# cekilir, dolayisiyla daha cok pompa enerjisi harcanir.
SULAMA_VERIMI = {
    "damla": 0.90,
    "yagmurlama": 0.75,
    "salma": 0.60,
}

# Tipik basma yuksekligi (m). Kuyu derinligi + boru kaybi.
BASMA_YUKSEKLIGI = {
    "kuyu": 50.0,
    "yuzey": 20.0,
}

# Girilmezse kullanilan varsayilanlar. BUNLAR OLCUM DEGIL, buyukluk mertebesi
# yer tutucudur; ciftcinin kendi kaydi girildiginde gosterge bayragi duser.
VARSAYILAN_N_KG_DA = 20.0     # kg saf N / dekar / sezon
VARSAYILAN_DIZEL_L_DA = 8.0   # litre / dekar / sezon

KAPSAM_DISI = (
    "Toprak organik karbon stok değişimi (arazi kullanım geçmişi gerekir)",
    "Üre hidrolizinden CO2 (gübre cinsi sorulmuyor)",
    "Kireçlemeden CO2",
    "Pestisit ve makine üretimi",
)


class SulamaYontemiYok(KeyError):
    """Tanimsiz sulama yontemi (damla/yagmurlama/salma disinda)."""


def pompa_enerjisi_kwh(su_m3: float, yontem: str, basma_m: float) -> float:
    """Tarlaya cekilen suyun pompalanmasi icin gereken elektrik (kWh).

    su_m3 NET bitki su ihtiyacidir; uygulama verimine BOLUNEREK tarlaya
    gercekte cekilen hacme cevrilir. Damla ile salma sulama arasindaki fark
    tam olarak burada ortaya cikar.
    """
    verim = SULAMA_VERIMI.get(yontem)
    if verim is None:
        raise SulamaYontemiYok(yontem)
    brut_m3 = su_m3 / verim
    joule = _RHO * _G * basma_m * brut_m3          # kg/m3 * m/s2 * m * m3 = J
    return joule / (3.6e6 * VERIM_POMPA)


def ayak_izi(
    alan_m2: float,
    *,
    azot_kg_da: float | None = None,
    dizel_l_da: float | None = None,
    sulama_m3: float = 0.0,
    sulama_yontemi: str = "damla",
    su_kaynagi: str = "kuyu",
) -> dict:
    """Bir parselin sezonluk sera gazi envanteri.

    alan_m2      : parsel alani (m2)
    azot_kg_da   : uygulanan saf azot, kg/dekar/sezon. None -> varsayilan.
    dizel_l_da   : yakit tuketimi, litre/dekar/sezon. None -> varsayilan.
    sulama_m3    : sezon boyunca NET bitki su ihtiyaci (m3). 0 ise sulama
                   kalemi sifir yazilir (kuru tarim).
    sulama_yontemi: damla | yagmurlama | salma
    su_kaynagi   : kuyu | yuzey  (basma yuksekligini belirler)

    Donen sozlukte her kalem hem mutlak (kg CO2e) hem dekar basina verilir;
    ciftci kendi tarlasini baska tarlalarla ancak dekar basina karsilastirabilir.
    """
    if alan_m2 <= 0:
        raise ValueError("alan_m2 pozitif olmalı")

    dekar = alan_m2 / 1000.0
    gosterge = azot_kg_da is None or dizel_l_da is None
    azot_kg_da = VARSAYILAN_N_KG_DA if azot_kg_da is None else azot_kg_da
    dizel_l_da = VARSAYILAN_DIZEL_L_DA if dizel_l_da is None else dizel_l_da

    n_toplam = azot_kg_da * dekar          # kg saf N
    dizel_toplam = dizel_l_da * dekar      # litre

    # 1. Dogrudan N2O: uygulanan azotun bir kismi topraktan N2O olarak cikar.
    dogrudan = n_toplam * EF1_DOGRUDAN * _N_TO_N2O * GWP_N2O

    # 2. Dolayli N2O: once NH3/NOx olarak ucup baska yere coken azot, sonra
    #    yikanip suya karisan azot. Ikisi de sonunda N2O'ya donusur.
    volat = n_toplam * FRAC_GASF * EF4_VOLATILIZASYON * _N_TO_N2O * GWP_N2O
    yikan = n_toplam * FRAC_LEACH * EF5_YIKANMA * _N_TO_N2O * GWP_N2O
    dolayli = volat + yikan

    # 3. Gubrenin fabrikada uretilmesi.
    uretim = n_toplam * EF_GUBRE_URETIM

    # 4. Traktor yakiti.
    yakit = dizel_toplam * EF_DIZEL

    # 5. Sulama pompasi.
    basma = BASMA_YUKSEKLIGI.get(su_kaynagi, BASMA_YUKSEKLIGI["kuyu"])
    kwh = pompa_enerjisi_kwh(sulama_m3, sulama_yontemi, basma) if sulama_m3 else 0.0
    sulama = kwh * EF_ELEKTRIK

    kalemler = [
        {
            "ad": "Gübreden doğrudan N2O",
            "kg_co2e": round(dogrudan, 1),
            "kaynak": f"IPCC 2019 EF1={EF1_DOGRUDAN}, GWP100(N2O)={GWP_N2O:.0f}",
        },
        {
            "ad": "Gübreden dolaylı N2O",
            "kg_co2e": round(dolayli, 1),
            "kaynak": f"IPCC 2019 FracGASF={FRAC_GASF}/EF4={EF4_VOLATILIZASYON}, "
                      f"FracLEACH={FRAC_LEACH}/EF5={EF5_YIKANMA}",
        },
        {
            "ad": "Gübre üretimi",
            "kg_co2e": round(uretim, 1),
            "kaynak": f"{EF_GUBRE_URETIM} kg CO2e/kg N (amonyak sentezi)",
        },
        {
            "ad": "Dizel yakıt",
            "kg_co2e": round(yakit, 1),
            "kaynak": f"IPCC 2006, {EF_DIZEL} kg CO2/L",
        },
        {
            "ad": "Sulama pompası elektriği",
            "kg_co2e": round(sulama, 1),
            "kaynak": f"{kwh:.0f} kWh x {EF_ELEKTRIK} kg CO2e/kWh "
                      f"({sulama_yontemi}, {su_kaynagi}, {basma:.0f} m basma)",
        },
    ]
    toplam = sum(k["kg_co2e"] for k in kalemler)

    return {
        "alan_m2": round(alan_m2, 1),
        "dekar": round(dekar, 2),
        "gosterge": gosterge,
        "azot_kg_da": round(azot_kg_da, 1),
        "dizel_l_da": round(dizel_l_da, 1),
        "sulama_m3": round(sulama_m3, 1),
        "sulama_kwh": round(kwh, 1),
        "sulama_yontemi": sulama_yontemi,
        "su_kaynagi": su_kaynagi,
        "kalemler": kalemler,
        "toplam_kg_co2e": round(toplam, 1),
        "dekar_basina_kg_co2e": round(toplam / dekar, 1),
        "kapsam_disi": list(KAPSAM_DISI),
        "not": (
            "Gübre ve yakıt miktarı girilmedi; tablo varsayılanı kullanıldı. "
            "Sonuç büyüklük mertebesi göstergesidir, kendi kayıtlarınızı "
            "girdiğinizde gerçek hesaba döner."
            if gosterge
            else "Girilen gübre ve yakıt miktarlarıyla hesaplandı."
        ),
    }


def azaltim_onerileri(sonuc: dict) -> list[dict]:
    """Envanterdeki en buyuk kalemlere gore somut azaltim adimlari.

    Genel tavsiye listesi degil: hangi kalem buyukse ona ait oneri uretilir,
    ve azaltimin kg CO2e karsiligi HESAPLANIR. "Daha az gubre kullanin" demek
    kolaydir; "%20 azaltim bu tarlada 143 kg CO2e" demek karar verdirir.
    """
    kalem = {k["ad"]: k["kg_co2e"] for k in sonuc["kalemler"]}
    gubre = kalem["Gübreden doğrudan N2O"] + kalem["Gübreden dolaylı N2O"] + kalem["Gübre üretimi"]
    oneriler = []

    if gubre > 0:
        # Toprak analizine gore dozlama tipik olarak %20 fazla azotu keser.
        oneriler.append({
            "baslik": "Toprak analizine göre azot dozu",
            "aciklama": "Azot kaleminde %20 azaltım, verimi düşürmeden "
                        "genellikle toprak analiziyle sağlanır.",
            "kazanc_kg_co2e": round(gubre * 0.20, 1),
        })

    if sonuc["sulama_yontemi"] != "damla" and kalem["Sulama pompası elektriği"] > 0:
        mevcut = SULAMA_VERIMI[sonuc["sulama_yontemi"]]
        oran = 1.0 - (mevcut / SULAMA_VERIMI["damla"])
        oneriler.append({
            "baslik": "Damla sulamaya geçiş",
            "aciklama": f"Uygulama verimi {mevcut:.0%} yerine "
                        f"{SULAMA_VERIMI['damla']:.0%} olur; aynı bitki su "
                        "ihtiyacı için daha az su pompalanır.",
            "kazanc_kg_co2e": round(kalem["Sulama pompası elektriği"] * oran, 1),
        })

    if kalem["Dizel yakıt"] > 0:
        oneriler.append({
            "baslik": "Azaltılmış toprak işleme",
            "aciklama": "Pulluk yerine korumalı toprak işleme yakıt "
                        "tüketimini tipik olarak üçte bir azaltır.",
            "kazanc_kg_co2e": round(kalem["Dizel yakıt"] * 0.33, 1),
        })

    oneriler.sort(key=lambda o: o["kazanc_kg_co2e"], reverse=True)
    return oneriler
