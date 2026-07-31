"""Sezon gunlugu hesabinin testleri.

Girdiler UYDURMA DEGIL: asagidaki ET0 ve yagis dizisi Open-Meteo'dan
40.22 / 28.85 (Bursa Karacabey) icin 2026-07-21..31 arasi cekilen gercek
gunluk degerlerdir. Beklenen sayilar da elle carpilip yazildi; fonksiyonun
kendi ciktisi beklenen deger olarak kopyalanmadi (o, testi hesaba degil
mevcut davranisa baglardi).
"""
from __future__ import annotations

from datetime import date

import pytest

from knowledge import fao56, gunluk

# Olculen seri (Bursa Karacabey, 2026-07-21..31).
TARIH = ["2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24", "2026-07-25",
         "2026-07-26", "2026-07-27", "2026-07-28", "2026-07-29", "2026-07-30",
         "2026-07-31"]
ET0 = [5.91, 6.12, 5.31, 5.31, 2.70, 5.04, 5.70, 6.18, 7.79, 8.03, 7.35]
YAGIS = [0.0, 0.0, 1.1, 0.0, 3.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
BUGUN = date(2026, 7, 31)


def test_acik_elde_hesapla_ayni():
    """25 Temmuz'da sulanmis domates: 26-31 Temmuz arasi 6 gun hesaba girer.

    ET0 toplami   = 5.04+5.70+6.18+7.79+8.03+7.35 = 40.09
    Kc(domates,mid) = 1.15  ->  ETc = 46.1035
    O gunlerde yagis 0 -> etkili yagis 0
    acik = 46.1 mm, litre/dekar = 46 100
    """
    s = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                             "domates", "mid", BUGUN)
    assert s["gecen_gun"] == 6
    assert s["kc"] == 1.15
    assert s["etc_mm"] == pytest.approx(46.1, abs=0.05)
    assert s["yagis_mm"] == 0.0
    assert s["acik_mm"] == pytest.approx(46.1, abs=0.05)
    assert s["litre_dekar"] == pytest.approx(46100, abs=50)


def test_sulama_gunu_hesaba_girmez():
    """SULAMA GUNU TUZAGI. 25 Temmuz'da sulandiysa o gunun ET0'i (2.70)
    ve yagisi (3.6) sayilmamali; toprak o gun zaten islanmistir.
    Ayni tarihi 24 Temmuz'a alirsak 25'i de girer ve gun sayisi 7 olur.
    """
    alti = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                                "domates", "mid", BUGUN)
    yedi = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 24),
                                "domates", "mid", BUGUN)
    assert alti["gecen_gun"] == 6 and yedi["gecen_gun"] == 7
    # Aradaki tek fark 25 Temmuz gunudur: ETc 2.70x1.15 = 3.105 artar.
    assert yedi["etc_mm"] - alti["etc_mm"] == pytest.approx(3.1, abs=0.05)
    # Ayni gunun yagisi da eklenir: ham 3.6, etkili 0.80x3.6 = 2.88.
    assert yedi["yagis_mm"] - alti["yagis_mm"] == pytest.approx(3.6, abs=0.05)
    assert yedi["etkili_yagis_mm"] - alti["etkili_yagis_mm"] == pytest.approx(2.88, abs=0.05)


def test_yagis_acigi_dusuruyor_ama_tamami_degil():
    """23 Temmuz'da sulanmis: 24-31 arasi 8 gun, icinde 3.6 mm yagis var.

    Yagisin TAMAMI degil %80'i dusulur (fao56.effective_rainfall_daily);
    yuzey akisi ve derin sizma bitkiye ulasmaz. Yagisin tamamini dusmek
    acigi olduğundan kucuk gosterir, yani eksik sulama onerisi uretir.
    """
    s = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 23),
                             "domates", "mid", BUGUN)
    assert s["yagis_mm"] == pytest.approx(3.6, abs=0.05)
    assert s["etkili_yagis_mm"] == pytest.approx(2.88, abs=0.05)
    # Etkili yagis ham yagistan KUCUK olmali; esit cikarsa katsayi kaybolmustur.
    assert s["etkili_yagis_mm"] < s["yagis_mm"]
    assert s["acik_mm"] == pytest.approx(s["etc_mm"] - s["etkili_yagis_mm"], abs=0.05)


def test_kc_urune_gore_degisiyor():
    """AYNI HAVA, FARKLI URUN, FARKLI ACIK. Kc sabit bir dolgu degil.

    domates mid Kc=1.15, bugday mid Kc=1.15 olabilir; ayrisan bir cift secilir:
    ETc orani tam Kc oranina esit olmali, cunku ET0 dizisi aynidir.
    """
    d = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                             "domates", "mid", BUGUN)
    z = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                             "zeytin", "mid", BUGUN)
    oran_kc = fao56.crop_coefficient("zeytin", "mid") / fao56.crop_coefficient("domates", "mid")
    assert z["etc_mm"] / d["etc_mm"] == pytest.approx(oran_kc, abs=0.01)


def test_kapsam_disi_urun_sessizce_varsayilan_kc_almiyor():
    with pytest.raises(fao56.KcYok):
        gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                             "boyle_bir_urun_yok", "mid", BUGUN)


def test_bugun_sulandiysa_sifir_acik_dondurmuyor():
    """EN KOLAY YANLIS: bugun sulayan ciftciye "0 mm acik" demek, hesabin
    yapildigini ve sonucun sifir CIKTIGINI ima eder. Oysa hesap hic
    yapilamadi (hesaba girecek gun yok). Ikisi ayri seydir.
    """
    with pytest.raises(gunluk.GunlukVeriYok):
        gunluk.birikmis_acik(TARIH, ET0, YAGIS, BUGUN, "domates", "mid", BUGUN)


def test_pencere_disinda_kalan_sulama_sifir_acik_dondurmuyor():
    """Sulama, olculen 11 gunluk pencerenin oncesinde (1 Temmuz). Pencerede
    o tarihten sonraki gunler var ama pencere sulamayi kapsamiyor; yine de
    11 gunun tamami hesaba girer ve bu DOGRUDUR (hepsi sulamadan sonradir).
    Sessiz sifir DONMEMELI.
    """
    s = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 1),
                             "domates", "mid", BUGUN)
    assert s["gecen_gun"] == 11


def test_gelecek_tarihli_sulama_reddediliyor():
    with pytest.raises(gunluk.GunlukVeriYok):
        gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 8, 10),
                             "domates", "mid", BUGUN)


def test_acik_yorumu_gun_karsiligini_bolerek_buluyor():
    s = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                             "domates", "mid", BUGUN)
    # 46.1 mm / 7.1 mm gunluk = 6.5 gun
    y = gunluk.acik_yorumu(s, 7.1)
    assert "6.5 günlük" in y
    assert "6 günde" in y


def test_acik_yorumu_sifir_etc_ile_bolme_yapmiyor():
    s = gunluk.birikmis_acik(TARIH, ET0, YAGIS, date(2026, 7, 25),
                             "domates", "mid", BUGUN)
    with pytest.raises(gunluk.GunlukVeriYok):
        gunluk.acik_yorumu(s, 0.0)


# ---------------------------------------------------------------------------
# Tekrar teshis
# ---------------------------------------------------------------------------

KAYITLAR = [
    {"tarih": "2026-07-05", "tur": "teshis", "etiket": "domates_erken_yaniklik"},
    {"tarih": "2026-07-08", "tur": "ilac", "etiket": "mancozeb"},
    {"tarih": "2026-07-12", "tur": "sulama"},
    {"tarih": "2026-07-20", "tur": "teshis", "etiket": "domates_kulleme"},
]


def test_ilk_kez_gorulen_hastalikta_tekrar_yok():
    assert gunluk.tekrar_teshis(KAYITLAR, "domates_gec_yaniklik", BUGUN) is None


def test_tekrar_eden_hastalik_ve_aradaki_ilaclama_sayiliyor():
    t = gunluk.tekrar_teshis(KAYITLAR, "domates_erken_yaniklik", BUGUN)
    assert t is not None
    assert t["onceki_tarih"] == "2026-07-05"
    assert t["gecen_gun"] == 26          # 5 Temmuz -> 31 Temmuz
    assert t["ilac_sayisi"] == 1
    assert t["ilac_son"] == "2026-07-08"


def test_ilaclama_yoksa_sayi_sifir_ilac_son_none():
    t = gunluk.tekrar_teshis(KAYITLAR, "domates_kulleme", BUGUN)
    assert t is not None and t["ilac_sayisi"] == 0 and t["ilac_son"] is None


def test_en_son_teshis_esas_aliniyor():
    """Ayni hastalik iki kez kayitliysa 'gecen gun' EN YAKIN olana gore
    olculur; en eskiye gore olcmek araliği oldugundan buyuk gosterirdi.
    """
    kayitlar = KAYITLAR + [
        {"tarih": "2026-07-25", "tur": "teshis", "etiket": "domates_erken_yaniklik"},
    ]
    t = gunluk.tekrar_teshis(kayitlar, "domates_erken_yaniklik", BUGUN)
    assert t["onceki_tarih"] == "2026-07-25" and t["gecen_gun"] == 6


def test_bugunku_teshis_kendisini_tekrar_saymiyor():
    """Teshis kaydi ONCE gunluge yazilip SONRA tekrar sorgusu yapilirsa,
    fonksiyon kendi kaydini 'onceki teshis' sanmamali (0 gun once tekrar
    etti gibi anlamsiz bir sonuc cikardi).
    """
    kayitlar = KAYITLAR + [
        {"tarih": BUGUN.isoformat(), "tur": "teshis", "etiket": "domates_kulleme"},
    ]
    t = gunluk.tekrar_teshis(kayitlar, "domates_kulleme", BUGUN)
    assert t["onceki_tarih"] == "2026-07-20"
