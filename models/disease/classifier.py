"""Hastalik teshisi (CNN) cikarim + Grad-CAM (Sprint 2).

Yaklasim (memory'deki karar):
  EfficientNetV2-S transfer ogrenme (timm), yaprak fotografindan hastalik
  siniflandirma; aciklanabilirlik icin Grad-CAM isi haritasi.

Bu modul GBDT ile ayni deseni kullanir: agir bagimliliklar (torch/timm)
lazy import edilir; egitilmis agirlik (checkpoint) yoksa is_available()=False
doner ve teshis agent'i durumu dogrustan bildirir. Boylece proje torch
kurulmadan da calisir; model egitilince (train.py) otomatik devreye girer.
"""
from __future__ import annotations

import importlib.util
from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent
_CKPT = _DIR / "efficientnetv2_plant.pt"     # egitim ciktisi (train.py uretir)
_LABELS_FILE = _DIR / "labels.txt"

MODEL_NAME = "tf_efficientnetv2_s"
IMG_SIZE = 224  # egitimle ayni (train.py); CPU icin 384 yerine 224

# Egitim yoksa referans sinif listesi. Skala genisletme (2026-07): 45 sinif / 17 urun.
# PlantVillage 38 (narenciye dahil) + zeytin 3 + muz 4. Etiketler <urun>_<durum>,
# <urun> daima tek kelime (predict() urun grubunu ilk "_" ile ayirir).
# labels.txt (train.py ciktisi) varsa o esas alinir; bu liste yalnizca yedek.
DEFAULT_LABELS = list(  # LABEL_TR anahtarlarindan turetilir (asagida tanimli)
    ()
)

# Model etiketi (ic anahtar) -> kullaniciya gosterilecek okunakli Turkce ad
LABEL_TR = {
    # Domates
    "domates_saglikli": "Domates sağlıklı",
    "domates_bakteriyel_leke": "Domateste bakteriyel leke",
    "domates_erken_yaniklik": "Domateste erken yanıklık",
    "domates_gec_yaniklik": "Domateste geç yanıklık",
    "domates_yaprak_kufu": "Domateste yaprak küfü",
    "domates_septoria_leke": "Domateste septoria yaprak lekesi",
    "domates_orumcek_akari": "Domateste örümcek akarı",
    "domates_hedef_leke": "Domateste hedef leke",
    "domates_sari_yaprak_virusu": "Domateste sarı yaprak kıvrılma virüsü",
    "domates_mozaik_virusu": "Domateste mozaik virüsü",
    # Biber
    "biber_saglikli": "Biber sağlıklı",
    "biber_bakteriyel_leke": "Biberde bakteriyel leke",
    # Patates
    "patates_saglikli": "Patates sağlıklı",
    "patates_erken_yaniklik": "Patateste erken yanıklık",
    "patates_gec_yaniklik": "Patateste geç yanıklık",
    # Elma
    "elma_saglikli": "Elma sağlıklı",
    "elma_kara_leke": "Elmada kara leke (scab)",
    "elma_siyah_curukluk": "Elmada siyah çürüklük",
    "elma_sedir_pas": "Elmada sedir pası",
    # Uzum
    "uzum_saglikli": "Üzüm sağlıklı",
    "uzum_kara_curukluk": "Üzümde kara çürüklük",
    "uzum_esca": "Üzümde esca (kara ölçek)",
    "uzum_yaprak_yanikligi": "Üzümde yaprak yanıklığı",
    # Narenciye
    "narenciye_yesillenme": "Narenciyede yeşillenme (HLB)",
    # Seftali
    "seftali_saglikli": "Şeftali sağlıklı",
    "seftali_bakteriyel_leke": "Şeftalide bakteriyel leke",
    # Kiraz
    "kiraz_saglikli": "Kiraz sağlıklı",
    "kiraz_kulleme": "Kirazda külleme",
    # Cilek
    "cilek_saglikli": "Çilek sağlıklı",
    "cilek_yaprak_yanigi": "Çilekte yaprak yanığı",
    # Misir
    "misir_saglikli": "Mısır sağlıklı",
    "misir_gri_yaprak_lekesi": "Mısırda gri yaprak lekesi",
    "misir_yaygin_pas": "Mısırda yaygın pas",
    "misir_yaprak_yanikligi": "Mısırda yaprak yanıklığı",
    # Diger tek-sinifli urunler
    "yabanmersini_saglikli": "Yaban mersini sağlıklı",
    "ahududu_saglikli": "Ahududu sağlıklı",
    "soya_saglikli": "Soya sağlıklı",
    "kabak_kulleme": "Kabakta külleme",
    # Zeytin
    "zeytin_saglikli": "Zeytin sağlıklı",
    "zeytin_tavus_gozu": "Zeytinde tavus gözü lekesi",
    "zeytin_akar": "Zeytinde akar (gal akarı)",
    # Muz
    "muz_saglikli": "Muz sağlıklı",
    "muz_sigatoka": "Muzda Sigatoka yaprak lekesi",
    "muz_cordana": "Muzda Cordana yaprak lekesi",
    "muz_pestalotiopsis": "Muzda Pestalotiopsis lekesi",
}

DEFAULT_LABELS = list(LABEL_TR.keys())

# Ic urun anahtari -> okunakli ad (grup bazli "tespit edilen urun" gosterimi icin)
CROP_TR = {
    "domates": "Domates", "biber": "Biber", "patates": "Patates",
    "elma": "Elma", "uzum": "Üzüm", "narenciye": "Narenciye",
    "seftali": "Şeftali", "kiraz": "Kiraz", "cilek": "Çilek",
    "misir": "Mısır", "yabanmersini": "Yaban mersini", "ahududu": "Ahududu",
    "soya": "Soya", "kabak": "Kabak", "zeytin": "Zeytin", "muz": "Muz",
}


# Kademeli guven: lab-saha ucurumu yuzunden gercek tarla fotolarinda dogru sinif
# sik sik ILK sirada ama dusuk guvenle cikar. Ikili gecti/kaldi yerine 3 kademe:
#   kesin   -> top-1 yuksek ve rakibinden acik farkli: net teshis + tedavi
#   olasi   -> orta guven: "en olasi" teshis + tedavi ama "kesin degil" uyarisi
#   belirsiz-> cok dusuk: teshis dayatma, net foto/belirti iste
_CONF_MIN = 0.55       # bu ustu: kesin
_CONF_PROBABLE = 0.30  # bu ustu (ama <0.55): olasi
_MARGIN_MIN = 0.10     # top-1 ile top-2 farki bu altindaysa kesin sayma (cekismeli)


def label_display(etiket: str) -> str:
    """Model etiketini kullaniciya gosterilecek okunakli Turkce ada cevirir."""
    return LABEL_TR.get(etiket, etiket.replace("_", " ").capitalize())


class DiseaseModelUnavailable(RuntimeError):
    """torch/timm veya egitilmis agirlik bulunamadi."""


def _has(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def is_available() -> bool:
    """Cikarim yapilabilir mi? (torch + timm + checkpoint)."""
    return _has("torch") and _has("timm") and _CKPT.exists()


def status() -> str:
    """Neden hazir/degil, insan-okur durum."""
    eksik = []
    if not _has("torch"):
        eksik.append("torch")
    if not _has("timm"):
        eksik.append("timm")
    if not _CKPT.exists():
        eksik.append(f"agirlik ({_CKPT.name})")
    return "hazir" if not eksik else "eksik: " + ", ".join(eksik)


def load_labels() -> list[str]:
    if _LABELS_FILE.exists():
        return [l.strip() for l in _LABELS_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]
    return DEFAULT_LABELS


@lru_cache(maxsize=1)
def _load_model():
    import timm
    import torch

    labels = load_labels()
    model = timm.create_model(MODEL_NAME, pretrained=False, num_classes=len(labels))
    state = torch.load(_CKPT, map_location="cpu")
    model.load_state_dict(state.get("model", state))
    model.eval()
    return model, labels


def _preprocess(image_path: str):
    """On-isleme: egitim-degerlendirme ile birebir (Resize -> CenterCrop).

    NOT: buyuk resize/kare-squash veya cok-gorunum TTA denendi ve gercek SAHA
    fotolarinda dogrulugu DUSURDU (saha %61.9 -> %54); model RandomResizedCrop(224)
    ile egitildigi icin en iyi cikarim bu sade on-islemeyle geliyor.
    """
    from PIL import Image
    from torchvision import transforms

    tf = transforms.Compose([
        transforms.Resize(IMG_SIZE),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    img = Image.open(image_path).convert("RGB")
    return tf(img).unsqueeze(0)


def predict(image_path: str, topk: int = 3) -> dict:
    """Yaprak fotografindan hastalik tahmini (once urun, sonra kademeli guven).

    Model 'diger' (hedef-disi/taninmayan yaprak) sinifiyla egitildigi icin
    narenciye/yabanci yaprak gorunce teshis DAYATMAZ; top-1 'diger' cikinca
    seviye='tanimsiz' doner (agent teshis/Grad-CAM gostermez). Ayrica 9 gercek
    sinif urun grubuna (domates/biber/patates) toplanip "tespit edilen urun"
    raporlanir ("once yapragi anla, sonra hastalik" mantigi).

    Donen: {etiket, guven, seviye, belirsiz, sebep, urun, urun_guven, topk[...]}
      seviye = kesin / olasi / belirsiz / tanimsiz
    """
    if not is_available():
        raise DiseaseModelUnavailable(status())

    import torch

    model, labels = _load_model()
    x = _preprocess(image_path)
    with torch.no_grad():
        probs = torch.softmax(model(x), dim=1)[0]
    k = min(topk, len(labels))
    conf, idx = torch.topk(probs, k)
    top = [{"etiket": labels[i], "guven": round(float(c), 3)} for c, i in zip(conf, idx)]

    # Urun grubu olasiligi (domates/biber/patates) - 'diger' ve _ olmayan haric
    crop_probs: dict[str, float] = {}
    for lbl, p in zip(labels, probs):
        if lbl == "diger" or "_" not in lbl:
            continue
        crop = lbl.split("_")[0]
        crop_probs[crop] = crop_probs.get(crop, 0.0) + float(p)
    urun = max(crop_probs, key=crop_probs.get) if crop_probs else None
    urun_guven = round(crop_probs.get(urun, 0.0), 3) if urun else 0.0

    top1 = top[0]["guven"]
    margin = top1 - (top[1]["guven"] if len(top) > 1 else 0.0)

    if top[0]["etiket"] == "diger":
        # model bu yapragi hedef urunlerden biri olarak tanimadi -> teshis yok
        seviye, sebep = "tanimsiz", "hedef_disi"
    elif top1 >= _CONF_MIN and margin >= _MARGIN_MIN:
        seviye, sebep = "kesin", None
    elif top1 >= _CONF_PROBABLE:
        seviye = "olasi"
        sebep = "cekismeli" if margin < _MARGIN_MIN else "orta_guven"
    else:
        seviye, sebep = "belirsiz", "guven_dusuk"

    return {"etiket": top[0]["etiket"], "guven": top1, "margin": round(margin, 3),
            "seviye": seviye, "belirsiz": seviye == "belirsiz", "sebep": sebep,
            "urun": urun, "urun_guven": urun_guven, "topk": top}


def gradcam(image_path: str, out_path: str) -> str:
    """Grad-CAM isi haritasini goruntu uzerine bindirip kaydeder.

    Son evrisim katmani (conv_head) hedeflenir; siniflandirmayi hangi bolgenin
    surukledigini gosterir (aciklanabilirlik). Donen: kaydedilen dosya yolu.
    """
    if not is_available():
        raise DiseaseModelUnavailable(status())

    import numpy as np
    import torch
    from PIL import Image

    model, labels = _load_model()
    x = _preprocess(image_path)

    activations, gradients = {}, {}
    target = model.conv_head  # timm EfficientNetV2 son evrisim

    def fwd_hook(_m, _i, out):
        activations["v"] = out.detach()

    def bwd_hook(_m, _gi, go):
        gradients["v"] = go[0].detach()

    h1 = target.register_forward_hook(fwd_hook)
    h2 = target.register_full_backward_hook(bwd_hook)
    try:
        logits = model(x)
        cls = int(logits.argmax(dim=1))
        model.zero_grad()
        logits[0, cls].backward()

        act = activations["v"][0]                       # [C,H,W]
        grad = gradients["v"][0]                         # [C,H,W]
        weights = grad.mean(dim=(1, 2))                  # GAP -> kanal agirligi
        cam = torch.relu((weights[:, None, None] * act).sum(0))
        cam = cam / (cam.max() + 1e-8)
        cam = cam.cpu().numpy()
    finally:
        h1.remove()
        h2.remove()

    # isi haritasini orijinal boyuta bindir
    base = Image.open(image_path).convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    heat = Image.fromarray(np.uint8(255 * cam)).resize((IMG_SIZE, IMG_SIZE))
    heat = heat.convert("L")
    heat_rgb = Image.merge("RGB", (heat, Image.new("L", heat.size), Image.new("L", heat.size)))
    overlay = Image.blend(base, heat_rgb, alpha=0.45)
    overlay.save(out_path)
    return out_path
