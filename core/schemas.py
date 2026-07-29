"""Proje genelinde paylasilan veri modelleri (pydantic)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Parcel(BaseModel):
    """MEGSIS'ten cozulen parsel bilgisi."""
    il: str
    ilce: str
    mahalle: str
    ada: str
    parsel: str
    lat: float | None = None
    lon: float | None = None
    alan_m2: float | None = None
    mevkii: str | None = None
    nitelik: str | None = None


class SoilData(BaseModel):
    """SoilGrids'ten gelen toprak ozellikleri (koordinattan)."""
    ph: float | None = None
    nitrogen: float | None = None
    clay: float | None = None
    sand: float | None = None
    silt: float | None = None
    organic_carbon: float | None = None


class ClimateData(BaseModel):
    """Open-Meteo'dan gelen iklim ozeti."""
    temperature: float | None = None      # ortalama C
    humidity: float | None = None         # %
    rainfall: float | None = None         # mm (donem toplami)


class FarmProfile(BaseModel):
    """Tarlanin kalici profili (hafiza katmani)."""
    id: str | None = None
    parcel: Parcel
    soil: SoilData | None = None
    climate: ClimateData | None = None
    notes: str = ""


class AgentResult(BaseModel):
    """Her agent'in standart ciktisi."""
    agent: str
    message: str
    data: dict = Field(default_factory=dict)
