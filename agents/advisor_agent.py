"""Danisman/tedavi agent'i (Sprint 2).

Iki gorev:
  1) Tedavi: sorguda (veya teshis ciktisinda) gecen hastaligi treatments.yaml'dan
     esleyip dogal + kimyasal + korunma onerisi verir.
  2) Genel danisman: hastalik eslesmesi yoksa sistemin yeteneklerini ve tarla
     profilini ozetleyerek yonlendirir.

RAG/LLM yerine yapili bilgi tabani (dis API/anahtar gerektirmez, ucretsiz).
Sprint 3'te vektor hafiza + LLM ile zenginlestirilebilir.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from agents.state import AgentState

_KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "treatments.yaml"


@lru_cache(maxsize=1)
def load_treatments() -> dict:
    with _KB_PATH.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def match_disease(text: str) -> tuple[str, dict] | None:
    """Metinde hastalik anahtar kelimesi arar; ilk eslesmeyi dondurur."""
    text = text.lower()
    for key, rec in load_treatments().items():
        for kw in rec.get("anahtar", []):
            if kw in text:
                return key, rec
    return None


def _treatment_message(rec: dict) -> str:
    return (
        f"{rec['ad']}\n"
        f"Belirti: {rec['belirti']}\n"
        f"Doğal/kültürel: {rec['dogal']}\n"
        f"Kimyasal (madde sınıfı): {rec['kimyasal']}\n"
        f"Korunma: {rec['korunma']}\n"
        f"Not: Kimyasal için il/ilçe Tarım Müdürlüğü + ruhsatlı ürün ve etiket dozu esastır."
    )


def advisor_node(state: AgentState) -> AgentState:
    query = state.get("query", "")

    # 1) tedavi: sorguda hastalik gecerse
    hit = match_disease(query)
    if hit:
        key, rec = hit
        return {"result": {
            "agent": "advisor",
            "message": _treatment_message(rec),
            "data": {"hastalik": key, "tedavi": rec},
        }}

    # 2) genel danisman
    profile = state.get("farm_profile") or {}
    parcel = profile.get("parcel") or {}
    yer = f"{parcel.get('ilce','')}/{parcel.get('il','')}".strip("/")
    baglam = f" Aktif tarla: {yer}." if yer else ""
    msg = (
        "Size şu konularda yardımcı olabilirim:\n"
        "- Ürün önerisi (toprak+iklime göre ne ekilir)\n"
        "- Sulama planı (FAO-56, ne kadar su)\n"
        "- İklim riski (don/sıcak/yağış/kuraklık)\n"
        "- Zararlı tahmini (derece-gün)\n"
        "- Hastalık teşhisi (yaprak fotoğrafı) ve tedavi\n"
        f"Hastalık adı veya belirti yazarsanız tedavi önerisi sunarım.{baglam}"
    )
    return {"result": {"agent": "advisor", "message": msg, "data": {}}}
