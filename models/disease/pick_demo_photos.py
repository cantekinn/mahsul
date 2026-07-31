"""app/ornek_fotograflar/ icine GERCEK tarla fotograflari secer.

Neden gerekli: klasordeki eski dosyalar make_synth_data.py'nin urettigi CIZIMLERDI
(yesil elips + kahverengi daireler). Model onlara dogal olarak "belirsiz" diyor;
demo ve ekran goruntusu icin kullanilamazlar.

Kaynak: PlantDoc test bolumu (data/field_benchmark/), lisans CC BY 4.0 - atif sart,
KAYNAK.md dosyasi otomatik yaziliyor.

Secim politikasi (dürüst demo):
  - Her istenen etiket icin model DOGRU bilen fotograflar arasindan secer.
  - En yuksek guvenli olani DEGIL, dogru bilinenlerin ortancasini alir; boylece
    demo tipik davranisi gosterir, en iyi vakayi degil.
  - Ayrica model'in "belirsiz" dedigi 1 ornek de eklenir: kademeli guven sistemi
    calisirken gorunsun diye (yanlis teshis dayatmadigimizin kaniti).

Bu secim bir BASARI OLCUSU DEGILDIR; gercek sayi icin eval_field.py kullan.

Calistirma:  py -m models.disease.pick_demo_photos
"""
from __future__ import annotations

import shutil
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_ROOT = _DIR.parent.parent
BENCH = _ROOT / "data" / "field_benchmark"
ORNEK = _ROOT / "app" / "ornek_fotograflar"
IMG_EXT = (".jpg", ".jpeg", ".png")

# Demo'da gorunmesini istedigimiz etiket -> cikti dosya adi
ISTENEN = {
    "domates_saglikli": "domates_saglikli",
    "domates_gec_yaniklik": "domates_gec_yaniklik",
    "domates_septoria_leke": "domates_septoria_leke",
    "biber_bakteriyel_leke": "biber_bakteriyel_leke",
    "elma_kara_leke": "elma_kara_leke",
    "misir_yaygin_pas": "misir_yaygin_pas",
    "uzum_kara_curukluk": "uzum_kara_curukluk",
    "patates_gec_yaniklik": "patates_gec_yaniklik",
}

KAYNAK_METNI = """# Ornek fotograflarin kaynagi

Bu klasordeki fotograflar **PlantDoc** veri setinin test bolumunden alinmistir.

- Depo: https://github.com/pratikkayal/PlantDoc-Dataset
- Lisans: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Makale: Singh et al., "PlantDoc: A Dataset for Visual Plant Disease Detection", CoDS-COMAD 2020

Fotograflar gercek tarla kosullarinda cekilmistir (degisken isik, karisik arka plan,
coklu yaprak). Laboratuvar fotograflari yerine bunlar secildi cunku uygulamanin
gercek kullanim kosulunu temsil ediyorlar.

Secim, modelin tipik davranisini gostermek icindir; basari orani olcusu DEGILDIR.
Olculen deger icin: `py -m models.disease.eval_field`
"""


def _fotograflar(etiket: str) -> list[Path]:
    klasor = BENCH / etiket
    if not klasor.is_dir():
        return []
    return sorted(p for p in klasor.iterdir() if p.suffix.lower() in IMG_EXT)


def main() -> None:
    from models.disease import classifier

    if not BENCH.exists():
        raise RuntimeError(
            f"{BENCH} yok. Once: py -m models.disease.eval_field --indir"
        )
    if not classifier.is_available():
        raise RuntimeError(f"Model hazir degil: {classifier.status()}")

    bilinen = set(classifier.load_labels())
    ORNEK.mkdir(parents=True, exist_ok=True)

    # Onceki secimi temizle (ilk calistirmada bunlar sentetik cizimlerdi)
    silinen = 0
    for eski in ORNEK.iterdir():
        if eski.is_file() and eski.suffix.lower() in (*IMG_EXT, ".png"):
            eski.unlink()
            silinen += 1
    if silinen:
        print(f"  onceki {silinen} fotograf silindi, yeniden secilecek")

    secilen = 0
    belirsiz_aday: tuple[Path, str] | None = None

    for etiket, ad in ISTENEN.items():
        if etiket not in bilinen:
            print(f"  ATLANDI {etiket}: model bu etiketi bilmiyor")
            continue
        dogrular: list[tuple[float, Path]] = []
        for yol in _fotograflar(etiket):
            s = classifier.predict(str(yol))
            if s["etiket"] == etiket and s["seviye"] in ("kesin", "olasi"):
                dogrular.append((s["guven"], yol))
            elif belirsiz_aday is None and s["seviye"] == "belirsiz":
                belirsiz_aday = (yol, etiket)
        if not dogrular:
            print(f"  ATLANDI {etiket}: dogru bilinen fotograf yok")
            continue
        dogrular.sort()
        guven, kaynak = dogrular[len(dogrular) // 2]  # ortanca, en iyisi degil
        hedef = ORNEK / f"{ad}{kaynak.suffix.lower()}"
        shutil.copy2(kaynak, hedef)
        secilen += 1
        print(f"  {hedef.name:32s} guven={guven:.2f}  ({len(dogrular)} adaydan ortanca)")

    if belirsiz_aday:
        kaynak, etiket = belirsiz_aday
        hedef = ORNEK / f"belirsiz_ornek_{etiket}{kaynak.suffix.lower()}"
        shutil.copy2(kaynak, hedef)
        secilen += 1
        print(f"  {hedef.name:32s} (model 'belirsiz' diyor - kademeli guven demosu)")

    (ORNEK / "KAYNAK.md").write_text(KAYNAK_METNI, encoding="utf-8")
    print(f"\n{secilen} fotograf -> {ORNEK}")
    print("Atif dosyasi yazildi: KAYNAK.md (CC BY 4.0 geregi)")


if __name__ == "__main__":
    main()
