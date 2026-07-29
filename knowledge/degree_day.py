"""Derece-gun (GDD) zararli fenoloji modeli (Sprint 2).

MAKINE OGRENMESI DEGIL, kabul gormus fenoloji fizigi.
Bocekler sicaklikla gelisir; belirli bir taban sicakligin (Tbase) uzerinde
biriken isi (Growing Degree Days) yasam evrelerini ve nesil sayisini belirler.

GDD_gun = max(0, (min(Tmax,Tupper) + Tmin)/2 - Tbase)   [derece-gun]
Biofix'ten (sezon baslangici) itibaren toplanir; esikleri asinca ilgili
evre/nesil gerceklesmis sayilir -> izleme/mucadele penceresi.

Esik degerleri bolgesel literatur ortalamalaridir; kesin mucadele icin
yerel tuzak/biofix kalibrasyonu onerilir.
"""
from __future__ import annotations


def gdd_day(tmin: float, tmax: float, tbase: float, tupper: float | None = None) -> float:
    """Tek gun icin GDD (yatay ust-kesme yontemi)."""
    tmax_c = min(tmax, tupper) if tupper is not None else tmax
    tmean = (tmax_c + tmin) / 2
    return max(0.0, tmean - tbase)


def accumulate_gdd(
    tmins: list[float], tmaxs: list[float], tbase: float, tupper: float | None = None
) -> float:
    """Gunluk min/max serisinden toplam biriken GDD."""
    return sum(gdd_day(tn, tx, tbase, tupper) for tn, tx in zip(tmins, tmaxs))


# Antalya hedef urunlerinin baslica zararlilari (literatur ortalamalari)
#   tbase/tupper : gelisim taban ve ust sicakligi (C)
#   nesil_gdd    : yumurtadan yetiskine bir nesil icin biriken GDD
#   evreler      : nesil ici kumulatif esikler (biofix'ten)
PEST_TABLE: dict[str, dict] = {
    "tuta_absoluta": {
        "ad": "Domates güvesi (Tuta absoluta)",
        "konak": ("domates", "patates", "biber"),
        "tbase": 8.1, "tupper": 34.6, "nesil_gdd": 453,
        "evreler": {"Yumurta açılımı": 60, "Larva": 250, "Yetişkin": 453},
        "not": "Yaprakta galeri/tünel açar. Feromon tuzak ve Bacillus thuringiensis ile mücadele; her nesil başında izleyin.",
    },
    "leptinotarsa": {
        "ad": "Patates böceği (Colorado)",
        "konak": ("patates",),
        "tbase": 10.0, "tupper": 33.0, "nesil_gdd": 335,
        "evreler": {"Yumurta açılımı": 120, "Larva": 250, "Yetişkin": 335},
        "not": "Yaprakları hızla yer. Erken larva döneminde mücadele edin; ürün nöbetleşmesi uygulayın.",
    },
    "bemisia_tabaci": {
        "ad": "Beyazsinek (Bemisia tabaci)",
        "konak": ("domates", "biber", "patates"),
        "tbase": 10.0, "tupper": 32.0, "nesil_gdd": 320,
        "evreler": {"Yumurta açılımı": 90, "Nimf": 200, "Yetişkin": 320},
        "not": "Virüs taşır. Sarı yapışkan tuzak ve biyolojik mücadele (Encarsia) kullanın.",
    },
    "bactrocera_oleae": {
        "ad": "Zeytin sineği (Bactrocera oleae)",
        "konak": ("zeytin",),
        "tbase": 9.0, "tupper": 32.0, "nesil_gdd": 400,
        "evreler": {"Yumurta açılımı": 80, "Larva": 260, "Yetişkin": 400},
        "not": "Meyveye yumurta bırakır. McPhail tuzağıyla izleyin; yakalanan sayıya göre mücadele edin.",
    },
    "ceratitis_capitata": {
        "ad": "Akdeniz meyve sineği (Ceratitis capitata)",
        "konak": ("narenciye",),
        "tbase": 10.2, "tupper": 33.0, "nesil_gdd": 450,
        "evreler": {"Yumurta açılımı": 90, "Larva": 300, "Yetişkin": 450},
        "not": "Olgunlaşan meyveyi delip yumurtlar. Tuzak ve zehirli yem ile kısmi dal uygulaması yapın.",
    },
}


def pests_for_crop(crop: str) -> list[str]:
    """Verilen urunu konak alan zararlilarin anahtarlari."""
    return [k for k, v in PEST_TABLE.items() if crop in v["konak"]]


def pest_status(cumulative_gdd: float, pest_key: str) -> dict:
    """Biriken GDD'ye gore zararlinin nesil/evre durumu."""
    pest = PEST_TABLE[pest_key]
    nesil_gdd = pest["nesil_gdd"]
    nesil_no = int(cumulative_gdd // nesil_gdd) + 1
    icinde = cumulative_gdd % nesil_gdd                      # mevcut nesildeki birikim

    # mevcut nesil icinde hangi evrede?
    evre = "Yumurta"
    kalan_evre = None
    for ad, esik in pest["evreler"].items():
        if icinde >= esik:
            evre = ad
        else:
            kalan_evre = (ad, round(esik - icinde, 1))
            break

    return {
        "zararli": pest["ad"],
        "toplam_gdd": round(cumulative_gdd, 1),
        "nesil": nesil_no,
        "evre": evre,
        "sonraki_evre": kalan_evre,          # (ad, kalan_gdd) veya None
        "not": pest["not"],
    }
