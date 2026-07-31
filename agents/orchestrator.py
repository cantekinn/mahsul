"""Orkestrator: niyeti belirler ve dogru uzman agent'a yonlendirir.

Sprint 3 itibariyla YEDI dugumun yedisi de gercek; stub kalmadi (carbon en son
gerceklendi, bkz agents/carbon_agent.py).

Bu modul langgraph'a bagli oldugu icin canli kaba GIRMIYOR. Ayni yonlendirme
karari HTTP'de de gerekiyordu; o yuzden karar mantigi agents/router.py'ye
tasindi ve iki taraf da oradan okuyor. Burada kalan sey yalnizca grafik
kurulumu.
"""
from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.advisor_agent import advisor_node
from agents.climate_risk_agent import climate_risk_node
from agents.diagnosis_agent import diagnosis_node
from agents.irrigation_agent import irrigation_node
from agents.carbon_agent import carbon_node
from agents.pest_agent import pest_node
from agents.router import INTENT_KEYWORDS, route  # noqa: F401  (disari acik)
from agents.state import AgentState
from core.schemas import ClimateData, SoilData
from models.crop_reco import recommend


def route_intent(state: AgentState) -> AgentState:
    """Kullanici sorgusundan (veya fotograf varliginda) niyeti cikarir.

    Karar mantigi agents/router.py'de: HTTP katmani da ayni yonlendiriciyi
    kullaniyor, iki kopya olmasin diye.
    """
    return {"intent": route(
        state.get("query", ""),
        has_image=bool(state.get("image_path")),
    )}


def crop_reco_node(state: AgentState) -> AgentState:
    """Aktif tarla profilinden toprak+iklime gore urun onerir (Sprint 1 - Sila)."""
    profile = state.get("farm_profile") or {}
    soil = SoilData(**(profile.get("soil") or {}))
    climate = ClimateData(**(profile.get("climate") or {}))

    if soil.ph is None and climate.temperature is None:
        return {
            "result": {
                "agent": "crop_reco",
                "message": "Once tarla konumunu girip toprak/iklim verisini getirin.",
                "data": {},
            }
        }

    recos = recommend(soil, climate, top_k=3)
    lines = [
        f"{i}. {r['ad']} - skor {r['skor']} ({r['uygunluk']})"
        for i, r in enumerate(recos, 1)
    ]
    message = "Toprak ve iklime en uygun urunler:\n" + "\n".join(lines)
    return {"result": {"agent": "crop_reco", "message": message, "data": {"oneriler": recos}}}


AGENT_NODES = {
    "crop_reco": crop_reco_node,
    "diagnosis": diagnosis_node,
    "irrigation": irrigation_node,
    "climate_risk": climate_risk_node,
    "pest": pest_node,
    "carbon": carbon_node,
    "advisor": advisor_node,
}


def build_graph():
    """Orkestrasyon grafigini kurar ve derler."""
    graph = StateGraph(AgentState)

    graph.add_node("router", route_intent)
    for name, node in AGENT_NODES.items():
        graph.add_node(name, node)

    graph.set_entry_point("router")
    # router -> niyete gore ilgili agent
    graph.add_conditional_edges(
        "router",
        lambda state: state["intent"],
        {name: name for name in AGENT_NODES},
    )
    # her agent -> son
    for name in AGENT_NODES:
        graph.add_edge(name, END)

    return graph.compile()
