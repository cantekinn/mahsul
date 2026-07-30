"""Hangi tarla karti hangi urunu cevaplayabilir. Tek kaynak.

NEDEN AYRI BIR MODUL:
Once tek bir liste vardi (core.config.agent_crops, 6 urun) ve uc kart da onu
kullaniyordu. Bu liste UC AYRI SINIRIN EN DARINA gore kesilmisti: sulama Kc
ister, iklim riski sicaklik trapezi ister, zararli ise urune ozel bocek
fenolojisi ister. Bunlar ayni sinirlar degil:

    iklim riski : sicaklik trapezi                -> 116 urun (bilgi tabani)
    sulama      : FAO-56 Tablo 12 Kc katsayisi    ->  84 urun
    zararli     : bocek basina derece-gun tablosu ->   6 urun

Tek listede birlestirilince iklim riski 116 yerine 6 urun cevapliyordu, yani
elde olan bilgi kullanilmadan atiliyordu. Yetenekler ayrildi; her kart kendi
kumesine bakar ve cevaplayamadiginda SEBEBINI soyler ("bu urun icin Kc yok"),
urunu listeden gizlemez. Gizlemek kullaniciya bilginin var olmadigini degil,
urunun var olmadigini dusundururdu.

Kumeler tablolardan TURETILIYOR, elle yazilmiyor: Kc tablosuna bir urun
eklendigi anda sulama karti onu kendiliginden destekler.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from knowledge.degree_day import PEST_TABLE
from knowledge.fao56 import KC_TABLE

_YEREL_KB = Path(__file__).resolve().parent / "crop_params.yaml"


@lru_cache(maxsize=1)
def iklim_bilgi_tabani() -> dict:
    """Iklim riski icin urun parametreleri: kuresel tablo + yerel 6 urun.

    Iki dosya birlesiyor cunku ikisi de gerekli:
      crop_params_global.yaml : 115 urun, EcoCrop turevi, oneri motorunun tabani
      crop_params.yaml        : 6 urun, Antalya icin elle ayarlanmis; ayrica
                                'narenciye' anahtari SADECE burada var (kuresel
                                tabloda portakal/limon/mandalina diye ayri ayri)

    CAKISMADA YEREL KAZANIYOR. Sebep davranis korumasi: domates/biber/patates/
    zeytin/muz icin iklim riski bugune kadar yerel esiklerle hesaplandi, kuresel
    tabloya gecmek ayni tarlada dunkunden farkli bir don uyarisi uretirdi.
    """
    from models.crop_reco.global_reco import bilgi_tabani

    birlesik = dict(bilgi_tabani())
    with _YEREL_KB.open(encoding="utf-8") as fh:
        birlesik.update(yaml.safe_load(fh))
    return birlesik


@lru_cache(maxsize=1)
def iklim_urunleri() -> frozenset[str]:
    """Iklim riski hesaplanabilen urunler: sicaklik trapezi olan her urun."""
    return frozenset(
        k for k, v in iklim_bilgi_tabani().items() if isinstance(v, dict) and "sicaklik" in v
    )


@lru_cache(maxsize=1)
def sulama_urunleri() -> frozenset[str]:
    """Sulama hesaplanabilen urunler: FAO-56 Tablo 12'de Kc'si olanlar."""
    return frozenset(KC_TABLE)


@lru_cache(maxsize=1)
def zararli_urunleri() -> frozenset[str]:
    """Zararli takvimi olan urunler: derece-gun tablosundaki boceklerin konaklari."""
    return frozenset(k for p in PEST_TABLE.values() for k in p["konak"])


# Uc noktalar ve arayuz bu adlarla konusur.
YETENEKLER = {
    "sulama": sulama_urunleri,
    "iklim": iklim_urunleri,
    "zararli": zararli_urunleri,
}

# Kart cevap veremediginde kullaniciya gosterilecek SEBEP. Uc yetenegin
# cevapsizlik nedeni farkli, tek bir "desteklenmiyor" cumlesi bunu gizlerdi.
YETENEK_GEREKCE = {
    "sulama": "Bu ürün FAO-56 Tablo 12'de yok; su tüketim katsayısı (Kc) "
              "olmadan sulama miktarı hesaplanamaz. Benzer bir ürünün "
              "katsayısını kullanmak sayıyı uydurmak olurdu.",
    "iklim": "Bu ürün için sıcaklık eşikleri tanımlı değil; don ve sıcak "
             "riski ürüne özel eşiksiz değerlendirilemez.",
    "zararli": "Bu ürünün zararlıları için derece-gün tablosu henüz yok. "
               "Tabloda şu an domates, biber, patates, zeytin ve narenciye var.",
}


def destekli(yetenek: str, urun: str) -> bool:
    return urun in YETENEKLER[yetenek]()


def kapsam(yetenek: str) -> frozenset[str]:
    return YETENEKLER[yetenek]()
