"""PlantVillage'in TAMAMINI (38 sinif / 14 urun) indirir (gercek egitim verisi).

Kaynak: spMohanty/PlantVillage-Dataset (GitHub, kamuya acik, kimlik gerektirmez).
Skala genisletme karari (2026-07): sadece domates/biber/patates yerine PlantVillage'in
14 urununun 38 sinifi cekilir. Boylece narenciye (Orange greening), elma, uzum, seftali,
kiraz, cilek, misir, soya, yaban mersini, ahududu, kabak da modele girer. Zeytin ve muz
PlantVillage'de YOK; onlar download_kaggle_extra.py ile ayrica eklenir.

Etiketler classifier.LABEL_TR ve treatments.yaml ile eslesen Turkce anahtarlara
donusturulur. Her etiket <urun>_<durum> formatinda ve <urun> TEK kelimedir
(predict() urun grubunu ilk "_" ile ayirir; yaban mersini -> "yabanmersini").

ImageFolder duzeni uretir:
    data/plantvillage/train/<turkce_sinif>/*.jpg
    data/plantvillage/val/<turkce_sinif>/*.jpg

Calistirma:  py -m models.disease.download_plantvillage
"""
from __future__ import annotations

import json
import shutil
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_DIR = Path(__file__).resolve().parent
DATA_ROOT = _DIR.parent.parent / "data" / "plantvillage"
API = "https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color/"

# PlantVillage sinif klasoru -> bizim Turkce etiketimiz (classifier/treatments ile ayni).
# 38 sinif / 14 urun. <urun> daima tek kelime (yabanmersini).
CLASS_MAP = {
    # Elma
    "Apple___healthy": "elma_saglikli",
    "Apple___Apple_scab": "elma_kara_leke",
    "Apple___Black_rot": "elma_siyah_curukluk",
    "Apple___Cedar_apple_rust": "elma_sedir_pas",
    # Yaban mersini
    "Blueberry___healthy": "yabanmersini_saglikli",
    # Kiraz
    "Cherry_(including_sour)___healthy": "kiraz_saglikli",
    "Cherry_(including_sour)___Powdery_mildew": "kiraz_kulleme",
    # Misir
    "Corn_(maize)___healthy": "misir_saglikli",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "misir_gri_yaprak_lekesi",
    "Corn_(maize)___Common_rust_": "misir_yaygin_pas",
    "Corn_(maize)___Northern_Leaf_Blight": "misir_yaprak_yanikligi",
    # Uzum
    "Grape___healthy": "uzum_saglikli",
    "Grape___Black_rot": "uzum_kara_curukluk",
    "Grape___Esca_(Black_Measles)": "uzum_esca",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "uzum_yaprak_yanikligi",
    # Narenciye
    "Orange___Haunglongbing_(Citrus_greening)": "narenciye_yesillenme",
    # Seftali
    "Peach___healthy": "seftali_saglikli",
    "Peach___Bacterial_spot": "seftali_bakteriyel_leke",
    # Biber
    "Pepper,_bell___healthy": "biber_saglikli",
    "Pepper,_bell___Bacterial_spot": "biber_bakteriyel_leke",
    # Patates
    "Potato___healthy": "patates_saglikli",
    "Potato___Early_blight": "patates_erken_yaniklik",
    "Potato___Late_blight": "patates_gec_yaniklik",
    # Ahududu
    "Raspberry___healthy": "ahududu_saglikli",
    # Soya
    "Soybean___healthy": "soya_saglikli",
    # Kabak
    "Squash___Powdery_mildew": "kabak_kulleme",
    # Cilek
    "Strawberry___healthy": "cilek_saglikli",
    "Strawberry___Leaf_scorch": "cilek_yaprak_yanigi",
    # Domates
    "Tomato___healthy": "domates_saglikli",
    "Tomato___Bacterial_spot": "domates_bakteriyel_leke",
    "Tomato___Early_blight": "domates_erken_yaniklik",
    "Tomato___Late_blight": "domates_gec_yaniklik",
    "Tomato___Leaf_Mold": "domates_yaprak_kufu",
    "Tomato___Septoria_leaf_spot": "domates_septoria_leke",
    "Tomato___Spider_mites Two-spotted_spider_mite": "domates_orumcek_akari",
    "Tomato___Target_Spot": "domates_hedef_leke",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "domates_sari_yaprak_virusu",
    "Tomato___Tomato_mosaic_virus": "domates_mozaik_virusu",
}

TRAIN_PER_CLASS = 300
VAL_PER_CLASS = 60


def _list_dir(pv_class: str) -> list[dict]:
    """Bir PlantVillage sinif klasorundeki dosyalari listeler (GitHub API)."""
    url = API + urllib.parse.quote(pv_class) + "?per_page=1000"
    req = urllib.request.Request(url, headers={"User-Agent": "agri-app"})
    with urllib.request.urlopen(req, timeout=30) as fh:
        return [d for d in json.load(fh) if d["type"] == "file"]


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agri-app"})
        with urllib.request.urlopen(req, timeout=30) as fh:
            dest.write_bytes(fh.read())
        return True
    except Exception:
        return False


def main() -> None:
    if DATA_ROOT.exists():
        shutil.rmtree(DATA_ROOT)  # eski sentetik test verisini temizle

    total = 0
    for pv_class, tr_key in CLASS_MAP.items():
        files = _list_dir(pv_class)
        files = [f for f in files if f["name"].lower().endswith((".jpg", ".jpeg", ".png"))]
        files.sort(key=lambda f: f["name"])
        take = files[: TRAIN_PER_CLASS + VAL_PER_CLASS]
        # az goruntulu siniflarda (ornek: patates saglikli=152) val her zaman pay alsin
        val_n = min(VAL_PER_CLASS, max(1, len(take) // 6))
        splits = {"train": take[: len(take) - val_n], "val": take[len(take) - val_n:]}

        for split, items in splits.items():
            out = DATA_ROOT / split / tr_key
            out.mkdir(parents=True, exist_ok=True)
            jobs = {}
            with ThreadPoolExecutor(max_workers=16) as ex:
                for f in items:
                    dest = out / f["name"]
                    jobs[ex.submit(_download, f["download_url"], dest)] = dest
                ok = sum(1 for fut in as_completed(jobs) if fut.result())
            total += ok
            print(f"{tr_key:26s} {split:5s}: {ok}/{len(items)}")
    print(f"Toplam {total} goruntu indirildi -> {DATA_ROOT}")


if __name__ == "__main__":
    main()
