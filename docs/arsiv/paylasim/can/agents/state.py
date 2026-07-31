"""LangGraph paylasilan durum (state) tanimi.

Tum agent'lar bu ortak durumu okur/yazar. Orkestrator, niyeti (intent)
belirleyip ilgili agent'a yonlendirir; agent sonucunu `result`'a yazar.
"""
from __future__ import annotations

from typing import Optional, TypedDict


class AgentState(TypedDict, total=False):
    query: str                    # kullanicinin sorusu / istegi
    intent: str                   # router'in belirledigi niyet
    farm_profile: Optional[dict]  # aktif tarla profili (hafizadan)
    result: dict                  # secilen agent'in ciktisi
