"""GBDT ikinci gorus katmani (Sprint 1 - Sila).

Egitilmis LightGBM modelini (train_gbdt.py ciktisi) yukler ve kural tabanli
motora "ikinci gorus" saglar. Model Kaggle Crop Recommendation veri setinde
egitildi; 22 Hindistan urununu kapsar, bizim hedef urunlerimizle sadece
orange->narenciye ve banana->muz ortusur. Bu yuzden GBDT birincil karar
kaynagi DEGILDIR; kural motoru (recommender.py) birincil kalir.

Onemli veri uyumsuzlugu:
  Model 7 girdi ister: N, P, K, temperature, humidity, ph, rainfall.
  SoilGrids hattimiz N/P/K oranini (Kaggle olcegi) ve P/K'yi vermez; sadece
  azot (g/kg), pH, doku, organik karbon gelir. Bu yuzden:
    - ph, temperature, humidity, rainfall  -> kendi hattimizdan gelir
    - N, P, K                              -> toprak analizinden girilir;
      girilmezse veri seti medyani kullanilir ve sonuc "gosterge" isaretlenir.
  Bu nedenle GBDT ciktisi guven amacli degil, sadece iklim-toprak parmak izi
  benzerligi gostergesidir.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from core.schemas import ClimateData, SoilData

_MODEL_PATH = Path(__file__).resolve().parent / "gbdt_model.txt"
_LABELS_PATH = Path(__file__).resolve().parent / "gbdt_labels.txt"

# Egitim ile ayni sira (train_gbdt._FEATURES)
_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

# N/P/K girilmezse kullanilan veri seti medyanlari (Kaggle Crop Recommendation).
# Notr on-kabul; toprak analizi ile degistirilmesi onerilir.
_DEFAULT_NPK = {"N": 37.0, "P": 51.0, "K": 32.0}

# Kaggle etiketi -> bizim urun anahtarimiz (yalnizca net ortusenler).
# Digerleri "iklim benzeri" olarak Ingilizce etiketiyle gosterilir.
_LABEL_MAP = {
    "orange": "narenciye",
    "banana": "muz",
}


@lru_cache(maxsize=1)
def _load_model():
    """Egitilmis LightGBM booster'i ve etiketleri yukler (onbellekli).

    Model dosyalari yoksa (egitim yapilmadi) None dondurur; cagiran taraf
    GBDT'yi atlar ve yalnizca kural motorunu kullanir.
    """
    if not _MODEL_PATH.exists() or not _LABELS_PATH.exists():
        return None, None
    import lightgbm as lgb  # yalnizca gerektiginde import (agir bagimlilik)

    booster = lgb.Booster(model_file=str(_MODEL_PATH))
    labels = _LABELS_PATH.read_text(encoding="utf-8").splitlines()
    return booster, labels


def model_available() -> bool:
    """GBDT modeli egitilmis ve yuklenebilir mi?"""
    booster, _ = _load_model()
    return booster is not None


def _map_label(kaggle_label: str) -> tuple[str, bool]:
    """Kaggle etiketini bizim urun anahtarina cevirir.

    Donen: (gosterim_adi, bizim_urunumuz_mu)
    """
    key = _LABEL_MAP.get(kaggle_label)
    if key is not None:
        return key, True
    return kaggle_label, False


def second_opinion(
    soil: SoilData,
    climate: ClimateData,
    npk: dict | None = None,
    top_k: int = 3,
) -> dict | None:
    """GBDT ile ikinci gorus dondurur (kural motorunu desteklemek icin).

    npk: {"N":.., "P":.., "K":..} toprak analizinden. None ise veri seti
         medyani kullanilir ve sonuc 'gosterge' isaretlenir.

    Donen sozluk:
        {
          "gosterge": bool,          # N/P/K varsayilan mi kullanildi
          "not": str,                # kullaniciya aciklama
          "tahminler": [             # olasiliga gore sirali
             {"ad": str, "olasilik": float, "bizim_urun": bool}, ...
          ]
        }
    Model yoksa ya da zorunlu iklim/toprak verisi eksikse None doner.
    """
    booster, labels = _load_model()
    if booster is None:
        return None

    # Zorunlu ozellikler bizim hattimizdan: en az ph + sicaklik gerekli
    if soil.ph is None or climate.temperature is None:
        return None

    gosterge = npk is None
    kaynak_npk = {**_DEFAULT_NPK, **(npk or {})}

    row = {
        "N": kaynak_npk["N"],
        "P": kaynak_npk["P"],
        "K": kaynak_npk["K"],
        "temperature": climate.temperature,
        "humidity": climate.humidity if climate.humidity is not None else 65.0,
        "ph": soil.ph,
        "rainfall": climate.rainfall if climate.rainfall is not None else 500.0,
    }
    x = [[row[f] for f in _FEATURES]]
    proba = booster.predict(x)[0]  # sinif olasiliklari

    sirali = sorted(range(len(labels)), key=lambda i: proba[i], reverse=True)
    tahminler = []
    for i in sirali[:top_k]:
        ad, bizim = _map_label(labels[i])
        tahminler.append(
            {"ad": ad, "olasilik": round(float(proba[i]), 3), "bizim_urun": bizim}
        )

    if gosterge:
        not_ = (
            "N/P/K girilmedi; veri seti medyani kullanildi. Sonuc yalnizca "
            "iklim-toprak benzerligi gostergesidir, toprak analizi ile guclenir."
        )
    else:
        not_ = "Toprak analizi N/P/K degerleri kullanildi."

    return {"gosterge": gosterge, "not": not_, "tahminler": tahminler}
