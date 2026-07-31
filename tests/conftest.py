"""Testlerin proje kokunu bulmasi icin tek satirlik yol ayari.

Moduller `knowledge.fao56` gibi kok-goreli adlarla import ediliyor. pytest
tests/ klasorunden calistirildiginda kok sys.path'te olmayabilir; burada bir
kez ekleniyor ki testler hangi dizinden cagrilirsa cagrilsin ayni sonucu
versin.
"""
from __future__ import annotations

import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))
