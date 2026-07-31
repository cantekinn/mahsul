"""Sezon gunlugu: kayitli olaylardan ne HESAPLANABILIR.

Bu modul, hafizanin cevabi gercekten degistirdigi yerdir. Gunlugun kendisi
(ne zaman sulandi, ne zaman ilac atildi, ne teshis kondu) arayuzde tarayicida
durur; burada yapilan is o tarihleri OLCULEN hava verisiyle birlestirip
tek basina hicbirinden cikmayan bir sayi uretmektir.

NEDEN TARAYICIDA SAKLANIYOR, SUNUCUDA DEGIL
memory/farm_profile_db.py bir SQLite tablosu tanimliyor ve yerelde calisiyor,
ama canli barinak (Render ucretsiz katman) diski kalici degil: kap her
uyandiginda dosya sistemi sifirlaniyor. Sunucuya yazilan gunluk, ciftci
ertesi gun geldiginde YOK olurdu; "hatirliyorum" diyip hatirlamayan bir
hafiza, hic hafiza olmamasindan kotudur. Bu yuzden kayit tarayicida,
HESAP sunucuda.

BU MODUL HAVA VERISI CEKMEZ. Girdi olarak gun gun ET0 ve yagis dizisi alir
(bkz. data/open_meteo.get_gunluk_su_serisi). Boylece test edilebilir: ayni
diziyi elle verip beklenen toplami elle carpip karsilastirabiliyoruz.
"""
from __future__ import annotations

from datetime import date

from knowledge import fao56


class GunlukVeriYok(Exception):
    """Hesap icin gereken gun araligi elde yok.

    fao56.KcYok ve knowledge.besin.BesinVeriYok ile ayni sebeple ayri bir tip:
    eksik veriyi sessizce sifir sayip "acik yok" demek, ciftciye sulamayi
    atlatirdi. Eksikse hesap YAPILMAZ, yapilmadigi soylenir.
    """


# Sulama gununun KENDISI hesaba katilmaz, ertesi gunden baslanir.
# Gerekce: o gun toprak zaten islanmistir; sulanan gunun ET0'ini acik olarak
# saymak, ciftciyi suladigi gun bile "eksik su verdin" diye uyarirdi. Kural
# tek yonde muhafazakar: acigi OLDUGUNDAN BUYUK gostermemeyi secer.
def birikmis_acik(
    tarih: list[str],
    et0: list[float],
    yagis: list[float],
    son_sulama: date,
    urun: str,
    asama: str = "mid",
    bugun: date | None = None,
) -> dict:
    """Son sulamadan bu yana biriken net su acigi.

    Hesap, gun gun:
        ETc_i          = ET0_i x Kc(urun, asama)
        etkili_yagis_i = 0.80 x yagis_i          (fao56.effective_rainfall_daily)
        acik           = toplam(ETc_i) - toplam(etkili_yagis_i),  alt sinir 0

    Etkili yagis orani gunluk pencerede zaten fao56'da tanimli; burada ikinci
    bir katsayi uydurulmuyor, o fonksiyon cagriliyor.

    1 mm = 1 litre/m2 oldugundan litre cevrimi carpmadan ibarettir; dekar
    (1000 m2) icin 1 mm = 1000 litre.

    Donen:
      gecen_gun        : sulamadan sonra hesaba giren gun sayisi
      etc_mm           : o gunlerin toplam bitki su tuketimi
      yagis_mm         : ayni gunlerin toplam OLCULEN yagisi (ham)
      etkili_yagis_mm  : bunun bitkiye ulasan kismi
      acik_mm          : net acik (>= 0)
      litre_dekar      : acigin dekar basina litre karsiligi
      kc               : kullanilan katsayi

    Firlatir:
      fao56.KcYok      : urun FAO-56 Tablo 12'de yoksa
      GunlukVeriYok    : sulama tarihinden sonra hic olculmus gun yoksa
    """
    kc = fao56.crop_coefficient(urun, asama)
    bugun = bugun or date.today()
    if son_sulama > bugun:
        raise GunlukVeriYok("son sulama tarihi gelecekte")

    etc_top = 0.0
    yagis_top = 0.0
    etkili_top = 0.0
    gun = 0
    for t, e, y in zip(tarih, et0, yagis):
        g = date.fromisoformat(t)
        if g <= son_sulama or g > bugun:
            continue
        etc_top += e * kc
        yagis_top += y
        etkili_top += fao56.effective_rainfall_daily(y)
        gun += 1

    if gun == 0:
        # Iki ayri sebep ayni sonucu verir ve ikisi de "0 mm acik" DEGILDIR:
        # ya sulama bugun yapildi (henuz acik birikmedi), ya da sulama tarihi
        # havanin olculdugu pencerenin (60 gun) disinda kaldi. Cagiran taraf
        # ayrimi tarihe bakarak yapar; burada onemli olan sifir dondurmemek.
        raise GunlukVeriYok("sulamadan sonra olculmus gun yok")

    # Litre, GOSTERILEN acik_mm'den turetilir, ham degerden degil. Aksi halde
    # ekranda "46.1 mm" ve "46 104 litre" yan yana durur; ciftci 46.1 x 1000
    # yapip 46 100 bulur ve hangisinin dogru oldugunu soramaz. Iki sayi ayni
    # sayi olmali.
    acik = round(max(0.0, etc_top - etkili_top), 1)
    return {
        "gecen_gun": gun,
        "kc": round(kc, 2),
        "etc_mm": round(etc_top, 1),
        "yagis_mm": round(yagis_top, 1),
        "etkili_yagis_mm": round(etkili_top, 1),
        "acik_mm": acik,
        "litre_dekar": round(acik * 1000.0, 0),
    }


def acik_yorumu(sonuc: dict, gunluk_etc_mm: float) -> str:
    """Birikmis acigi "kac gunluk tuketime denk" diline cevirir.

    Ciftci icin 39 mm soyut bir sayidir; "gunde 7.1 mm tuketen domates icin
    5.5 gunluk su" somuttur. Bolme disinda bir sey yapilmaz, yeni bir esik
    ya da tavsiye uydurulmaz.
    """
    if gunluk_etc_mm <= 0:
        raise GunlukVeriYok("gunluk ETc sifir ya da negatif")
    gun_karsiligi = sonuc["acik_mm"] / gunluk_etc_mm
    return (
        f"{sonuc['gecen_gun']} günde biriken {sonuc['acik_mm']} mm açık, "
        f"bu ürünün {gun_karsiligi:.1f} günlük tüketimine denk."
    )


def tekrar_teshis(kayitlar: list[dict], etiket: str, bugun: date | None = None) -> dict | None:
    """Ayni hastalik daha once teshis edildi mi, arada ilaclama var mi.

    kayitlar: [{"tarih": "2026-07-10", "tur": "teshis", "etiket": "..."} ...]
              "tur" degerleri: teshis | ilac | sulama | gubre | ekim | hasat

    Bu bir tahmin degil, KAYIT OKUMASIDIR: "ayni etiket 21 gun once de
    yazilmis ve arada bir ilaclama kaydi var" cumlesi gunluge bakan herkesin
    goreceginin aynisidir. Ilacin ise yarayip yaramadigi hakkinda hukum
    VERILMEZ; iki olgu yan yana konur, yorumu ciftci yapar.

    Donen (tekrar yoksa None):
      onceki_tarih : ayni etiketin en son gorildigi gun
      gecen_gun    : aradan gecen gun
      ilac_sayisi  : iki teshis arasinda kayitli ilaclama sayisi
      ilac_son     : bu araliktaki en son ilaclama tarihi (yoksa None)
    """
    bugun = bugun or date.today()
    oncekiler = [
        date.fromisoformat(k["tarih"])
        for k in kayitlar
        if k.get("tur") == "teshis" and k.get("etiket") == etiket and k.get("tarih")
    ]
    oncekiler = [g for g in oncekiler if g < bugun]
    if not oncekiler:
        return None
    onceki = max(oncekiler)

    ilaclar = [
        date.fromisoformat(k["tarih"])
        for k in kayitlar
        if k.get("tur") == "ilac" and k.get("tarih")
    ]
    aradakiler = [g for g in ilaclar if onceki <= g <= bugun]
    return {
        "onceki_tarih": onceki.isoformat(),
        "gecen_gun": (bugun - onceki).days,
        "ilac_sayisi": len(aradakiler),
        "ilac_son": max(aradakiler).isoformat() if aradakiler else None,
    }
