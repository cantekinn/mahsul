"""Demo arayuzu: tarla tanimla -> toprak+iklim getir -> urun onerisi + profil kaydet.

Sprint 1. Konum girisi (koordinat) birincil; MEGSIS parsel geometrisi (Ozlem)
GeoJSON gelince merkez koordinat + alan uretir. Urun onerisi kural tabanli
motordan (Sila) gerceğe bagli. Profil SQLite hafizaya kaydedilir (Ozlem).

Calistirma:
    streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from core.schemas import ClimateData, FarmProfile, Parcel, SoilData
from data.open_meteo import get_climate
from data.parcel_files import load_parcels
from data.soilgrids import get_soil
from memory.farm_profile_db import (
    find_by_parcel,
    list_profiles,
    save_profile,
)
from models.crop_reco import recommend, gbdt_second_opinion, gbdt_available

# Antalya varsayilan (Serik ovasi - toprak verisi olan bir tarim koordinati)
DEFAULT_LAT, DEFAULT_LON = 37.05, 31.05


@st.cache_data(show_spinner="Toprak ve iklim verisi getiriliyor...")
def _fetch(lat: float, lon: float):
    """Koordinat icin toprak + iklim verisini getirir.

    Her kaynak bagimsiz cagrilir; biri (gecici sunucu hatasi vb.) basarisiz
    olursa digeri yine gelir ve uyari dondurulur. Boylece tek bir dis API
    kesintisi tum akisi dusurmez.
    """
    warnings: list[str] = []
    try:
        soil = get_soil(lat, lon)
    except Exception as exc:  # dis API sinir noktasi
        soil = SoilData()
        warnings.append(f"Toprak verisi alinamadi (SoilGrids): {exc}")
    try:
        climate = get_climate(lat, lon)
    except Exception as exc:
        climate = ClimateData()
        warnings.append(f"Iklim verisi alinamadi (Open-Meteo): {exc}")
    return soil, climate, warnings


st.set_page_config(page_title="Tarim Asistani", layout="centered")
st.title("Tarim Asistani")
st.caption("Kucuk ciftci icin cok agentli tarim danismani - demo (Sprint 1)")

with st.sidebar:
    st.header("Tarla Konumu")

    # Yerel MEGSIS parsel dosyalarindan dogrudan sec (asil kullanim yolu).
    dosya_parselleri = load_parcels()
    if dosya_parselleri:
        etiket_map = {k["etiket"]: k["parcel"] for k in dosya_parselleri}
        secim_dosya = st.selectbox(
            "Parsel dosyasindan sec", ["(sec)"] + list(etiket_map)
        )
        if secim_dosya != "(sec)" and st.button("Sec ve getir", type="primary"):
            parcel = etiket_map[secim_dosya]
            st.session_state["parcel"] = parcel.model_dump()
            soil, climate, warnings = _fetch(parcel.lat, parcel.lon)
            st.session_state["soil"] = soil.model_dump()
            st.session_state["climate"] = climate.model_dump()
            for w in warnings:
                st.warning(w)
        st.divider()

    kayitli = list_profiles()
    if kayitli:
        etiketler = {
            f"{p['il']}/{p['ilce']} ada {p['ada']} parsel {p['parsel']}": p
            for p in kayitli
        }
        secim = st.selectbox("Kayitli tarla yukle", ["(yeni)"] + list(etiketler))
        if secim != "(yeni)" and st.button("Yukle"):
            p = etiketler[secim]
            prof = find_by_parcel(p["il"], p["ada"], p["parsel"])
            if prof:
                st.session_state["parcel"] = prof.parcel.model_dump()
                # Kayitli profilde toprak/iklim yoksa (tohumlanan parsel) merkez
                # koordinattan canli getir; varsa kayittakini kullan.
                if prof.soil is None and prof.parcel.lat is not None:
                    soil, climate, warnings = _fetch(prof.parcel.lat, prof.parcel.lon)
                    st.session_state["soil"] = soil.model_dump()
                    st.session_state["climate"] = climate.model_dump()
                    for w in warnings:
                        st.warning(w)
                else:
                    st.session_state["soil"] = (prof.soil or SoilData()).model_dump()
                    st.session_state["climate"] = (prof.climate or ClimateData()).model_dump()

    st.divider()
    st.write("MEGSIS parsel girisi TKGM erisimi gerektirir; simdilik koordinat.")
    il = st.text_input("Il", value="Antalya")
    ilce = st.text_input("Ilce", value="Serik")
    ada = st.text_input("Ada", value="120")
    parsel = st.text_input("Parsel", value="7")
    lat = st.number_input("Enlem", value=DEFAULT_LAT, format="%.4f")
    lon = st.number_input("Boylam", value=DEFAULT_LON, format="%.4f")
    getir = st.button("Veriyi Getir", type="primary")

if getir:
    soil, climate, warnings = _fetch(lat, lon)
    st.session_state["soil"] = soil.model_dump()
    st.session_state["climate"] = climate.model_dump()
    st.session_state["parcel"] = Parcel(il=il, ilce=ilce, mahalle="", ada=ada, parsel=parsel, lat=lat, lon=lon).model_dump()
    for w in warnings:
        st.warning(w)

if "soil" in st.session_state:
    soil_d = st.session_state["soil"]
    climate_d = st.session_state["climate"]
    soil = SoilData(**soil_d)
    climate = ClimateData(**climate_d)

    parcel_d = st.session_state.get("parcel") or {}
    if parcel_d:
        p = Parcel(**parcel_d)
        st.subheader("Parsel")
        adres = f"{p.il} / {p.ilce} / {p.mahalle}".strip(" /")
        st.write(f"**Adres:** {adres}  |  **Ada/Parsel:** {p.ada}/{p.parsel}")
        satir = []
        if p.mevkii:
            satir.append(f"**Mevkii:** {p.mevkii}")
        if p.nitelik:
            satir.append(f"**Nitelik:** {p.nitelik}")
        if p.alan_m2:
            satir.append(f"**Alan:** {p.alan_m2:,.0f} m2")
        if p.lat is not None:
            satir.append(f"**Merkez:** {p.lat:.5f}, {p.lon:.5f}")
        if satir:
            st.write("  |  ".join(satir))

    st.subheader("Iklim ozeti (son ~1 yil)")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ort. sicaklik", f"{climate.temperature} C" if climate.temperature is not None else "-")
    c2.metric("Ort. nem", f"%{climate.humidity}" if climate.humidity is not None else "-")
    c3.metric("Yillik yagis", f"{climate.rainfall} mm" if climate.rainfall is not None else "-")

    st.subheader("Toprak (SoilGrids, 0-5 cm)")
    if soil.ph is None:
        st.info(
            "SoilGrids bu hucre icin toprak verisi dondurmedi (kiyi/kentsel/kapsam "
            "disi olabilir ya da servis gecici yanit vermedi). Sorun degil; oneriler "
            "asagida yalnizca iklim verisine gore hesaplandi. Toprak icin farkli bir "
            "tarim koordinati da deneyebilirsin."
        )
    else:
        s1, s2 = st.columns(2)
        s1.metric("pH", soil.ph)
        s1.metric("Azot (g/kg)", soil.nitrogen)
        s1.metric("Organik karbon (g/kg)", soil.organic_carbon)
        s2.metric("Kil %", soil.clay)
        s2.metric("Kum %", soil.sand)
        s2.metric("Silt %", soil.silt)

    st.subheader("Urun onerisi")
    if soil.ph is None and climate.temperature is None:
        st.info("Oneri icin en az toprak ya da iklim verisi gerekli. Veriyi tekrar getirin.")
        recos = []
    else:
        if soil.ph is None:
            st.caption("Not: Toprak verisi yok; skorlar yalnizca iklim (sicaklik/yagis) uzerinden.")
        recos = recommend(soil, climate, top_k=4)
    for r in recos:
        with st.expander(f"{r['ad']}  -  skor {r['skor']} ({r['uygunluk']})", expanded=False):
            st.write(f"**Sezon:** {r['sezon']}")
            st.write(r["not"])
            if r["faktorler"]:
                st.write("**Neden bu skor (faktor uyumu 0-1):**")
                st.table(r["faktorler"])

    # GBDT ikinci gorus (deneysel, destekleyici). Kural motoru birincil kalir.
    if recos and gbdt_available():
        with st.expander("Deneysel: GBDT ikinci gorus", expanded=False):
            st.caption(
                "Kaggle veri setinde egitilmis model. Hedef urunlerimizle sadece "
                "orange->narenciye, banana->muz ortusur; digerleri iklim benzeri "
                "olarak gosterilir. Karar birincil olarak yukaridaki kural "
                "motorundan gelir."
            )
            npk = None
            if st.checkbox("Toprak analizi N/P/K gir"):
                c1, c2, c3 = st.columns(3)
                npk = {
                    "N": c1.number_input("N", value=37.0, format="%.1f"),
                    "P": c2.number_input("P", value=51.0, format="%.1f"),
                    "K": c3.number_input("K", value=32.0, format="%.1f"),
                }
            op = gbdt_second_opinion(soil, climate, npk=npk)
            if op is None:
                st.info("Ikinci gorus icin en az pH ve sicaklik verisi gerekli.")
            else:
                if op["gosterge"]:
                    st.warning(op["not"])
                else:
                    st.caption(op["not"])
                for t in op["tahminler"]:
                    etiket = "bizim urun" if t["bizim_urun"] else "iklim benzeri"
                    st.write(f"- {t['ad']}  (olasilik {t['olasilik']}, {etiket})")

    if st.button("Bu tarlayi hafizaya kaydet"):
        parcel_d = st.session_state.get("parcel") or {}
        prof = FarmProfile(parcel=Parcel(**parcel_d), soil=soil, climate=climate)
        pid = save_profile(prof)
        st.success(f"Kaydedildi (id: {pid[:8]}...). Sonraki oturumda hatirlanacak.")

st.divider()
st.subheader("Soru sor")
st.caption("Diger agent'lar (sulama, teshis, iklim riski) sonraki sprintlerde gelecek.")
query = st.text_input("Orn: tarlama ne ekmeliyim?")
if query:
    from agents.orchestrator import build_graph

    profile = {
        "soil": st.session_state.get("soil"),
        "climate": st.session_state.get("climate"),
    }
    state = build_graph().invoke({"query": query, "farm_profile": profile})
    result = state.get("result", {})
    st.write(f"**Niyet:** {state.get('intent')}  |  **Agent:** {result.get('agent')}")
    st.write(result.get("message", ""))
