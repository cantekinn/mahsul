"""Zararli agent'i (Sprint 2): derece-gun (GDD) ile zararli fenoloji tahmini.

Akis:
  parsel (lat/lon) -> Open-Meteo gunluk min/max sicaklik (biofix'ten bugune)
  -> knowledge.degree_day: her zararli icin GDD birikimi -> nesil/evre
  -> izleme/mucadele penceresi mesaji.

Biofix (sezon baslangici) varsayilan 1 Mart (Antalya); erken tarihlerde
son ~1 ay verisiyle kismi tahmin.

Modul iki kapi sunar: zararli_durumu() saf hesaptir (hata yutmaz, HTTP uc
noktasi bunu cagirir), pest_node() LangGraph adaptorudur. Gerekce
irrigation_agent.py basindaki notta.
"""
from __future__ import annotations

from datetime import date

from agents.state import AgentState
from core.config import settings
from data.open_meteo import get_season_temps
from knowledge import degree_day as dd
from knowledge.kapsam import zararli_urunleri

# Kaynak: zararli tablosundaki boceklerin konak listesi (bkz kapsam.py).
_CROPS = zararli_urunleri


def _detect_crops(query: str) -> tuple[str, ...]:
    found = tuple(sorted(c for c in _CROPS() if c in query))
    return found or tuple(settings.target_crops)


class SicaklikSerisiYok(RuntimeError):
    """Open-Meteo cevap verdi ama biofix'ten bugune gunluk seri bos dondu."""


def zararli_durumu(
    lat: float, lon: float, urunler: tuple[str, ...], biofix: date | None = None
) -> dict:
    """Derece-gun birikimiyle zararli nesil/evre durumu. Saf hesap: hata YUTMAZ.

    Urunun tanimli zararlisi yoksa 'durumlar' bos liste doner; bu hata degil,
    gecerli bir cevaptir (ornegin muzun tabloda kaydi yok).
    """
    biofix = biofix or date(date.today().year, 3, 1)   # Antalya sezon baslangici
    temps = get_season_temps(lat, lon, biofix)
    if temps["gun"] == 0:
        raise SicaklikSerisiYok("Bu konum için sıcaklık serisi alınamadı.")

    seen: set[str] = set()
    durumlar = []
    for crop in urunler:
        for pk in dd.pests_for_crop(crop):
            if pk in seen:
                continue
            seen.add(pk)
            pest = dd.PEST_TABLE[pk]
            gdd = dd.accumulate_gdd(temps["tmin"], temps["tmax"], pest["tbase"], pest["tupper"])
            durumlar.append(dd.pest_status(gdd, pk))

    return {"gun": temps["gun"], "biofix": biofix.isoformat(), "durumlar": durumlar}


def pest_node(state: AgentState) -> AgentState:
    profile = state.get("farm_profile") or {}
    parcel = profile.get("parcel") or {}
    lat, lon = parcel.get("lat"), parcel.get("lon")
    query = state.get("query", "").lower()

    if lat is None or lon is None:
        return {"result": {
            "agent": "pest",
            "message": "Zararlı tahmini için önce parsel/konum girip tarlayı tanıtın.",
            "data": {},
        }}

    try:
        sonuc = zararli_durumu(lat, lon, _detect_crops(query))
    except SicaklikSerisiYok as exc:
        return {"result": {"agent": "pest", "message": str(exc), "data": {}}}
    except Exception as exc:
        return {"result": {
            "agent": "pest",
            "message": f"Hava servisine ulaşılamadı, zararlı tahmini yapılamadı ({exc}).",
            "data": {},
        }}

    results = sonuc["durumlar"]
    if not results:
        return {"result": {
            "agent": "pest",
            "message": "Seçilen ürün için tanımlı zararlı kaydı yok.",
            "data": {},
        }}

    lines = []
    for r in results:
        sonraki = ""
        if r["sonraki_evre"]:
            ad, kalan = r["sonraki_evre"]
            sonraki = f", sonraki evre: {ad} (yaklaşık {kalan} GDD sonra)"
        lines.append(
            f"- {r['zararli']}: {r['nesil']}. nesil, {r['evre']} evresinde "
            f"(toplam {r['toplam_gdd']} GDD){sonraki}\n    {r['not']}"
        )
    msg = (
        f"Zararlı derece-gün tahmini (başlangıç 1 Mart, {sonuc['gun']} gün):\n"
        + "\n".join(lines)
    )
    return {"result": {"agent": "pest", "message": msg, "data": sonuc}}
