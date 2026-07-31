"""train_colab.ipynb'yi uretir (Google Colab ucretsiz GPU icin egitim notebook'u).

Notebook kendi kendine yeter (repoya bagimli degil): PlantVillage 38 sinifini
GitHub API ile, zeytin+muz'u Kaggle ile indirir, EfficientNetV2-S egitir ve
egitilmis agirlik + labels.txt'yi indirir. Bu script sadece gecerli .ipynb JSON'u
uretmek icindir; elle JSON kacisiyla ugrasmamak icin json.dump kullanir.

Calistirma:  py -m models.disease.build_colab_nb
Cikti:       models/disease/train_colab.ipynb
"""
from __future__ import annotations

import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent
OUT = _DIR / "train_colab.ipynb"


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "outputs": [], "source": text.splitlines(keepends=True)}


INTRO = """# Tarim Asistani - Hastalik Modeli Egitimi (Colab GPU)

45 sinif / 16 urun: PlantVillage 38 (narenciye dahil) + zeytin (3) + muz (4).
Ustune **PlantDoc gercek tarla fotograflari** eklenir; laboratuvar-saha ucurumunu
kapatan kisim budur ve egitimde 3 kat agirlik alir.

## Kullanim
1. Menu: **Runtime > Change runtime type > T4 GPU** sec.
2. Hucreleri sirayla calistir (**Runtime > Run all**).
3. Kaggle hucresinde `kaggle.json` yukle (Kaggle > Settings > Create Legacy API Key).
4. Son hucre `efficientnetv2_plant.pt` ve `labels.txt`'yi indirir.
5. Bu iki dosyayi repoda `models/disease/` altina koy; model devreye girer.

Not: Zeytin ve muz Kaggle'da; kaggle.json olmadan o iki urun atlanir (38 sinif kalir).
Egitim her epoch'ta `lab=` ve `saha=` dogrulugunu ayri basar; en iyi checkpoint
**saha** dogruluguna gore secilir (demo gercek fotografla yapilacak).
"""

SETUP = """# Kurulum ve GPU kontrolu
!pip -q install timm
import torch
print("GPU:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "YOK (CPU) - Runtime>T4 GPU sec")
"""

GH_AUTH = '''# GitHub API limiti (bir kere basimiza geldi, sinif kaybettik)
# Kimliksiz: 60 istek/saat. PlantVillage 38 istek yiyor, PlantDoc 1; toplam 39.
# Sinirda geziyoruz ve Colab IP'si PAYLASIMLI - baskasi kotayi yemisse sinif kaybederiz.
# Token girersen limit 5000/saat olur ve sorun tamamen biter.
#
# Token alma (30 saniye, ucretsiz):
#   github.com > Settings > Developer settings > Personal access tokens
#   > Tokens (classic) > Generate new token (classic)
#   > isim ver, sure sec, HICBIR KUTUYU ISARETLEME (public veri icin yetki gerekmez)
#   > Generate token > ghp_... ile baslayan metni kopyala
# Enter'a basip gecebilirsin; o zaman 60 limitiyle devam eder.
import getpass, json, urllib.error, urllib.request

_tok = getpass.getpass("GitHub token (bos birak = kimliksiz, 60/saat): ").strip()
GH_HEADERS = {"User-Agent": "agri-app"}
if _tok:
    GH_HEADERS["Authorization"] = "Bearer " + _tok

_req = urllib.request.Request("https://api.github.com/rate_limit", headers=GH_HEADERS)
try:
    _core = json.load(urllib.request.urlopen(_req, timeout=30))["resources"]["core"]
except urllib.error.HTTPError as _e:
    if _e.code == 401:
        raise RuntimeError(
            "Token gecersiz (401). Kopyalarken bir karakter eksik/fazla olabilir ya da "
            "token suresi dolmus olabilir. Hucreyi tekrar calistirip yeniden yapistir; "
            "vazgecersen bos birak (60/saat ile devam eder)."
        ) from None
    raise
print(f"GitHub API: kalan {_core['remaining']} / {_core['limit']} istek")

GEREKLI = 40  # PlantVillage 38 + PlantDoc 1 + bu kontrol 1
if _core["remaining"] < GEREKLI:
    raise RuntimeError(
        f"Kalan istek {_core['remaining']}, gereken {GEREKLI}. Token gir ya da "
        "limitin sifirlanmasini bekle. Devam edersen siniflar SESSIZCE eksik iner."
    )
print("Yeterli. Devam edebilirsin.")
'''

PV = '''# PlantVillage 38 sinifini indir (klasor basina 1 API istegi = 38 istek)
# GH_HEADERS bir onceki hucreden gelir; token girdiysen limit 5000/saat.
import json, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DATA = Path("/content/data/plantvillage")
API = "https://api.github.com/repos/spMohanty/PlantVillage-Dataset/contents/raw/color/"
TRAIN_PER_CLASS, VAL_PER_CLASS = 350, 70

CLASS_MAP = {CLASS_MAP_JSON}

def list_dir(pv):
    url = API + urllib.parse.quote(pv) + "?per_page=1000"
    req = urllib.request.Request(url, headers=GH_HEADERS)
    with urllib.request.urlopen(req, timeout=30) as fh:
        return [d for d in json.load(fh) if d["type"] == "file"]

def dl(url, dest, deneme=3):
    # Paralel indirmede tek tuk istek kopuyor; sessizce kaybetmemek icin tekrar dene.
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agri-app"})
            with urllib.request.urlopen(req, timeout=30) as fh:
                dest.write_bytes(fh.read())
            return True
        except Exception:
            if i == deneme - 1:
                return False
            time.sleep(1 + i)
    return False

total, kayip = 0, 0
for pv, key in CLASS_MAP.items():
    files = [f for f in list_dir(pv) if f["name"].lower().endswith((".jpg", ".jpeg", ".png"))]
    files.sort(key=lambda f: f["name"])
    take = files[: TRAIN_PER_CLASS + VAL_PER_CLASS]
    val_n = min(VAL_PER_CLASS, max(1, len(take) // 6))
    inen = 0
    for split, items in {"train": take[:-val_n], "val": take[-val_n:]}.items():
        out = DATA / split / key
        out.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=16) as ex:
            jobs = [ex.submit(dl, f["download_url"], out / f["name"]) for f in items]
            inen += sum(1 for j in as_completed(jobs) if j.result())
    total += inen
    kayip += len(take) - inen
    isaret = "" if inen == len(take) else f"  <-- {len(take) - inen} EKSIK"
    print(f"{key:26s} {inen}/{len(take)}{isaret}")
print("PlantVillage toplam:", total, "| inemeyen:", kayip)
'''

KAGGLE = '''# Zeytin + Muz (Kaggle). kaggle.json yukle; yoksa bu hucreyi atla (38 sinif kalir).
import os, shutil, subprocess, tempfile
from pathlib import Path
from google.colab import files

print("kaggle.json dosyasini sec (Kaggle > Account > Create New API Token):")
up = files.upload()
os.makedirs("/root/.kaggle", exist_ok=True)
shutil.move("kaggle.json", "/root/.kaggle/kaggle.json")
os.chmod("/root/.kaggle/kaggle.json", 0o600)
!pip -q install kaggle

DATA = Path("/content/data/plantvillage")
VAL_FRACTION = 0.15
IMG_EXT = (".jpg", ".jpeg", ".png")
DATASETS = [
    ("habibulbasher01644/olive-leaf-image-dataset", [
        (("aculus", "gall", "mite", "akar"), "zeytin_akar"),
        (("peacock", "spilocaea", "spot", "leke"), "zeytin_tavus_gozu"),
        (("healthy", "saglikli"), "zeytin_saglikli")]),
    ("shifatearman/bananalsd", [
        (("sigatoka",), "muz_sigatoka"),
        (("cordana",), "muz_cordana"),
        (("pestalotiopsis",), "muz_pestalotiopsis"),
        (("healthy", "saglikli"), "muz_saglikli")]),
]

def match(path, rules):
    low = str(path).lower().replace("\\\\", "/")
    for kws, label in rules:
        if any(k in low for k in kws):
            return label
    return None

grand = 0
for slug, rules in DATASETS:
    print("==", slug)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["kaggle", "datasets", "download", "-d", slug, "-p", tmp, "--unzip"], check=True)
        by = {}
        for p in Path(tmp).rglob("*"):
            if p.is_file() and p.suffix.lower() in IMG_EXT:
                lbl = match(p, rules)
                if lbl:
                    by.setdefault(lbl, []).append(p)
        for label, fl in by.items():
            fl = sorted(fl)
            n_val = max(1, int(len(fl) * VAL_FRACTION))
            for split, items in {"val": fl[:n_val], "train": fl[n_val:]}.items():
                out = DATA / split / label
                out.mkdir(parents=True, exist_ok=True)
                for i, src in enumerate(items):
                    shutil.copyfile(src, out / f"extra_{label}_{i}{src.suffix.lower()}")
                    grand += 1
            print(f"  {label:22s}: {len(fl)}")
print("Ek (zeytin+muz) toplam:", grand)
'''

PLANTDOC = '''# PlantDoc GERCEK TARLA fotograflari (lab-saha ucurumunu kapatir) - GitHub, kimlik gerekmez
# Bu hucre ATLANIRSA model laboratuvar fotosunda parlak, gercek tarlada zayif kalir.
# ONEMLI: GitHub API kimliksiz saatte 60 istek verir. PlantVillage hucresi 38 tanesini
# kullaniyor, o yuzden burada klasor basina istek ATMIYORUZ: tek "git tree" cagrisiyla
# tum repo dosya listesi aliniyor (1 istek). Indirmeler raw.githubusercontent'ten,
# onlar limite girmiyor.
import json, time, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DATA = Path("/content/data/plantvillage")
PD_REPO, PD_BRANCH = "pratikkayal/PlantDoc-Dataset", "master"
PD_RAW = f"https://raw.githubusercontent.com/{PD_REPO}/{PD_BRANCH}/"

PD_MAP = {
    "Apple leaf": "elma_saglikli",
    "Apple Scab Leaf": "elma_kara_leke",
    "Apple rust leaf": "elma_sedir_pas",
    "Bell_pepper leaf": "biber_saglikli",
    "Bell_pepper leaf spot": "biber_bakteriyel_leke",
    "Blueberry leaf": "yabanmersini_saglikli",
    "Cherry leaf": "kiraz_saglikli",
    "Corn Gray leaf spot": "misir_gri_yaprak_lekesi",
    "Corn leaf blight": "misir_yaprak_yanikligi",
    "Corn rust leaf": "misir_yaygin_pas",
    "Peach leaf": "seftali_saglikli",
    "Potato leaf early blight": "patates_erken_yaniklik",
    "Potato leaf late blight": "patates_gec_yaniklik",
    "Raspberry leaf": "ahududu_saglikli",
    "Soyabean leaf": "soya_saglikli",
    "Squash Powdery mildew leaf": "kabak_kulleme",
    "Strawberry leaf": "cilek_saglikli",
    "Tomato Early blight leaf": "domates_erken_yaniklik",
    "Tomato Septoria leaf spot": "domates_septoria_leke",
    "Tomato leaf": "domates_saglikli",
    "Tomato leaf bacterial spot": "domates_bakteriyel_leke",
    "Tomato leaf late blight": "domates_gec_yaniklik",
    "Tomato leaf mosaic virus": "domates_mozaik_virusu",
    "Tomato leaf yellow virus": "domates_sari_yaprak_virusu",
    "Tomato mold leaf": "domates_yaprak_kufu",
    "Tomato two spotted spider mites leaf": "domates_orumcek_akari",
    "grape leaf": "uzum_saglikli",
    "grape leaf black rot": "uzum_kara_curukluk",
}

def pd_dl(path, dest, deneme=3):
    # Tekrar deneme sart: ilk denemede ~%6 istek kopuyor ve sessizce kaybolurdu.
    url = PD_RAW + urllib.parse.quote(path)
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "agri-app"})
            with urllib.request.urlopen(req, timeout=30) as fh:
                dest.write_bytes(fh.read())
            return True
        except Exception:
            if i == deneme - 1:
                return False
            time.sleep(1 + i)
    return False

# 1 istek: tum repo agaci
url = f"https://api.github.com/repos/{PD_REPO}/git/trees/{PD_BRANCH}?recursive=1"
req = urllib.request.Request(url, headers=GH_HEADERS)
with urllib.request.urlopen(req, timeout=120) as fh:
    tree = json.load(fh)
if tree.get("truncated"):
    raise RuntimeError("PlantDoc agaci kirpildi - liste eksik, devam etme")

SPLIT_MAP = {"train": "train", "test": "val"}
buckets = defaultdict(list)
for node in tree["tree"]:
    if node["type"] != "blob":
        continue
    parts = node["path"].split("/")
    if len(parts) != 3 or not parts[2].lower().endswith((".jpg", ".jpeg", ".png")):
        continue
    pd_split, pd_class, name = parts
    if pd_split in SPLIT_MAP and pd_class in PD_MAP:
        buckets[(SPLIT_MAP[pd_split], PD_MAP[pd_class])].append((node["path"], name))

total = 0
for (our_split, key), items in sorted(buckets.items()):
    out = DATA / our_split / key
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=16) as ex:
        jobs = [ex.submit(pd_dl, p, out / ("plantdoc_" + n)) for p, n in items]
        got = sum(1 for j in as_completed(jobs) if j.result())
    total += got
    print(f"  {our_split:5s} {key:26s} {got}/{len(items)}")

# Sessiz kayip olmasin: eslenen her sinif gercekten geldi mi?
eksik = [c for c in PD_MAP if not any(k[1] == PD_MAP[c] for k in buckets)]
if eksik:
    print("UYARI - hic dosya gelmeyen sinif:", eksik)
print("PlantDoc saha fotografi eklendi:", total)
'''

TRAIN = '''# EfficientNetV2-S egitimi (transfer ogrenme, GPU)
# Saha (PlantDoc) fotograflari lab fotografindan cok daha az; FIELD_WEIGHT ile
# ornekleme agirligi verilir, yoksa model tarlayi ogrenmez.
import timm, torch
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms
from pathlib import Path

DATA = Path("/content/data/plantvillage")
IMG_SIZE, EPOCHS, BS, LR = 224, 12, 64, 3e-4
FIELD_WEIGHT = 3.0
device = "cuda" if torch.cuda.is_available() else "cpu"

train_tf = transforms.Compose([
    transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(), transforms.ColorJitter(0.2, 0.2, 0.2),
    transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
val_tf = transforms.Compose([
    transforms.Resize(IMG_SIZE), transforms.CenterCrop(IMG_SIZE),
    transforms.ToTensor(), transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])

train_ds = datasets.ImageFolder(DATA / "train", train_tf)
val_ds = datasets.ImageFolder(DATA / "val", val_tf)
Path("labels.txt").write_text("\\n".join(train_ds.classes), encoding="utf-8")
print(len(train_ds), "train,", len(val_ds), "val,", len(train_ds.classes), "sinif")

def is_field(path):
    return Path(path).name.startswith("plantdoc_")

w = [FIELD_WEIGHT if is_field(p) else 1.0 for p, _ in train_ds.samples]
n_field = sum(1 for p, _ in train_ds.samples if is_field(p))
print(f"saha (PlantDoc) egitim fotografi: {n_field}  (agirlik x{FIELD_WEIGHT})")
sampler = WeightedRandomSampler(w, num_samples=len(w), replacement=True)

# Val'i lab / saha diye ayir ki gercek tarla performansini ayri olcelim.
field_idx = [i for i, (p, _) in enumerate(val_ds.samples) if is_field(p)]
lab_idx = [i for i, (p, _) in enumerate(val_ds.samples) if not is_field(p)]
print(f"val: {len(lab_idx)} lab, {len(field_idx)} saha")

train_dl = DataLoader(train_ds, batch_size=BS, sampler=sampler, num_workers=2, pin_memory=True)
val_dl = DataLoader(val_ds, batch_size=BS, num_workers=2, pin_memory=True)

model = timm.create_model("tf_efficientnetv2_s", pretrained=True, num_classes=len(train_ds.classes)).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=EPOCHS)
crit = nn.CrossEntropyLoss(label_smoothing=0.1)
scaler = torch.cuda.amp.GradScaler()

best = (0.0, 0.0)
for ep in range(EPOCHS):
    model.train()
    for xb, yb in train_dl:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()
        with torch.cuda.amp.autocast():
            loss = crit(model(xb), yb)
        scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
    sched.step()
    model.eval(); ok = []
    with torch.no_grad():
        for xb, yb in val_dl:
            p = model(xb.to(device)).argmax(1).cpu()
            ok.extend((p == yb).tolist())
    acc = sum(ok) / max(len(ok), 1)
    lab_acc = sum(ok[i] for i in lab_idx) / max(len(lab_idx), 1)
    field_acc = sum(ok[i] for i in field_idx) / max(len(field_idx), 1)
    print(f"epoch {ep+1}/{EPOCHS}  val={acc:.4f}  lab={lab_acc:.4f}  saha={field_acc:.4f}", flush=True)
    # Saha dogrulugu once: demo gercek tarla fotografiyla yapilacak.
    if (field_acc, lab_acc) >= best:
        best = (field_acc, lab_acc)
        torch.save({"model": model.state_dict(), "classes": train_ds.classes}, "efficientnetv2_plant.pt")
print(f"Bitti. En iyi saha={best[0]:.4f}  lab={best[1]:.4f}")
'''

EXPORT = """# Egitilmis agirlik + etiketleri indir
from google.colab import files
files.download("efficientnetv2_plant.pt")
files.download("labels.txt")
print("Bu iki dosyayi repoda models/disease/ altina koy.")
"""


def main() -> None:
    from models.disease.download_plantvillage import CLASS_MAP
    pv_cell = PV.replace("{CLASS_MAP_JSON}", json.dumps(CLASS_MAP, ensure_ascii=False, indent=4))
    nb = {
        "cells": [
            md(INTRO), code(SETUP), code(GH_AUTH), code(pv_cell), code(PLANTDOC),
            code(KAGGLE), code(TRAIN), code(EXPORT),
        ],
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    OUT.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Yazildi: {OUT}  ({len(nb['cells'])} hucre)")


if __name__ == "__main__":
    main()
