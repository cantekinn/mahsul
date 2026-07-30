"""Niyet yonlendirici: serbest metinden hangi uzmanin cevaplayacagini bulur.

NEDEN ORCHESTRATOR'DAN AYRILDI
Bu mantik `agents/orchestrator.py` icindeydi, o modul de ilk satirinda
`from langgraph.graph import ...` yapiyor. Yonlendirmenin kendisi ise saf
karakter isi: sozluk arama + Turkce/ASCII katlama, tek bir dis bagimliligi
yok. Langgraph kaba girmedigi icin (gerekce Dockerfile'daki agents/ COPY
blogunda) yonlendirici de canliya cikamiyordu; oysa "ciftci ne yazarsa yazsin
dogru karta gitsin" ozelligi grafik kutuphanesine degil bu 40 satira bagli.

Ayirinca tek kaynak korunuyor: orchestrator.py buradan import ediyor, HTTP
katmani da buradan import ediyor. Anahtar kelime listesi tek yerde duruyor,
iki kopyanin zamanla ayrisma ihtimali yok.
"""
from __future__ import annotations

# Niyet -> anahtar kelimeler. Anahtarlar ASCII yazilir; normalize() sorgudaki
# Turkce karakterleri ASCII'ye katladigi icin "zararlı böcek" gibi girisler de
# eslesir.
#
# SIRA ONEMLI: sozluk ilk eslesende durur. "hastalik" once bakilir cunku
# "hastalikli urun" yazan kullanici urun onerisi degil teshis istiyor.
INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "diagnosis": ("hastalik", "yaprak", "leke", "teshis", "curume", "kuruma"),
    "carbon": ("karbon", "ayak izi", "emisyon", "sera gazi"),
    "irrigation": ("sula", "su ", "sulama", "damla", "kac litre"),
    "climate_risk": ("don", "kurak", "risk", "hava", "sicaklik", "zarar gor"),
    "pest": ("bocek", "zararli", "haser", "kurt", "guve"),
    "crop_reco": ("ne ek", "urun", "oneri", "tavsiye", "ekim", "ne yetis"),
}

# Niyetin kullaniciya gosterilecek adi ve hangi sekmeye ait oldugu.
# Sekme adi arayuzun `Gorunum` tipiyle ayni yazilir; yanit "bunu su sekmede
# gorebilirsin" diyebilsin diye.
INTENT_TR: dict[str, tuple[str, str]] = {
    "diagnosis": ("Hastalık teşhisi", "teshis"),
    "carbon": ("Karbon ayak izi", "tarla"),
    "irrigation": ("Sulama planı", "tarla"),
    "climate_risk": ("İklim riski", "tarla"),
    "pest": ("Zararlı takvimi", "tarla"),
    "crop_reco": ("Ürün önerisi", "harita"),
    "advisor": ("Genel danışman", "tarla"),
}

# Turkce -> ASCII katlama. 'İ' ve 'I' ikisi de 'i'ye katlanir: kullanici
# "İklim" da yazabilir "iklim" de, ikisi de ayni anahtarla eslesmeli.
_TR_FOLD = str.maketrans("çğıiöşüÇĞİIÖŞÜ", "cgiiosucgiiosu")


def normalize(text: str) -> str:
    """Sorguyu anahtar kelime karsilastirmasina hazirlar (ASCII, kucuk harf)."""
    return text.translate(_TR_FOLD).lower()


def route(query: str, *, has_image: bool = False) -> str:
    """Sorgudan niyeti cikarir.

    Fotograf varsa metne hic bakilmaz: kullanici yaprak fotografi yukladiysa
    ne yazarsa yazsin teshis istiyordur.
    Hicbir anahtar kelime tutmazsa 'advisor' doner (genel danisman), cunku
    "anlamadim" demek yerine elde olan bilgiyle cevap vermek yeglenir.
    """
    if has_image:
        return "diagnosis"
    q = normalize(query)
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "advisor"
