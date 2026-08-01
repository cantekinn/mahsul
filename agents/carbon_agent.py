"""Karbon ayak izi agent'i (Sprint 3): parselin sezonluk sera gazi envanteri.

Sprint 2 sonunda bu dugum stub'di. Hesap cekirdegi knowledge/karbon.py'de
(IPCC 2019 Tier 1); burada yapilan tek is, envanterin SULAMA kalemini uydurmak
yerine tarlanin kendi FAO-56 sulama planindan turetmek.

SULAMA SUYU NEREDEN GELIYOR
Envanterin bes kaleminden dordu (gubre N2O x2, gubre uretimi, dizel) yalnizca
ciftcinin girdigi miktara bagli. Besincisi, pompa elektrigi, tarlaya cekilen su
hacmine bagli ve o hacim zaten olculuyor: /sulama uc noktasindaki ayni
`sulama_plani()` net mm/gun uretiyor. Ayni sayiyi burada tekrar cagirmak yerine
ikinci bir yaklasik deger uydurmak, kullaniciya ayni tarla icin iki farkli su
miktari gosterirdi.

SEZON UZUNLUGU ACIK BIR SENARYODUR
ET0 7 gunluk tahmin penceresinden gelir. Onu sezona yaymak icin `sezon_gun`
carpani kullaniliyor ve bu yanitta ACIKCA yaziliyor ("bugunku ET0 sezon boyunca
sabit kalirsa"). Gizli bir varsayim degil, kullanicinin degistirebildigi bir
parametre; boylece sayinin nereden geldigi gorunur kalir.

IKI GIRIS KAPISI (projenin diger ajanlariyla ayni desen)
  karbon_plani() : saf hesap, hata YUTMAZ -> HTTP 503/422 uretebilsin.
  carbon_node()  : LangGraph adaptoru, hatayi yutup sohbet cumlesi kurar.
"""
from __future__ import annotations

from agents.irrigation_agent import ET0Yok, _detect_crops, sulama_plani
from agents.state import AgentState
from knowledge import karbon
from knowledge.fao56 import KcYok


def karbon_plani(
    lat: float,
    lon: float,
    urun: str,
    alan_m2: float,
    *,
    sezon_gun: int = 120,
    azot_kg_da: float | None = None,
    dizel_l_da: float | None = None,
    sulama_yontemi: str = "damla",
    su_kaynagi: str = "kuyu",
) -> dict:
    """Parselin sezonluk karbon ayak izi. Saf hesap: hata YUTMAZ.

    Sulama suyu tarlanin gercek FAO-56 planindan gelir. Urunun Kc katsayisi
    yoksa KcYok yukari gider (uydurma bir su miktari uretilmez); hava servisi
    susarsa istisna yukari gider.
    """
    plan = sulama_plani(lat, lon, (urun,), "mid", alan_m2)
    net_mm_gun = plan["planlar"][0]["net_mm_gun"]

    # 1 mm su, 1 m2'ye 1 litre demektir: mm x m2 / 1000 -> m3
    sulama_m3 = net_mm_gun * sezon_gun * alan_m2 / 1000.0

    sonuc = karbon.ayak_izi(
        alan_m2,
        azot_kg_da=azot_kg_da,
        dizel_l_da=dizel_l_da,
        sulama_m3=sulama_m3,
        sulama_yontemi=sulama_yontemi,
        su_kaynagi=su_kaynagi,
    )
    sonuc["urun"] = urun
    sonuc["sezon_gun"] = sezon_gun
    sonuc["net_mm_gun"] = net_mm_gun
    sonuc["et0_mm_gun"] = plan["et0_mm_gun"]
    # Karbonun sulama kalemi ET0'dan geliyor, yani sulama planiyla ayni kaynaga
    # bagli. Tarihi de birlikte tasiniyor ki iki kart ayni anda ayni seyi desin.
    sonuc["kayit_tarihi"] = plan.get("kayit_tarihi")
    sonuc["su_senaryosu"] = (
        f"Bugünkü ET0 ({plan['et0_mm_gun']} mm/gün) sezon boyunca sabit kalırsa, "
        f"{sezon_gun} günde net {net_mm_gun} mm/gün."
    )
    sonuc["azaltim"] = karbon.azaltim_onerileri(sonuc)
    return sonuc


def carbon_node(state: AgentState) -> AgentState:
    """LangGraph adaptoru: serbest metinden karbon envanteri kurar."""
    profile = state.get("farm_profile") or {}
    parcel = profile.get("parcel") or {}
    lat, lon = parcel.get("lat"), parcel.get("lon")
    alan = parcel.get("alan_m2")

    if lat is None or lon is None or not alan:
        return {"result": {
            "agent": "carbon",
            "message": "Karbon ayak izi için önce parsel konumunu ve alanını girin.",
            "data": {},
        }}

    # Urun once serbest metinden aranir (sulama ajaninin ayni cikarimi), yoksa
    # profildeki urun, o da yoksa bolgenin ilk hedef urunu.
    metinden = _detect_crops(state.get("query", "").lower())
    urun = (profile.get("urun") or metinden[0]).lower()
    try:
        sonuc = karbon_plani(lat, lon, urun, alan)
    except KcYok:
        return {"result": {
            "agent": "carbon",
            "message": f"{urun.capitalize()} için FAO-56 su tüketim katsayısı "
                       "tanımlı olmadığından sulama enerjisi hesaplanamıyor.",
            "data": {},
        }}
    except ET0Yok as exc:
        return {"result": {"agent": "carbon", "message": str(exc), "data": {}}}
    except Exception as exc:  # ag/servis hatasi - graf cokmesin
        return {"result": {
            "agent": "carbon",
            "message": f"Hava servisine ulaşılamadı, karbon hesabı yapılamadı ({exc}).",
            "data": {},
        }}

    satirlar = [
        f"- {k['ad']}: {k['kg_co2e']} kg CO2e" for k in sonuc["kalemler"]
    ]
    msg = (
        f"{urun.capitalize()} / {sonuc['dekar']} dekar, {sonuc['sezon_gun']} günlük sezon:\n"
        + "\n".join(satirlar)
        + f"\nToplam {sonuc['toplam_kg_co2e']} kg CO2e "
          f"({sonuc['dekar_basina_kg_co2e']} kg CO2e/dekar)\n"
        + sonuc["not"]
    )
    return {"result": {"agent": "carbon", "message": msg, "data": sonuc}}
