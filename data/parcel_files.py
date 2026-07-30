"""Yerel MEGSIS/TKGM parsel JSON dosyalarindan parsel yukleyici.

Repo kokunde bolge klasorleri (orn. serik_bogazkent, aksu, alanya_turkler,
gazipasa_beyobasi) icindeki `tkgm-parsel-sorgu-sonuc-*.json` dosyalarini tarar.
Her dosya bir GeoJSON FeatureCollection'dir; buradan:
  - adres bilgisi (il/ilce/mahalle/ada/parsel, mevkii, nitelik)
  - merkez koordinat (lat/lon) ve alan (m2)  -> data.megsis.parcel_from_geojson
uretilir. Boylece kullanici elle ada/parsel/koordinat girmeden dropdown'dan
parsel secebilir.

Canli MEGSIS servisine ihtiyac yoktur; tamamen yerel dosyalardan calisir.
"""
from __future__ import annotations

import json
from pathlib import Path

from core.schemas import Parcel
from data.megsis import parcel_from_geojson

_ROOT = Path(__file__).resolve().parent.parent
_GLOB = "*/tkgm-parsel-sorgu-sonuc-*.json"


def _bolge_etiketi(klasor: str) -> str:
    """Klasor adini okunabilir bolge etiketine cevirir (serik_bogazkent -> Serik Bogazkent)."""
    return klasor.replace("_", " ").title()


def _parse_dosya(path: Path) -> Parcel | None:
    """Tek bir TKGM JSON dosyasindan Parcel uretir; hata olursa None."""
    try:
        geojson = json.loads(path.read_text(encoding="utf-8"))
        props = geojson["features"][0]["properties"]
        parcel = parcel_from_geojson(
            geojson,
            il=props.get("Il", ""),
            ilce=props.get("Ilce", ""),
            mahalle=props.get("Mahalle", ""),
            ada=props.get("Ada", ""),
            parsel=props.get("ParselNo", ""),
        )
        parcel.mevkii = props.get("Mevkii") or None
        parcel.nitelik = props.get("Nitelik") or None
        return parcel
    except (KeyError, IndexError, ValueError):
        return None


def load_parcels() -> list[dict]:
    """Tum bolge klasorlerindeki parselleri okur.

    Donen her oge:
        {
          "bolge": "Serik Bogazkent",
          "etiket": "Serik Bogazkent - ada 10 parsel 1 (Kulak Ve Kumluk)",
          "parcel": Parcel,   # merkez koordinat + alan + adres dolu
        }
    Etikete gore alfabetik siralanir.
    """
    kayitlar: list[dict] = []
    for path in sorted(_ROOT.glob(_GLOB)):
        parcel = _parse_dosya(path)
        if parcel is None:
            continue
        bolge = _bolge_etiketi(path.parent.name)
        mevki = f" ({parcel.mevkii})" if parcel.mevkii else ""
        etiket = f"{bolge} - ada {parcel.ada} parsel {parcel.parsel}{mevki}"
        kayitlar.append({"bolge": bolge, "etiket": etiket, "parcel": parcel})

    kayitlar.sort(key=lambda k: k["etiket"])
    return kayitlar
