"""Sulama agent'i (Sprint 2): FAO-56 ile gunluk sulama plani.

Akis:
  parsel (lat/lon/alan) -> Open-Meteo ET0 (FAO-56) + beklenen yagis
  -> knowledge.fao56.irrigation_plan -> her urun icin net sulama (mm/gun, litre/gun)

Urun sorguda gecerse (ornegin "domates") sadece o urun; yoksa bolge hedef
urunleri (config.settings.target_crops) icin plan uretilir.

IKI GIRIS KAPISI VAR, SEBEBI:
  sulama_plani()   : saf hesap. Parametreleri acik alir, hata YUTMAZ, mesaj
                     kurmaz. HTTP uc noktasi bunu cagirir; boylece Open-Meteo
                     susunca kullaniciya 200 + "ulasilamadi" metni degil, 503 +
                     sunucunun kendi gerekcesi doner (projenin /oneri'de
                     yerlesik davranisi).
  irrigation_node(): LangGraph adaptoru. Serbest metinden urun/asama cikarir,
                     hatayi yutup sohbet cumlesi kurar, cunku grafik ortasinda
                     patlayan bir dugum tum akisi durdurur.
Hesap tek yerde (sulama_plani) duruyor; iki kapinin ayrisip farkli sayi
uretmesi mumkun degil.
"""
from __future__ import annotations

from agents.state import AgentState
from core.config import settings
from data.open_meteo import get_irrigation_inputs
from knowledge import fao56
from knowledge.kapsam import sulama_urunleri

# sorguda urun/asama tespiti. Kaynak: Kc tablosunun kendisi (bkz kapsam.py) -
# elle tutulan bir liste, tablo genisleyince sessizce geride kalirdi.
_CROPS = sulama_urunleri
_STAGE_KEYWORDS = {
    "ini": ("fide", "ekim", "dikim", "baslangic", "cimlen"),
    "end": ("hasat", "olgun", "son donem"),
}


def _detect_stage(query: str) -> str:
    for stage, kws in _STAGE_KEYWORDS.items():
        if any(kw in query for kw in kws):
            return stage
    return "mid"


def _detect_crops(query: str) -> tuple[str, ...]:
    found = tuple(sorted(c for c in _CROPS() if c in query))
    return found or tuple(settings.target_crops)


class ET0Yok(RuntimeError):
    """Open-Meteo cevap verdi ama bu konum icin ET0 uretmedi (deniz, kutup)."""


def sulama_plani(
    lat: float,
    lon: float,
    urunler: tuple[str, ...],
    asama: str = "mid",
    alan_m2: float | None = None,
) -> dict:
    """Bir konum icin FAO-56 sulama plani. Saf hesap: hata YUTMAZ.

    Open-Meteo erisilemezse cagiranin gormesi icin istisna yukari gider.
    ET0 uretilemezse ET0Yok atar. Urunun FAO-56 Kc katsayisi yoksa fao56.KcYok
    atar; burada yakalanmaz cunku "Kc'siz urune yaklasik bir sayi uretmek" bu
    modulun yapmayacagi tek sey.
    """
    inputs = get_irrigation_inputs(lat, lon)
    et0 = inputs.get("et0_mm_gun")
    if et0 is None:
        raise ET0Yok("Bu konum için ET0 verisi üretilemedi.")

    # tahmin doneminin ORTALAMA gunluk yagisi (aya olceklemeden; yagisli bir
    # haftayi tum aya yaymak net sulamayi yaniltir).
    gun = max(inputs.get("gun", 7), 1)
    rain_daily = inputs.get("yagis_mm_donem", 0.0) / gun

    return {
        "et0_mm_gun": et0,
        "yagis_mm_donem": inputs["yagis_mm_donem"],
        "gun": gun,
        "asama": asama,
        "planlar": [
            fao56.irrigation_plan(et0, c, asama, rain_daily, alan_m2) for c in urunler
        ],
    }


def irrigation_node(state: AgentState) -> AgentState:
    profile = state.get("farm_profile") or {}
    parcel = profile.get("parcel") or {}
    lat, lon = parcel.get("lat"), parcel.get("lon")
    area = parcel.get("alan_m2")
    query = state.get("query", "").lower()

    if lat is None or lon is None:
        return {"result": {
            "agent": "irrigation",
            "message": "Sulama planı için önce parsel/konum girip tarlayı tanıtın.",
            "data": {},
        }}

    stage = _detect_stage(query)
    try:
        sonuc = sulama_plani(lat, lon, _detect_crops(query), stage, area)
    except ET0Yok as exc:
        return {"result": {"agent": "irrigation", "message": str(exc), "data": {}}}
    except fao56.KcYok as exc:
        # Ag hatasi degil kapsam sorunu; asagidaki genel dala dusup "hava
        # servisine ulasilamadi" demesi kullaniciyi yanlis yere bakmaya iterdi.
        return {"result": {
            "agent": "irrigation",
            "message": f"{exc.args[0].capitalize()} için FAO-56 su tüketim "
                       "katsayısı (Kc) tanımlı değil, sulama miktarı "
                       "hesaplanamıyor.",
            "data": {},
        }}
    except Exception as exc:  # ag/servis hatasi - agent cokmesin
        return {"result": {
            "agent": "irrigation",
            "message": f"Hava servisine ulaşılamadı, sulama planı üretilemedi ({exc}).",
            "data": {},
        }}

    et0 = sonuc["et0_mm_gun"]
    gun = sonuc["gun"]
    plans = sonuc["planlar"]

    lines = []
    for p in plans:
        litre = f", yaklaşık {p['litre_gun']:.0f} L/gün (parsel)" if "litre_gun" in p else ""
        lines.append(
            f"- {p['urun'].capitalize()}: net {p['net_mm_gun']} mm/gün "
            f"(ETc {p['etc_mm_gun']}, Kc {p['kc']}){litre}"
        )
    asama = {"ini": "başlangıç", "mid": "gelişme", "end": "hasat"}[stage]
    msg = (
        f"FAO-56 sulama planı (ET0={et0} mm/gün, {asama} aşaması, "
        f"beklenen yağış {sonuc['yagis_mm_donem']} mm/{gun} gün):\n"
        + "\n".join(lines)
    )
    return {"result": {"agent": "irrigation", "message": msg, "data": {
        "et0_mm_gun": et0,
        "yagis_mm_donem": sonuc["yagis_mm_donem"],
        "stage": stage,
        "planlar": plans,
    }}}
