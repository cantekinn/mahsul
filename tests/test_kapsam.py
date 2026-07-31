"""Kapsam kumeleri ve bilgi tabani tutarliligi.

Buradaki testler tek bir soruyu sinar: "bir urun bir karta gorunuyorsa o kart
gercekten hesap yapabiliyor mu". Kapsam kumeleri tablolardan turetildigi icin
bir tabloya yazim hatasiyla eklenen urun sessizce OLU kalir: listede gorunmez
ama neden gorunmedigi de sorulmaz.
"""
from __future__ import annotations

import pytest

from knowledge.fao56 import KC_TABLE, crop_coefficient
from knowledge.kapsam import (
    YETENEK_GEREKCE,
    YETENEKLER,
    destekli,
    iklim_bilgi_tabani,
    iklim_urunleri,
    kapsam,
    sulama_urunleri,
    zararli_urunleri,
)


def test_uc_yetenegin_de_gerekcesi_var():
    """Kart cevap veremediginde SEBEP gostermek zorunda.

    Gerekcesi olmayan bir yetenek eklenirse arayuz bos bir kutu cizer ve
    kullanici urunun desteklenmedigini degil uygulamanin bozuldugunu sanar.
    """
    assert set(YETENEKLER) == set(YETENEK_GEREKCE)
    for gerekce in YETENEK_GEREKCE.values():
        assert len(gerekce) > 40


def test_kapsam_kumeleri_bos_degil_ve_beklenen_buyuklukte():
    """Olculmus buyuklukler: iklim > sulama > zararli.

    Uc sinir farkli oldugu icin kumeler de farkli buyuklukte olmali. Ucu
    esitlenirse birisi digerinin listesine baglanmis demektir; bu tam olarak
    kapsam.py'nin duzeltmek icin yazildigi hataydi.
    """
    assert len(zararli_urunleri()) < len(sulama_urunleri()) < len(iklim_urunleri())
    assert len(sulama_urunleri()) == len(KC_TABLE)


@pytest.mark.parametrize("urun", sorted(KC_TABLE))
def test_sulama_kapsamindaki_her_urun_gercekten_hesaplanabiliyor(urun):
    """Kumede olmak yetmez; crop_coefficient cagrisi hata vermemeli."""
    assert destekli("sulama", urun)
    assert crop_coefficient(urun, "mid") > 0


@pytest.mark.parametrize("urun", sorted(KC_TABLE))
def test_kc_tablosundaki_urun_bilgi_tabaninda_da_var(urun):
    """YAZIM HATASI YAKALAYICI.

    Kc tablosuna 'aycicegi' yerine 'aycicek' yazilsa sulama kartinda hicbir
    zaman secilemeyen olu bir kayit olusurdu ve hicbir hata mesaji cikmazdi.
    Urun adlari bilgi tabaniyla ayni yazilmak zorunda.
    """
    assert urun in iklim_bilgi_tabani(), f"'{urun}' Kc tablosunda var, bilgi tabaninda yok"


@pytest.mark.parametrize("urun", sorted(zararli_urunleri()))
def test_zararli_konaklari_bilgi_tabaninda(urun):
    assert urun in iklim_bilgi_tabani(), f"zararli konagi '{urun}' bilgi tabaninda yok"


def test_desteklenmeyen_urun_yanlislikla_destekli_gorunmuyor():
    """Kekik FAO-56 Tablo 12'de yok; sulama kapsaminda gorunmemeli.

    Bu urun bilgi tabaninda VAR (oneri motoru cevaplayabiliyor) ama sulama
    hesabi yapilamiyor. Iki kumenin ayri olmasinin somut ornegi.
    """
    assert not destekli("sulama", "kekik")
    assert destekli("iklim", "kekik")


def test_bilinmeyen_yetenek_sessizce_bos_kume_donmez():
    with pytest.raises(KeyError):
        kapsam("gubre")
