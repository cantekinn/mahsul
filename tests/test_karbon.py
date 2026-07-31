"""IPCC 2019 Tier 1 karbon envanteri testleri.

Beklenen sayilar ELDE HESAPLANDI, koddan okunmadi. Ornek: 1 dekara 20 kg saf
azot icin dogrudan N2O

    20 kg N x EF1(0.010) x (44/28) x GWP100(273) = 85.8 kg CO2e

Zincirdeki her carpanin kaynagi karbon.py'de yaziyor. Bir katsayi guncellenirse
(ornegin AR6 yerine AR7 GWP'si) bu testler kirmizi yanar; istenen budur, cunku
katsayi degisimi sonucun anlamini degistirir ve fark edilmeden gecmemelidir.
"""
from __future__ import annotations

import pytest

from knowledge.karbon import (
    SULAMA_VERIMI,
    SulamaYontemiYok,
    ayak_izi,
    azaltim_onerileri,
    pompa_enerjisi_kwh,
)


def test_azot_zinciri_elde_hesapla_ayni():
    """1 dekar, 20 kg N, 8 L dizel, sulama yok.

    dogrudan = 20 x 0.010 x 44/28 x 273           = 85.8
    volatil  = 20 x 0.11 x 0.010 x 44/28 x 273    =  9.4
    yikanma  = 20 x 0.24 x 0.011 x 44/28 x 273    = 22.7
    uretim   = 20 x 5.5                           = 110.0
    dizel    =  8 x 2.65                          = 21.2
    """
    s = ayak_izi(1000.0, azot_kg_da=20.0, dizel_l_da=8.0)
    kalem = {k["ad"]: k["kg_co2e"] for k in s["kalemler"]}

    assert kalem["Gübreden doğrudan N2O"] == pytest.approx(85.8, abs=0.1)
    assert kalem["Gübreden dolaylı N2O"] == pytest.approx(32.1, abs=0.1)
    assert kalem["Gübre üretimi"] == pytest.approx(110.0, abs=0.1)
    assert kalem["Dizel yakıt"] == pytest.approx(21.2, abs=0.1)
    assert kalem["Sulama pompası elektriği"] == 0.0
    assert s["toplam_kg_co2e"] == pytest.approx(249.1, abs=0.2)


def test_dekar_basina_alandan_bagimsiz():
    """Ayni yogunlukta 1 dekar ile 10 dekar, dekar basina AYNI sonucu vermeli.

    Ciftci kendi tarlasini baskasininkiyle ancak dekar basina karsilastirir;
    alanla olceklenen bir hata bu karsilastirmayi sessizce bozardi.
    """
    kucuk = ayak_izi(1000.0, azot_kg_da=20.0, dizel_l_da=8.0)
    buyuk = ayak_izi(10000.0, azot_kg_da=20.0, dizel_l_da=8.0)
    assert buyuk["dekar_basina_kg_co2e"] == pytest.approx(
        kucuk["dekar_basina_kg_co2e"], rel=0.001
    )
    assert buyuk["toplam_kg_co2e"] == pytest.approx(
        kucuk["toplam_kg_co2e"] * 10, rel=0.001
    )


def test_pompa_hidroligi_elde_hesapla_ayni():
    """100 m3 net su, damla (verim 0.90), kuyu (50 m basma).

    brut = 100 / 0.90                       = 111.111 m3
    is   = 1000 x 9.81 x 50 x 111.111       = 5.450e7 J
    kWh  = 5.450e7 / (3.6e6 x 0.60)         = 25.23
    """
    assert pompa_enerjisi_kwh(100.0, "damla", 50.0) == pytest.approx(25.23, abs=0.02)


def test_salma_sulama_damlanin_tam_1_5_kati_enerji_ister():
    """Enerji brut hacimle dogru orantili; brut hacim verimle ters orantili.

    0.90 / 0.60 = 1.5. Bu oran basma yuksekliginden ve su miktarindan
    BAGIMSIZ olmali; degilse verim carpani yanlis yere uygulanmis demektir.
    """
    for su, basma in ((100.0, 50.0), (37.5, 20.0)):
        damla = pompa_enerjisi_kwh(su, "damla", basma)
        salma = pompa_enerjisi_kwh(su, "salma", basma)
        assert salma / damla == pytest.approx(
            SULAMA_VERIMI["damla"] / SULAMA_VERIMI["salma"], rel=1e-9
        )


def test_tanimsiz_sulama_yontemi_hata_verir():
    with pytest.raises(SulamaYontemiYok):
        pompa_enerjisi_kwh(100.0, "sisleme", 50.0)


def test_gosterge_bayragi_sadece_eksik_girdide_yanar():
    """Varsayilan kullanildiysa sonuc "gosterge" isaretlenmeli.

    Bu bayrak, uydurulmus bir sayinin olculmus gibi sunulmasini engelleyen tek
    mekanizma. Ikisinden BIRI eksikse bile yanmali.
    """
    assert ayak_izi(1000.0)["gosterge"] is True
    assert ayak_izi(1000.0, azot_kg_da=20.0)["gosterge"] is True
    assert ayak_izi(1000.0, dizel_l_da=8.0)["gosterge"] is True
    assert ayak_izi(1000.0, azot_kg_da=20.0, dizel_l_da=8.0)["gosterge"] is False


def test_sifir_veya_negatif_alan_reddedilir():
    with pytest.raises(ValueError):
        ayak_izi(0.0)
    with pytest.raises(ValueError):
        ayak_izi(-100.0)


def test_kapsam_disi_kalemler_sessizce_sifir_sayilmaz():
    """Hesaplanmayan kalemler yanitta ISIMLE duruyor mu.

    Toprak karbon stogu gibi bir kalemi listeden cikarmak, envanteri oldugundan
    tam gostermek olurdu.
    """
    s = ayak_izi(1000.0)
    assert len(s["kapsam_disi"]) >= 4
    assert any("organik karbon" in k for k in s["kapsam_disi"])


def test_azaltim_onerisi_en_buyuk_kazancla_basliyor():
    """Oneriler genel tavsiye degil, kalem buyuklugune gore siralanmis olmali."""
    s = ayak_izi(5000.0, azot_kg_da=25.0, dizel_l_da=10.0,
                 sulama_m3=800.0, sulama_yontemi="salma")
    oneriler = azaltim_onerileri(s)
    kazanclar = [o["kazanc_kg_co2e"] for o in oneriler]
    assert kazanclar == sorted(kazanclar, reverse=True)
    assert all(o["kazanc_kg_co2e"] > 0 for o in oneriler)


def test_damla_sulamada_damlaya_gecis_onerisi_cikmaz():
    """Zaten damla sulama yapana "damlaya gec" demek gurultudur."""
    s = ayak_izi(5000.0, azot_kg_da=25.0, dizel_l_da=10.0,
                 sulama_m3=800.0, sulama_yontemi="damla")
    assert not any(o["baslik"] == "Damla sulamaya geçiş" for o in azaltim_onerileri(s))
