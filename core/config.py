"""Merkezi yapilandirma. Ortam degiskenlerini .env'den okur."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///farm.db")

    # Dis veri kaynaklari (hepsi ucretsiz / anahtarsiz)
    open_meteo_url: str = "https://api.open-meteo.com/v1/forecast"
    soilgrids_url: str = "https://rest.isric.org/soilgrids/v2.0/properties/query"
    megsis_url: str = "https://cbsapi.tkgm.gov.tr/megsis"

    # Odak bolge / urunler (Sprint 1)
    region: str = "Antalya"
    target_crops: tuple[str, ...] = ("domates", "biber", "patates")

    # Sulama/iklim/zararli ajanlarinin ve HTTP uc noktalarinin isleyebildigi
    # urunler. Uc ajan bu listeyi kendi icinde ayri ayri tutuyordu; dordunculer
    # (HTTP uc noktalari) eklenince liste dort yerde ayni kalmak zorunda
    # kalacakti. Tek yer: burasi.
    #
    # Sinir NEREDEN GELIYOR: Kc katsayilari (fao56.KC_TABLE) ve zararli
    # tablosu (degree_day.PEST_TABLE) yalnizca bu urunler icin tanimli.
    # Liste uzatilirsa o iki tablo da genisletilmeli, yoksa Kc sessizce 1.0
    # (referans cim) olur ve sulama miktari yanlis cikar.
    agent_crops: tuple[str, ...] = (
        "domates", "biber", "patates", "narenciye", "zeytin", "muz",
    )


settings = Settings()
