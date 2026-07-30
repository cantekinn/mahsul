"""Iklim risk agent'i (Sprint 2): tahmini urune ozel risklere cevirir.

Akis:
  parsel (lat/lon) -> Open-Meteo 16 gunluk tahmin (min/max sicaklik, yagis)
  -> knowledge.climate_risk: urune ozel esiklerle don/sicak/yagis/kuraklik riski.

Urun sorguda gecerse o urun; yoksa bolge hedef urunleri degerlendirilir.

Modul iki kapi sunar: iklim_riski() saf hesaptir (hata yutmaz, HTTP uc noktasi
bunu cagirir), climate_risk_node() LangGraph adaptorudur. Gerekce
irrigation_agent.py basindaki notta.
"""
from __future__ import annotations

from agents.state import AgentState
from core.config import settings
from data.open_meteo import get_forecast_series
from knowledge import climate_risk
from knowledge.kapsam import iklim_bilgi_tabani, iklim_urunleri

# Sorguda urun tespiti icin: iklim riski hesaplanabilen HER urun. Once 6
# urunluk ortak liste kullaniliyordu, oysa sicaklik trapezi 116 urunde var
# (bkz knowledge/kapsam.py).
_CROPS = iklim_urunleri


def _detect_crops(query: str) -> tuple[str, ...]:
    found = tuple(sorted(c for c in _CROPS() if c in query))
    return found or tuple(settings.target_crops)


class TahminYok(RuntimeError):
    """Open-Meteo cevap verdi ama bu konum icin gunluk seri bos dondu."""


def iklim_riski(lat: float, lon: float, urunler: tuple[str, ...]) -> dict:
    """16 gunluk tahminden urune ozel risk listesi. Saf hesap: hata YUTMAZ."""
    fc = get_forecast_series(lat, lon)
    if fc["gun"] == 0:
        raise TahminYok("Bu konum için tahmin verisi alınamadı.")

    kb = iklim_bilgi_tabani()
    return {
        "gun": fc["gun"],
        "riskler": {
            crop: climate_risk.assess_climate_risk(
                fc["tmin"], fc["tmax"], fc["prec"],
                crop_key=crop, crop_params=kb.get(crop),
            )
            for crop in urunler
        },
    }


def climate_risk_node(state: AgentState) -> AgentState:
    profile = state.get("farm_profile") or {}
    parcel = profile.get("parcel") or {}
    lat, lon = parcel.get("lat"), parcel.get("lon")
    query = state.get("query", "").lower()

    if lat is None or lon is None:
        return {"result": {
            "agent": "climate_risk",
            "message": "İklim riski için önce parsel/konum girip tarlayı tanıtın.",
            "data": {},
        }}

    try:
        sonuc = iklim_riski(lat, lon, _detect_crops(query))
    except TahminYok as exc:
        return {"result": {"agent": "climate_risk", "message": str(exc), "data": {}}}
    except Exception as exc:
        return {"result": {
            "agent": "climate_risk",
            "message": f"Hava tahminine ulaşılamadı ({exc}).",
            "data": {},
        }}

    per_crop = sonuc["riskler"]

    # mesaj: en yuksek seviyeli riskleri one al
    order = {"yuksek": 0, "orta": 1, "dusuk": 2}
    lines = []
    for crop, risks in per_crop.items():
        risks_sorted = sorted(risks, key=lambda r: order[r["seviye"]])
        rl = "; ".join(f"[{r['seviye']}] {r['aciklama']}" for r in risks_sorted)
        lines.append(f"- {crop.capitalize()}: {rl}")

    msg = "16 günlük iklim risk değerlendirmesi:\n" + "\n".join(lines)
    return {"result": {"agent": "climate_risk", "message": msg, "data": sonuc}}
