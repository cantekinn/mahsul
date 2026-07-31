"""Besin karnesi testleri.

Beklenen degerlerin hicbiri koddan okunmadi; her biri asagida elle carpilip
bolundu. Bir testi koda bakarak yazmak, kodun yaptigi seyi tekrar yazmak olur
ve formul yanlissa test de ayni yanlisi onaylar.

Girdiler UYDURULMADI: Bursa Karacabey ve Sanliurfa Harran icin SoilGrids'ten
gercekten olculen 0-30 cm agirlikli degerler kullanildi.
"""
from __future__ import annotations

import pytest

from core.schemas import SoilData
from knowledge.besin import (
    BesinVeriYok,
    azot_stogu_kg_da,
    besin_karnesi,
    karbon_azot,
    kilitli_elementler,
    laboratuvar_testleri,
    organik_madde,
)

# Olculen degerler (data/soilgrids_wcs.py wcs_surum_katmani, 0-30 cm).
KARACABEY = SoilData(ph=7.07, nitrogen=1.96, organic_carbon=23.28,
                     bulk_density=1.38, cec=25.12, clay=29.42, sand=35.3)
HARRAN = SoilData(ph=7.3, nitrogen=1.66, organic_carbon=10.22,
                  bulk_density=1.48, cec=30.82, clay=48.02, sand=12.37)


# --- Tek tek hesaplar ------------------------------------------------------

def test_organik_madde_elde_hesapla_ayni():
    """Karacabey: 23.28 g/kg organik karbon.

      %C  = 23.28 / 10        = 2.328
      %OM = 2.328 x 1.724     = 4.0135
    """
    assert organik_madde(23.28) == pytest.approx(4.0135, abs=1e-4)


def test_azot_stogu_elde_hesapla_ayni():
    """Karacabey: 1.96 g/kg azot, 1.38 g/cm3 yogunluk, 30 cm.

      kutle = 1000 m2 x 0.30 m x 1.38 t/m3 x 1000 kg/t = 414 000 kg
      azot  = 414 000 x 1.96 / 1000                    = 811.44 kg/da
    """
    assert azot_stogu_kg_da(1.96, 1.38, 30.0) == pytest.approx(811.44, abs=0.01)


def test_azot_stogu_derinlikle_dogru_orantili():
    """DERINLIK KARISTIRMA TUZAGI.

    Ayni topragi 0-5 cm yerine 0-30 cm icin sormak stogu tam 6 katina cikarmali.
    Bu carpanin kaymasi, laboratuvar raporundaki sayiyla uydu verisinin
    kiyaslanmasini sessizce bozar; iki taraf da "kg/da" yazdigi icin fark
    gozle anlasilmaz.
    """
    bes = azot_stogu_kg_da(1.96, 1.38, 5.0)
    otuz = azot_stogu_kg_da(1.96, 1.38, 30.0)
    assert otuz / bes == pytest.approx(6.0, rel=1e-12)


def test_karbon_azot_birimsiz_oran():
    """Karacabey: 23.28 / 1.96 = 11.878."""
    assert karbon_azot(23.28, 1.96) == pytest.approx(11.878, abs=1e-3)


@pytest.mark.parametrize("cagri", [
    lambda: organik_madde(None),
    lambda: organik_madde(0.0),
    lambda: azot_stogu_kg_da(1.96, None),
    lambda: azot_stogu_kg_da(None, 1.38),
    lambda: karbon_azot(23.28, None),
    lambda: kilitli_elementler(None),
    lambda: laboratuvar_testleri(None),
])
def test_eksik_olcum_sessizce_varsayilana_dusmez(cagri):
    """Yigin yogunlugu yoksa 1.4 varsaymak, uydurulan sayiyi hesap gibi
    gosterirdi. fao56.KcYok ile ayni kural."""
    with pytest.raises(BesinVeriYok):
        cagri()


# --- pH'a bagli alinabilirlik ----------------------------------------------

def test_notr_toprakta_kilitli_element_yok():
    assert kilitli_elementler(6.5) == []
    assert kilitli_elementler(7.0) == []


def test_alkali_toprakta_dort_element_kilitleniyor():
    adlar = [k["element"] for k in kilitli_elementler(8.1)]
    assert adlar == ["Fosfor", "Demir", "Çinko", "Mangan"]


def test_asit_toprakta_baska_elementler_kilitleniyor():
    adlar = [k["element"] for k in kilitli_elementler(5.0)]
    assert "Fosfor" in adlar
    assert "Molibden" in adlar
    assert "Demir" not in adlar        # demir asit toprakta ALINABILIR


def test_fosfor_iki_ucta_da_kilitli_ama_sebebi_farkli():
    """FOSFORUN IKI AYRI MEKANIZMASI.

    Fosfor hem asit hem kirecli toprakta alinamaz, ama sebep ayni degil:
    asitte demir/aluminyum fosfati, kirecte kalsiyum fosfati olarak coker.
    Cozumleri de zit yonde (kireclemek / asitlendirmek). Tek bir "fosfor
    kilitli" mesaji verilseydi ciftci yanlis yone gidebilirdi.
    """
    asit = next(k for k in kilitli_elementler(5.0) if k["element"] == "Fosfor")
    alkali = next(k for k in kilitli_elementler(8.1) if k["element"] == "Fosfor")
    assert asit["sebep"] != alkali["sebep"]
    assert "alüminyum" in asit["sebep"]
    assert "kalsiyum" in alkali["sebep"]


def test_fosfor_testi_phe_gore_secilir():
    """Kirecli toprakta Bray-1 fosforu DUSUK gosterir; Olsen istenmeli."""
    alkali = next(t for t in laboratuvar_testleri(7.3) if t["element"] == "Fosfor")
    asit = next(t for t in laboratuvar_testleri(6.2) if t["element"] == "Fosfor")
    assert "Olsen" in alkali["test"]
    assert "Bray" in asit["test"]


def test_fosfor_testi_sinirinda_olsen_secilir():
    """Sinir pH 7.0'in KENDISI alkali tarafa sayilir; kirec bu noktada zaten
    var olabilir ve yanlis yonde hata yapmak fosforu yok gostermek olur."""
    sinir = next(t for t in laboratuvar_testleri(7.0) if t["element"] == "Fosfor")
    assert "Olsen" in sinir["test"]


# --- Karne butunu ----------------------------------------------------------

def _bolum(karne: dict, anahtar: str) -> dict | None:
    return next((b for b in karne["bolumler"] if b["anahtar"] == anahtar), None)


def test_karne_olculen_degerlerin_hepsini_tasiyor():
    karne = besin_karnesi(KARACABEY)
    assert set(karne["olculen"]) == {"ph", "nitrogen", "organic_carbon",
                                     "bulk_density", "cec", "clay", "sand"}
    assert karne["eksik"] == []


def test_karne_hesaplari_tek_tek_hesaplarla_ayni():
    karne = besin_karnesi(KARACABEY)
    assert _bolum(karne, "organik_madde")["deger"] == pytest.approx(4.01, abs=0.01)
    assert _bolum(karne, "azot_stok")["deger"] == pytest.approx(811.4, abs=0.1)
    assert _bolum(karne, "karbon_azot")["deger"] == pytest.approx(11.9, abs=0.05)


def test_eksik_tek_olcum_tum_karneyi_dusurmuyor():
    """Yigin yogunlugu olmayan ESKI onbellek kaydi. Azot stogu hesaplanamaz
    ama organik madde, C/N, pH ve KDK hesaplanabilir; karne bunlari SUNMALI
    ve eksigi ayrica soylemeli."""
    eski = KARACABEY.model_copy(update={"bulk_density": None})
    karne = besin_karnesi(eski)
    assert _bolum(karne, "azot_stok") is None
    assert [e["anahtar"] for e in karne["eksik"]] == ["azot_stok"]
    for anahtar in ("organik_madde", "karbon_azot", "kdk", "ph"):
        assert _bolum(karne, anahtar) is not None


def test_ph_yoksa_kilit_listesi_bos_ama_sessiz_degil():
    karne = besin_karnesi(KARACABEY.model_copy(update={"ph": None}))
    assert karne["kilitli"] == []
    assert karne["laboratuvar"] == []
    assert any(e["anahtar"] == "ph" for e in karne["eksik"])


def test_iki_gercek_toprak_farkli_organik_madde_sinifi_aliyor():
    """Karacabey 4.01 % (iyi/yuksek sinirinda), Harran 1.76 % (az).

    Harran: 10.22 / 10 x 1.724 = 1.7619
    Sinif siniri 2.0 oldugu icin "az" cikmali. Iki nokta ayni sinifa duserse
    siniflandirma ayirt etmiyor demektir.
    """
    k = _bolum(besin_karnesi(KARACABEY), "organik_madde")
    h = _bolum(besin_karnesi(HARRAN), "organik_madde")
    assert h["deger"] == pytest.approx(1.76, abs=0.01)
    assert h["sinif"] == "az"
    assert k["sinif"] != h["sinif"]


def test_karne_azot_stogunu_alinabilir_azot_diye_sunmuyor():
    """EN KOLAY YANLIS ANLASILAN SAYI.

    811 kg/da toplam azot, "gubre atmama gerek yok" gibi okunabilir. Aciklama
    bunun organik bagli oldugunu ve hesaplanamadigini SOYLEMEK zorunda; aksi
    halde karne ciftciyi azotsuz birakir.
    """
    aciklama = _bolum(besin_karnesi(KARACABEY), "azot_stok")["aciklama"]
    assert "organik" in aciklama
    assert "hesaplanamaz" in aciklama


# --- Urune ozel bolum ------------------------------------------------------

BUGDAY = {"ad": "Buğday", "verimlilik": "high",
          "ph": {"min": 5.5, "opt_min": 6, "opt_max": 7, "max": 8.5}}


def test_urun_optimum_ustunde_uyariyor():
    """Karacabey pH 7.07, bugdayin optimumu 6-7. Ustunde ama yasayabildigi
    araligin (5.5-8.5) icinde: 'olmaz' degil 'en verimli degil' denmeli."""
    karne = besin_karnesi(KARACABEY, BUGDAY)
    notlar = " ".join(karne["urun"]["notlar"])
    assert "üstünde" in notlar
    assert "dışında" not in notlar


def test_urun_yasayamadigi_phte_farkli_konusuyor():
    karne = besin_karnesi(KARACABEY.model_copy(update={"ph": 9.0}), BUGDAY)
    assert "dışında" in " ".join(karne["urun"]["notlar"])


def test_verimlilik_ihtiyaci_yuksek_urun_fakir_toprakta_uyariyor():
    """Harran organik maddesi az, bugdayin verimlilik ihtiyaci yuksek."""
    karne = besin_karnesi(HARRAN, BUGDAY)
    assert any("verimlili" in n for n in karne["urun"]["notlar"])


def test_urun_verilmezse_urun_bolumu_hic_uretilmez():
    assert "urun" not in besin_karnesi(KARACABEY)
