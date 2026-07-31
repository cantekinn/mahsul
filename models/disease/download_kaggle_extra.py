"""Zeytin + Muz yaprak veri setlerini Kaggle'dan indirir (skala genisletme).

PlantVillage'de zeytin ve muz YOK. Akdeniz/Antalya bolgesine uygun bu iki urunu
Kaggle'daki acik veri setlerinden ekliyoruz:

  Zeytin: habibulbasher01644/olive-leaf-image-dataset
          3 sinif, ~3400 goruntu, Denizli/Turkiye'de toplanmis (bolgemize birebir).
          Healthy, Olive Peacock Spot (Spilocaea oleagina), Aculus Olearius (gal akari).
  Muz:    shifatearman/bananalsd
          4 sinif (Healthy, Sigatoka, Cordana, Pestalotiopsis), tarlada cekilmis.

Bu indirici mevcut data/plantvillage klasorunu SILMEZ; uzerine EKLER. Bu yuzden
once download_plantvillage (ve istege bagli download_plantdoc) calismis olmali.

Klasor adlari veri setleri arasinda degisebildigi icin sinif klasoru -> Turkce
etiket eslemesi SABIT ISIM yerine ANAHTAR KELIME ile yapilir (dosya yolu icinde
gecen kelimeye gore). Boylece kaynak klasor adi biraz farkli olsa da dogru eslesir.

On kosul: Kaggle API kurulu ve kimlik dogrulanmis olmali.
  Colab'da:  files.upload() ile kaggle.json yukle, ~/.kaggle/kaggle.json'a koy.
  Yerelde:   pip install kaggle; kaggle.json'u %USERPROFILE%\\.kaggle\\ altina koy.

Calistirma:  py -m models.disease.download_kaggle_extra
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

_DIR = Path(__file__).resolve().parent
DATA_ROOT = _DIR.parent.parent / "data" / "plantvillage"

VAL_FRACTION = 0.15  # her sinifin ~%15'i val'e
IMG_EXT = (".jpg", ".jpeg", ".png")

# (kaggle_slug, [(anahtar_kelimeler, turkce_etiket), ...])
# Anahtar kelimeler klasor yolunda (kucuk harf) aranir; ilk eslesen etikete gider.
DATASETS = [
    (
        "habibulbasher01644/olive-leaf-image-dataset",
        [
            (("aculus", "gall", "mite", "akar"), "zeytin_akar"),
            (("peacock", "spilocaea", "spot", "leke"), "zeytin_tavus_gozu"),
            (("healthy", "saglikli", "saglam"), "zeytin_saglikli"),
        ],
    ),
    (
        "shifatearman/bananalsd",
        [
            (("sigatoka",), "muz_sigatoka"),
            (("cordana",), "muz_cordana"),
            (("pestalotiopsis",), "muz_pestalotiopsis"),
            (("healthy", "saglikli"), "muz_saglikli"),
        ],
    ),
]


def _kaggle_download(slug: str, dest: Path) -> None:
    """Kaggle CLI ile veri setini indirip acar (dest altina)."""
    dest.mkdir(parents=True, exist_ok=True)
    cmd = ["kaggle", "datasets", "download", "-d", slug, "-p", str(dest), "--unzip"]
    subprocess.run(cmd, check=True)


def _match_label(path: Path, rules: list) -> str | None:
    """Dosya yolundaki klasor adlarina bakip Turkce etiketi bulur (anahtar kelime)."""
    low = str(path).lower().replace("\\", "/")
    for keywords, label in rules:
        if any(k in low for k in keywords):
            return label
    return None


def _place(images_by_label: dict[str, list[Path]]) -> int:
    """Etiket bazli goruntuleri train/val olarak data/plantvillage altina kopyalar."""
    total = 0
    for label, files in images_by_label.items():
        files = sorted(files)
        n_val = max(1, int(len(files) * VAL_FRACTION))
        splits = {"val": files[:n_val], "train": files[n_val:]}
        for split, items in splits.items():
            out = DATA_ROOT / split / label
            out.mkdir(parents=True, exist_ok=True)
            for i, src in enumerate(items):
                # cakismayi onlemek icin kaynak-etiket-index ile benzersiz ad
                dest = out / f"extra_{label}_{i}{src.suffix.lower()}"
                try:
                    shutil.copyfile(src, dest)
                    total += 1
                except Exception:
                    pass
        print(f"{label:26s}: {len(splits['train'])} train + {len(splits['val'])} val")
    return total


def main() -> None:
    if not (DATA_ROOT / "train").exists():
        raise RuntimeError(
            f"Once PlantVillage indirilmeli: {DATA_ROOT}/train yok. "
            "py -m models.disease.download_plantvillage calistirin."
        )

    grand = 0
    for slug, rules in DATASETS:
        print(f"\n== {slug} ==")
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            _kaggle_download(slug, tmpdir)
            images_by_label: dict[str, list[Path]] = {}
            for p in tmpdir.rglob("*"):
                if p.is_file() and p.suffix.lower() in IMG_EXT:
                    label = _match_label(p, rules)
                    if label:
                        images_by_label.setdefault(label, []).append(p)
            if not images_by_label:
                print("  UYARI: eslesme yok. Klasor yapisini kontrol et (anahtar kelimeler).")
            grand += _place(images_by_label)
    print(f"\nToplam {grand} ek goruntu (zeytin+muz) eklendi -> {DATA_ROOT}")


if __name__ == "__main__":
    main()
