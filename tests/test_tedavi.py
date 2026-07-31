"""Model etiketi -> tedavi kaydi eslesmesi testleri.

Bu eslestirici bir SOZLUK DEGIL, alt dize aramasi yapiyor: model etiketinin
ASCII varyanti icinde treatments.yaml anahtarlarindan hangisi geciyorsa o kayit
seciliyor, esitlikte en uzun anahtar kazaniyor. Guclu tarafi yeni bir sinif
eklendiginde kendiliginden eslesmesi; zayif tarafi ise YANLIS eslesmenin
sessiz olmasi. Kullanici hatali bir ilac tavsiyesi ile karsilasir ve bunu
anlamasinin yolu yoktur.

Bu yuzden buradaki iki test tek tek ornek degil, TUM etiket kumesi uzerinde
degismez kural sinar.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from models.disease.tedavi import tedavi_bul

KOK = Path(__file__).resolve().parent.parent
ETIKETLER = (KOK / "models" / "disease" / "labels.txt").read_text(
    encoding="utf-8"
).split()

HASTALIK_ETIKETLERI = [e for e in ETIKETLER if not e.endswith("_saglikli")]


def test_etiket_dosyasi_beklenen_boyutta():
    """45 sinif: model, cam_agirlik.npy ve bu dosya ayni sayida olmali."""
    assert len(ETIKETLER) == 45


@pytest.mark.parametrize("etiket", HASTALIK_ETIKETLERI)
def test_her_hastalik_etiketinin_tedavisi_var(etiket):
    """Bosluk birakilmis sinif olmamali.

    labels.txt'ye yeni bir hastalik eklenip treatments.yaml unutulursa
    kullanici teshisi gorur ama "ne yapayim" sorusunun cevabini goremez. O
    durumda teshis tek basina ise yaramaz.
    """
    assert tedavi_bul(etiket) is not None


@pytest.mark.parametrize("etiket", HASTALIK_ETIKETLERI)
def test_tedavi_kaydinin_konagi_etiketin_urunuyle_ayni(etiket):
    """EN ONEMLI TEST: eslesme dogru URUNE mi dustu.

    Alt dize aramasi kolayca baska urunun hastaligina kayabilir (ornegin
    'halkali leke' anahtari hem elma hem zeytin kayitlarinda gecer). Etiketin
    urun oneki, secilen kaydin konak listesinde YOKSA eslesme yanlistir.
    Tedavi metni okununca dogru gorunecegi icin bunu gozle yakalamak mumkun
    degil; test sart.
    """
    urun = etiket.split("_")[0]
    kayit = tedavi_bul(etiket)
    assert urun in kayit["konak"], f"{etiket} -> {kayit['ad']} (konak {kayit['konak']})"


def test_saglikli_etiket_tedavi_dondurmez():
    """Saglikli yaprakta ilac onerisi, gereksiz ilaclama demektir."""
    for etiket in ETIKETLER:
        if etiket.endswith("_saglikli"):
            assert tedavi_bul(etiket) is None


def test_hedef_disi_tedavi_dondurmez():
    assert tedavi_bul("diger") is None


def test_bilinmeyen_etiket_sessizce_bir_kayda_dusmez():
    assert tedavi_bul("mars_toprak_hastaligi") is None


def test_en_uzun_anahtar_kazanir():
    """Erken ve gec yaniklik ayri kayitlara dusmeli.

    Ikisi de '... yaniklik' ile bitiyor; kural en uzun anahtari secmeseydi
    ikisi de ayni kayda dusebilir ve Alternaria'ya karsi Phytophthora ilaci
    onerilebilirdi. Mucadelesi tamamen farkli iki hastalik.
    """
    erken = tedavi_bul("domates_erken_yaniklik")
    gec = tedavi_bul("domates_gec_yaniklik")
    assert erken["ad"] != gec["ad"]
    assert "Alternaria" in erken["ad"]
    assert "Phytophthora" in gec["ad"]


def test_tedavi_kaydinin_dort_blogu_da_dolu():
    """Arayuz belirti/dogal/kimyasal/korunma diye dort blok ciziyor.

    Biri bos gelirse ekranda basligi olan bos bir kutu kalir; kullanici
    bilginin olmadigini degil uygulamanin bozuldugunu dusunur.
    """
    for etiket in HASTALIK_ETIKETLERI:
        kayit = tedavi_bul(etiket)
        for alan in ("ad", "belirti", "dogal", "kimyasal", "korunma"):
            assert kayit[alan].strip(), f"{etiket}: {alan} bos"
