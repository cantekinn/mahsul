"""SoilGrids (ISRIC) istemcisi: koordinattan toprak ozellikleri (ucretsiz).

0-5 cm derinlikteki ortalama degerleri ceker. SoilGrids degerleri olcekli
gelir (orn. pH x10), asagida gercek birime cevrilir.

NOT: SoilGrids kullanilabilir P/K vermez; sadece pH, azot, doku, organik
karbon guvenilirdir. Gubre/eksik element icin bunlar + bolgesel ortalama
kullanilir (bkz. proje notlari).
"""
from __future__ import annotations

import requests

from core.config import settings
from core.schemas import SoilData

# SoilGrids ozellik adi -> (SoilData alani, olcek bolme faktoru)
_PROPS = {
    "phh2o": ("ph", 10.0),          # pH x10 -> pH
    "nitrogen": ("nitrogen", 100.0),  # cg/kg -> g/kg
    "clay": ("clay", 10.0),         # g/kg -> %
    "sand": ("sand", 10.0),
    "silt": ("silt", 10.0),
    "soc": ("organic_carbon", 10.0),  # dg/kg -> g/kg
}


def get_soil(lat: float, lon: float, timeout: int = 30) -> SoilData:
    """Verilen koordinat icin 0-5 cm toprak ozelliklerini dondurur."""
    params = [("lat", lat), ("lon", lon), ("depth", "0-5cm"), ("value", "mean")]
    params += [("property", p) for p in _PROPS]

    resp = requests.get(settings.soilgrids_url, params=params, timeout=timeout)
    resp.raise_for_status()
    layers = resp.json().get("properties", {}).get("layers", [])

    values: dict[str, float] = {}
    for layer in layers:
        name = layer.get("name")
        if name not in _PROPS:
            continue
        field, factor = _PROPS[name]
        depths = layer.get("depths", [])
        if depths and depths[0].get("values", {}).get("mean") is not None:
            values[field] = round(depths[0]["values"]["mean"] / factor, 2)

    return SoilData(**values)
