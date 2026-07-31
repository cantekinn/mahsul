"""Gercek MEGSIS parsel kayitlarini DB'ye tohumlar (test icin hazir liste).

Kayitlar data/parcels_seed.csv dosyasindan okunur. Boylece UI'da her seferinde
elle ada/parsel girmek yerine "Kayitli tarla yukle" dropdown'undan secilir.

CSV kolonlari (baslik zorunlu):
    il,ilce,mahalle,ada,parsel,lat,lon,alan_m2
  - lat/lon: parsel merkez koordinati (MEGSIS poligonunun merkezi)
  - alan_m2: opsiyonel (bos birakilabilir); toplam su/gubre hesabinda kullanilir

Deterministik id (uuid5) sayesinde tekrar calisinca cogaltmaz, gunceller.

Calistirma:
    py -m scripts.seed_parcels
"""
from __future__ import annotations

import csv
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.schemas import FarmProfile, Parcel
from memory.farm_profile_db import save_profile

_CSV = Path(__file__).resolve().parent.parent / "data" / "parcels_seed.csv"
_NS = uuid.UUID("00000000-0000-0000-0000-0000000a0a0a")


def _num(value: str | None) -> float | None:
    value = (value or "").strip()
    if not value:
        return None
    return float(value.replace(",", "."))


def seed() -> None:
    if not _CSV.exists():
        print(f"[hata] CSV yok: {_CSV}")
        print("Gercek MEGSIS kayitlarini bu dosyaya ekleyin (baslik: il,ilce,mahalle,ada,parsel,lat,lon,alan_m2).")
        return

    count = 0
    with _CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if not (row.get("ada") and row.get("parsel")):
                continue
            parcel = Parcel(
                il=row.get("il", "Antalya").strip(),
                ilce=row.get("ilce", "").strip(),
                mahalle=row.get("mahalle", "").strip(),
                ada=row["ada"].strip(),
                parsel=row["parsel"].strip(),
                lat=_num(row.get("lat")),
                lon=_num(row.get("lon")),
                alan_m2=_num(row.get("alan_m2")),
            )
            prof = FarmProfile(
                id=str(uuid.uuid5(_NS, f"{parcel.il}-{parcel.ada}-{parcel.parsel}")),
                parcel=parcel,
                notes="seed",
            )
            save_profile(prof)
            count += 1

    print(f"[ok] {count} parsel DB'ye yazildi (tekrar calisinca gunceller).")
    print("UI'da sol paneldeki 'Kayitli tarla yukle' dropdown'undan sec.")


if __name__ == "__main__":
    seed()
