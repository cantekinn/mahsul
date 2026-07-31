"""Tarla profili kalici hafizasi (Sprint 1 - Ozlem).

Ciftcinin tarlasini (parsel + toprak + iklim + notlar) SQLite'ta saklar.
Bu, cok agentli sistemin "hafiza" katmani: agent'lar sonraki oturumlarda ayni
tarlayi hatirlar (sezon gunlugu, tekrar analiz gerektirmez).

FarmProfile pydantic modeli JSON olarak tek satirda tutulur; sorgu icin
il/ilce/ada/parsel ayrica kolonlanir.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from core.config import settings
from core.schemas import FarmProfile


class _Base(DeclarativeBase):
    pass


class _FarmRow(_Base):
    __tablename__ = "farm_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    il: Mapped[str] = mapped_column(String(64), index=True)
    ilce: Mapped[str] = mapped_column(String(64))
    ada: Mapped[str] = mapped_column(String(32))
    parsel: Mapped[str] = mapped_column(String(32))
    profil_json: Mapped[str] = mapped_column(Text)
    guncelleme: Mapped[str] = mapped_column(String(32))


_engine = create_engine(settings.database_url, future=True)
_Base.metadata.create_all(_engine)


def save_profile(profile: FarmProfile) -> str:
    """Profili kaydeder/gunceller ve id dondurur (yoksa uretir)."""
    pid = profile.id or str(uuid.uuid4())
    profile.id = pid
    row = _FarmRow(
        id=pid,
        il=profile.parcel.il,
        ilce=profile.parcel.ilce,
        ada=profile.parcel.ada,
        parsel=profile.parcel.parsel,
        profil_json=profile.model_dump_json(),
        guncelleme=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    with Session(_engine) as s:
        s.merge(row)
        s.commit()
    return pid


def get_profile(profile_id: str) -> FarmProfile | None:
    """id ile profili getirir."""
    with Session(_engine) as s:
        row = s.get(_FarmRow, profile_id)
        if row is None:
            return None
        return FarmProfile.model_validate_json(row.profil_json)


def find_by_parcel(il: str, ada: str, parsel: str) -> FarmProfile | None:
    """il+ada+parsel ile mevcut profili bulur (varsa)."""
    with Session(_engine) as s:
        stmt = select(_FarmRow).where(
            _FarmRow.il == il, _FarmRow.ada == ada, _FarmRow.parsel == parsel
        )
        row = s.scalars(stmt).first()
        return FarmProfile.model_validate_json(row.profil_json) if row else None


def list_profiles() -> list[dict]:
    """Kayitli profillerin ozetini dondurur (UI listesi icin)."""
    with Session(_engine) as s:
        rows = s.scalars(select(_FarmRow).order_by(_FarmRow.guncelleme.desc())).all()
        return [
            {
                "id": r.id,
                "il": r.il,
                "ilce": r.ilce,
                "ada": r.ada,
                "parsel": r.parsel,
                "guncelleme": r.guncelleme,
            }
            for r in rows
        ]


def delete_profile(profile_id: str) -> bool:
    """Profili siler; silindiyse True."""
    with Session(_engine) as s:
        row = s.get(_FarmRow, profile_id)
        if row is None:
            return False
        s.delete(row)
        s.commit()
        return True
