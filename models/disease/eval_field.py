"""Egitilmis modeli GERCEK TARLA fotograflariyla olcer (lab val'i degil).

Neden ayri script: lab val dogrulugu (%98+) yaniltici. Kullanici tarlada telefonla
cekiyor; asil sayi budur. Kaynak PlantDoc test split'i, GitHub'dan kimliksiz gelir.

ONEMLI - GitHub API kimliksiz saatte 60 istek verir. Klasor basina listeleme yapmak
limiti doldurup sinifleri SESSIZCE atlatir (bir kere basimiza geldi). Bu yuzden tek
"git tree ?recursive=1" cagrisi yapilir (1 istek); indirmeler raw.githubusercontent
uzerinden gider ve limite girmez.

DIKKAT - Colab egitiminde ayni PlantDoc test split'i val olarak kullaniliyor ve en
iyi checkpoint ona gore seciliyor. Yani buradaki sayi "dogrulama" sayisidir, tamamen
gorulmemis test degildir. Raporlarken boyle yaz.

Calistirma:
    py -m models.disease.eval_field            # gerekirse indirir, sonra olcer
    py -m models.disease.eval_field --indir    # sadece indir
"""
from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

_DIR = Path(__file__).resolve().parent
BENCH_ROOT = _DIR.parent.parent / "data" / "field_benchmark"

REPO, BRANCH = "pratikkayal/PlantDoc-Dataset", "master"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
TREE = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
SPLIT = "test"  # egitime girmeyen bolum (Colab'da val olarak kullaniliyor)
IMG_EXT = (".jpg", ".jpeg", ".png")

# PlantDoc sinif klasoru -> bizim 45 sinifli semamiz (build_colab_nb.py ile ayni)
CLASS_MAP = {
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


def _get_json(url: str, timeout: int = 120) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "agri-app"})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.load(fh)


# PlantDoc'ta URL'den turemis adlar var (orn. "IMG_1629.JPG?1507122477.jpg").
# Windows'ta \\ / : * ? " < > | yasaktir; temizlemezsek dosya yazilamaz.
_YASAK = '<>:"/\\|?*'


def _guvenli_ad(ad: str) -> str:
    return "".join("_" if ch in _YASAK else ch for ch in ad).strip(" .") or "foto.jpg"


def _download(path: str, dest: Path) -> str | None:
    """Indirir; basarili ise None, degilse hata metni doner."""
    try:
        req = urllib.request.Request(RAW + urllib.parse.quote(path),
                                     headers={"User-Agent": "agri-app"})
        with urllib.request.urlopen(req, timeout=30) as fh:
            veri = fh.read()
        dest.write_bytes(veri)
        return None
    except Exception as exc:
        return f"{path}: {exc}"


def indir() -> int:
    """PlantDoc test split'ini BENCH_ROOT/<etiket>/ altina ceker. Toplam dosya sayisi doner."""
    tree = _get_json(TREE)
    if tree.get("truncated"):
        raise RuntimeError("PlantDoc agaci kirpilmis - liste eksik, olcum guvenilmez")

    kova: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for node in tree["tree"]:
        if node["type"] != "blob":
            continue
        parts = node["path"].split("/")
        if len(parts) != 3 or not parts[2].lower().endswith(IMG_EXT):
            continue
        pd_split, pd_class, name = parts
        if pd_split == SPLIT and pd_class in CLASS_MAP:
            kova[CLASS_MAP[pd_class]].append((node["path"], name))

    # Bazi siniflar PlantDoc'un test bolumunde hic yok (orn. domates_orumcek_akari
    # yalnizca train'de). Bu hata degil; ama sessiz kalmasin, olcum kapsami disi kalir.
    eksik = sorted({CLASS_MAP[c] for c in CLASS_MAP} - set(kova))
    if eksik:
        print(f"  NOT - PlantDoc test'te bulunmayan sinif (olcum disi): {eksik}")

    toplam = 0
    for etiket, items in sorted(kova.items()):
        out = BENCH_ROOT / etiket
        out.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=16) as ex:
            jobs = [ex.submit(_download, p, out / _guvenli_ad(n)) for p, n in items]
            hatalar = [h for h in (j.result() for j in as_completed(jobs)) if h]
        if hatalar:
            raise RuntimeError(f"{etiket}: {len(hatalar)} dosya inmedi -> {hatalar[0]}")
        ok = len(items)
        toplam += ok
        print(f"  {etiket:26s} {ok}")
    print(f"Toplam {toplam} saha fotografi -> {BENCH_ROOT}")
    return toplam


def olc() -> None:
    from models.disease import classifier

    if not classifier.is_available():
        raise RuntimeError(f"Model hazir degil: {classifier.status()}")

    etiketler = set(classifier.load_labels())
    dosyalar = sorted(p for p in BENCH_ROOT.rglob("*") if p.suffix.lower() in IMG_EXT)
    if not dosyalar:
        raise RuntimeError(f"{BENCH_ROOT} bos - once --indir calistirin")

    sinif_ok = urun_ok = 0
    seviye_sayim: dict[str, int] = defaultdict(int)
    urun_bazli: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # dogru, toplam
    karisiklik: dict[tuple[str, str], int] = defaultdict(int)
    atlanan = 0

    for yol in dosyalar:
        gercek = yol.parent.name
        if gercek not in etiketler:
            atlanan += 1
            continue
        sonuc = classifier.predict(str(yol))
        tahmin = sonuc["etiket"]
        g_urun, t_urun = gercek.split("_")[0], tahmin.split("_")[0]

        seviye_sayim[sonuc["seviye"]] += 1
        urun_bazli[g_urun][1] += 1
        if tahmin == gercek:
            sinif_ok += 1
        if t_urun == g_urun:
            urun_ok += 1
            urun_bazli[g_urun][0] += 1
        else:
            karisiklik[(g_urun, t_urun)] += 1

    n = len(dosyalar) - atlanan
    print(f"\nSAHA OLCUMU  ({n} fotograf, PlantDoc test)")
    print(f"  sinif dogrulugu : {sinif_ok}/{n} = {sinif_ok / n:.1%}")
    print(f"  urun dogrulugu  : {urun_ok}/{n} = {urun_ok / n:.1%}")
    if atlanan:
        print(f"  atlanan (model bu etiketi bilmiyor): {atlanan}")

    print("\n  guven kademesi:")
    for sev in ("kesin", "olasi", "belirsiz", "tanimsiz"):
        if seviye_sayim.get(sev):
            print(f"    {sev:9s} {seviye_sayim[sev]:4d}  ({seviye_sayim[sev] / n:.1%})")

    print("\n  urun bazli dogru tespit:")
    for urun, (ok, top) in sorted(urun_bazli.items(), key=lambda kv: kv[1][0] / kv[1][1]):
        print(f"    {urun:14s} {ok:3d}/{top:3d} = {ok / top:5.1%}")

    print("\n  en sik urun karistirmasi:")
    for (g, t), c in sorted(karisiklik.items(), key=lambda kv: -kv[1])[:8]:
        print(f"    {g:14s} -> {t:14s} {c}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Modeli gercek tarla fotograflariyla olc")
    ap.add_argument("--indir", action="store_true", help="sadece veri indir, olcme")
    args = ap.parse_args()

    if args.indir or not BENCH_ROOT.exists():
        indir()
    if not args.indir:
        olc()


if __name__ == "__main__":
    main()
