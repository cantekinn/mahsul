"""Derece-gun (GDD) zararli fenolojisi testleri.

GDD formulunde iki tane sessiz hata yapma yeri var ve ikisi de sonucu YANLIS
AMA MAKUL bir sayiya goturur, yani gozle fark edilmez:
  1. Ust kesme (tupper) uygulanmazsa sicak gunler nesil sayisini sisirir.
  2. Taban sicaklikin altindaki gunler eksiye dususe izin verilirse birikim
     geriye gider ve zararli takvimi geri kayar.
Testler dogrudan bu ikisini hedefliyor.
"""
from __future__ import annotations

import pytest

from knowledge.degree_day import PEST_TABLE, accumulate_gdd, gdd_day, pest_status, pests_for_crop


def test_ust_kesme_sicak_gunu_sinirlar():
    """Tuta absoluta: tbase=8.1, tupper=34.6. Tmin=10, Tmax=40 olan bir gun.

    Kesmesiz : (40.0 + 10)/2 - 8.1 = 16.9   (yanlis, bocek 40 C'de hizlanmaz)
    Kesmeli  : (34.6 + 10)/2 - 8.1 = 14.2   (dogru)
    """
    assert gdd_day(10.0, 40.0, tbase=8.1, tupper=34.6) == pytest.approx(14.2)
    assert gdd_day(10.0, 40.0, tbase=8.1) == pytest.approx(16.9)


def test_soguk_gun_negatif_birikim_uretmez():
    """Tbase altindaki gun 0 katkı verir; birikimi geri almaz."""
    assert gdd_day(-5.0, 5.0, tbase=10.0) == 0.0
    assert accumulate_gdd([-5.0, -5.0], [5.0, 5.0], tbase=10.0) == 0.0


def test_birikim_gunlerin_toplamina_esit():
    tmins = [10.0, 12.0, 14.0]
    tmaxs = [22.0, 26.0, 30.0]
    beklenen = sum(gdd_day(a, b, 10.0, 33.0) for a, b in zip(tmins, tmaxs))
    assert accumulate_gdd(tmins, tmaxs, 10.0, 33.0) == pytest.approx(beklenen)


def test_nesil_siniri_dogru_tarafta():
    """Tam nesil esiginde YENI nesil baslar, oncekinin sonunda kalmaz.

    Tuta icin nesil_gdd = 453.
      452.9 -> 1. nesil, son evrenin (Yetiskin, 453) 0.1 oncesi
      453.0 -> 2. nesil, bastan basliyor
    Bu bir eksi-bir hatasinin en klasik yeri; kaymasi ilaclama penceresini bir
    nesil oteler.
    """
    onceki = pest_status(452.9, "tuta_absoluta")
    assert onceki["nesil"] == 1
    assert onceki["sonraki_evre"] == ("Yetişkin", 0.1)

    sonraki = pest_status(453.0, "tuta_absoluta")
    assert sonraki["nesil"] == 2
    assert sonraki["evre"] == "Yumurta"
    assert sonraki["sonraki_evre"] == ("Yumurta açılımı", 60.0)


def test_sifir_birikimde_ilk_nesil_yumurta():
    d = pest_status(0.0, "leptinotarsa")
    assert d["nesil"] == 1
    assert d["evre"] == "Yumurta"


def test_konak_listesi_iki_yonlu_tutarli():
    """pests_for_crop(u) dondurdugu her bocegin konagi gercekten u olmali.

    Iki taraf elle yazilsaydi biri guncellenip digeri unutulurdu; bu test o
    ayrismayi yakalar.
    """
    for urun in {k for p in PEST_TABLE.values() for k in p["konak"]}:
        for anahtar in pests_for_crop(urun):
            assert urun in PEST_TABLE[anahtar]["konak"]


def test_evre_esikleri_artan_ve_nesil_icinde():
    """Evre esikleri siralı olmali ve nesil suresini asmamali.

    Sirasiz bir tablo, pest_status'un dongusunu sessizce yanlis evrede
    durdurur; nesli asan bir esige ise hicbir zaman ulasilmaz.
    """
    for anahtar, p in PEST_TABLE.items():
        esikler = list(p["evreler"].values())
        assert esikler == sorted(esikler), anahtar
        assert esikler[-1] <= p["nesil_gdd"], anahtar
        assert p["tbase"] < p["tupper"], anahtar
