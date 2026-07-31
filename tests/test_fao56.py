"""FAO-56 sulama fizigi testleri.

NEDEN BU TESTLER YAZILABILIYOR: fao56.py makine ogrenmesi degil, yayinlanmis
denklemler. Allen et al. (1998) kitabi her denklem icin SAYISAL ORNEK veriyor.
Yani beklenen degeri biz uydurmuyoruz, kitaptan aliyoruz. Testin degeri de
buradan geliyor: kodun ciktisini kendi ciktisiyla karsilastiran bir test
(karakterizasyon testi) yanlis formulu de "gecer" yazar.

Her testin ust satirinda hangi ornek/tablodan alindigi yaziyor.
"""
from __future__ import annotations

import pytest

from knowledge.fao56 import (
    KC_TABLE,
    KcYok,
    atmospheric_pressure,
    crop_coefficient,
    effective_rainfall,
    extraterrestrial_radiation,
    net_irrigation,
    net_radiation,
    penman_monteith_et0,
    psychrometric_constant,
    saturation_vapor_pressure,
    slope_svp,
)


# --- Tek tek denklemler: FAO-56'nin kendi ornekleri ------------------------

def test_atmosfer_basinci_ornek2():
    """FAO-56 Ornek 2: 1800 m rakimda P = 81.8 kPa."""
    assert atmospheric_pressure(1800) == pytest.approx(81.8, abs=0.05)


def test_psikrometrik_sabit_ornek2():
    """FAO-56 Ornek 2: ayni rakimda gamma = 0.054 kPa/C."""
    assert psychrometric_constant(1800) == pytest.approx(0.054, abs=0.0005)


def test_doygun_buhar_basinci_ornek3():
    """FAO-56 Ornek 3: e(24.5 C) = 3.075 kPa, e(15 C) = 1.705 kPa."""
    assert saturation_vapor_pressure(24.5) == pytest.approx(3.075, abs=0.001)
    assert saturation_vapor_pressure(15.0) == pytest.approx(1.705, abs=0.001)


def test_egim_delta_annex2_tablo24():
    """FAO-56 Annex 2 Tablo 2.4: Delta(20 C)=0.145, Delta(30 C)=0.243 kPa/C."""
    assert slope_svp(20.0) == pytest.approx(0.145, abs=0.001)
    assert slope_svp(30.0) == pytest.approx(0.243, abs=0.001)


def test_atmosfer_disi_radyasyon_ornek8():
    """FAO-56 Ornek 8: 3 Eylul (J=246), 20 derece GUNEY -> Ra = 32.2 MJ/m2/gun.

    Guney yarikure BILEREK secildi: enlem isaretini yanlis kullanan bir hata
    kuzey ornekte gizlenebilir, burada gizlenemez.
    """
    assert extraterrestrial_radiation(-20.0, 246) == pytest.approx(32.2, abs=0.1)


def test_net_radyasyon_ornek11_12():
    """FAO-56 Ornek 11+12: Rio de Janeiro, Mayis.

    Tmax=25.1 Tmin=19.1 ea=2.1 kPa Rs=14.5 Ra=25.1 MJ/m2/gun (deniz seviyesi)
    -> Rnl = 3.5 ve Rn = 7.6 MJ/m2/gun.
    """
    rn = net_radiation(rs=14.5, ra=25.1, t_min=19.1, t_max=25.1, ea=2.1, elevation_m=0)
    assert rn == pytest.approx(7.6, abs=0.05)


def test_et0_ornek17_uccle():
    """FAO-56 Ornek 17: Uccle (Brüksel), 6 Temmuz -> ET0 = 3.9 mm/gun.

    OLCULEN SAPMA VE SEBEBI: bu fonksiyon ea'yi ORTALAMA bagil nemden
    hesapliyor (ea = es * RHmean/100), kitap ise RHmax/RHmin ikilisinden
    (ea = 1.409 kPa). RHmean ile ea = 1.468 kPa cikiyor; ea buyudukce buhar
    basinci acigi (es-ea) kuculuyor ve ET0 DUSUYOR. Yani sapmanin yonu
    onceden bilinebilir, rastgele degil: 3.79 < 3.9.

    Tolerans 0.15 mm/gun (%3.9) bu bilinen yaklasimin payidir. Daraltmak icin
    Open-Meteo'dan RHmax/RHmin cekmek gerekir; sulama karti gunluk ortalama
    nemle calistigi icin bu bilincli bir kabul.
    """
    et0 = penman_monteith_et0(
        t_min=12.3, t_max=21.5, rh_mean=73.5, wind_2m=2.078,
        rs=22.07, latitude_deg=50.80, elevation_m=100, day_of_year=187,
    )
    assert et0 == pytest.approx(3.9, abs=0.15)
    assert et0 < 3.9, "RHmean yaklasimi ET0'i DUSURMELI, artirmamali"


# --- Etkili yagis: USDA-SCS parcali fonksiyonu ----------------------------

def test_etkili_yagis_250mm_esiginde_sureklidir():
    """Parcali fonksiyonun kirilma noktasinda siçrama olmamali.

    p<=250 kolu: 250*(125-50)/125 = 150. p>250 kolu: 125+0.1*250 = 150.
    Iki kol ayni sayiyi vermezse tarla, yagis 250 mm'yi gectigi anda aniden
    farkli bir sulama plani alirdi.
    """
    assert effective_rainfall(250.0) == pytest.approx(150.0)
    assert effective_rainfall(250.001) == pytest.approx(150.0, abs=0.001)


def test_etkili_yagis_yagistan_buyuk_olamaz():
    for p in (0.0, 10.0, 50.0, 120.0, 250.0, 400.0):
        assert effective_rainfall(p) <= p


def test_negatif_yagis_sifira_kirpilir():
    assert effective_rainfall(-5.0) == 0.0


# --- Kc tablosu: sessiz varsayilan TUZAGININ testi ------------------------

def test_tanimsiz_urun_sessizce_1_donmez():
    """fao56.py'deki en onemli davranis.

    Eskiden tanimsiz urunde Kc = 1.0 (referans cim) donuyordu. 1.0 gecerli bir
    Kc oldugu icin hata hicbir yerde gorunmuyordu ve kullanici yanlis su
    miktarini dogru sanip uyguluyordu. Bu test o davranisin geri gelmesini
    engeller.
    """
    with pytest.raises(KcYok):
        crop_coefficient("kekik")


def test_kc_asamalari_tutarli():
    """Her kayitta uc asama da olmali ve Kc fiziksel araliktan cikmamali.

    Kc, referans cime gore orandir; 0 ile 1.5 arasi disina cikan bir deger
    tabloya yanlis yazilmistir (FAO-56 Tablo 12'nin en yukseki 1.25).
    """
    for urun, kc in KC_TABLE.items():
        assert set(kc) == {"ini", "mid", "end"}, urun
        for asama, deger in kc.items():
            assert 0.0 < deger <= 1.30, f"{urun}.{asama} = {deger}"


def test_net_sulama_negatife_dusmez():
    """Yagis bitki ihtiyacindan cok oldugunda sulama 0'dir, eksi degil.

    Eksi bir deger "tarladan su cikarin" demek olurdu; anlamsiz.
    """
    # domates mid Kc=1.15, ET0=4 -> ETc=4.6 mm/gun. 20 mm/gun yagisin
    # %80'i (16 mm) etkili; 4.6 - 16 < 0.
    assert net_irrigation(4.0, "domates", "mid", rainfall_mm_daily=20.0) == 0.0
