"""Hastalik teshis cikarimi — ONNX runtime, torch YOK.

NEDEN AYRI DOSYA (classifier.py yaninda):
- classifier.py torch+timm gerekiyor, egitim/Grad-CAM icin tutulur ama
  canliya girmez (~800 MB dep). Bu dosya sadece onnxruntime (~50 MB dep)
  ve numpy + Pillow (zaten var) kullanir.
- Kademeli guven mantigi ve etiket haritasi classifier.py'den import edilir;
  tekrar yazilmaz. classifier.py'nin module-level import'lari torch'a
  DOKUNMAZ (torch tum torch cagrilari fonksiyon icinde lazy) — dogrulandi.

INPUT: image bytes (PNG/JPG/vb.). OUTPUT: predict() classifier.predict()
sozlesmesiyle AYNI dict (etiket, guven, seviye, urun, urun_guven, topk,
margin, sebep, belirsiz) + isi/kirpma (bkz. _cam).
"""
from __future__ import annotations

import io
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from models.disease.classifier import (
    _CONF_MIN, _CONF_PROBABLE, _MARGIN_MIN,
    IMG_SIZE, load_labels,
)

_DIR = Path(__file__).resolve().parent
_ONNX_PATH = _DIR / "efficientnetv2_plant.onnx"
# CAM icin siniflandirici agirliklari (45x1280). Modelin ICINDE initializer
# olarak duruyor ama onnxruntime initializer'lari disari vermiyor; sirf bunu
# okumak icin `onnx` (protobuf) paketini canliya sokmamak adina ayri .npy.
# Uretici: scripts/model_cam_ciktisi.py
_CAM_AGIRLIK_PATH = _DIR / "cam_agirlik.npy"
# Modele scripts/model_cam_ciktisi.py tarafindan eklenen ikinci cikti.
_OZELLIK_TENSOR = "/bn2/act/Mul_output_0"

# ImageNet normalizasyonu (train.py ile birebir ayni)
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class TeshisModelYok(RuntimeError):
    """ONNX model dosyasi veya onnxruntime bulunamadi."""


def is_available() -> bool:
    """Cikarim yapilabilir mi (dosya + onnxruntime)."""
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return _ONNX_PATH.exists()


def status() -> str:
    """Neden hazir/degil, insan-okur durum."""
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return "eksik: onnxruntime"
    if not _ONNX_PATH.exists():
        return f"eksik: {_ONNX_PATH.name}"
    return "hazir"


@lru_cache(maxsize=1)
def _session():
    """Modeli bir kez yukler (module-level cache). Ilk cagride ~1-2 sn."""
    import onnxruntime as ort

    if not _ONNX_PATH.exists():
        raise TeshisModelYok(f"Model dosyasi yok: {_ONNX_PATH}")

    # Ucretsiz kademede tek isci + tek intra-op thread; RAM/CPU koruma.
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1

    sess = ort.InferenceSession(
        str(_ONNX_PATH),
        sess_options=opts,
        providers=["CPUExecutionProvider"],
    )
    girdi_ad = sess.get_inputs()[0].name
    ciktilar = [o.name for o in sess.get_outputs()]
    # Isi haritasi ciktisi YAMALANMAMIS modellerde yok. Varligi burada bir kez
    # sorulur; her istekte kontrol etmek yerine None tasinir ve teshis isi
    # haritasi olmadan calismaya devam eder (eski model dosyasiyla da acilir).
    ozellik_ad = _OZELLIK_TENSOR if _OZELLIK_TENSOR in ciktilar else None
    return sess, girdi_ad, ciktilar[0], ozellik_ad


def _preprocess_bytes(img_bytes: bytes) -> tuple[np.ndarray, dict]:
    """Resim baytlarini modelin bekledigi (1,3,224,224) float32 tensore cevirir.

    train.py'nin _preprocess() ile birebir: kisa kenari IMG_SIZE'a esitle
    (aspect korunur), sonra IMG_SIZE x IMG_SIZE center crop, /255 normalize,
    ImageNet mean/std, HWC->CHW, batch axis.

    torchvision.Resize(IMG_SIZE): kisa kenari IMG_SIZE'a esitler (aspect korunur).
    PIL Image.resize aspect korumaz; ayni davranisi elle hesapliyoruz.

    IKINCI DONUS DEGERI kirpma dikdortgeni, ORIJINAL fotografin pikselinde.
    Model kareyi gorur, kullanici tam fotografi gorur; isi haritasini tam
    fotografin uzerine cizmek isiyi yanlis yere dusururdu. Hesabin burada
    yapilmasi onemli: kirpmanin kurali bu fonksiyonun kendisi, ikinci bir
    yerde tekrarlanirsa iki taraf sessizce ayrisir.
    """
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    w, h = img.size
    if w < h:
        yw, yh = IMG_SIZE, int(round(h * IMG_SIZE / w))
    else:
        yw, yh = int(round(w * IMG_SIZE / h)), IMG_SIZE
    olcek = yw / w  # yh / h ile ayni (aspect korundu)
    img = img.resize((yw, yh), Image.BILINEAR)
    l = (yw - IMG_SIZE) // 2
    t = (yh - IMG_SIZE) // 2
    img = img.crop((l, t, l + IMG_SIZE, t + IMG_SIZE))
    kirpma = {
        "x": round(l / olcek, 1),
        "y": round(t / olcek, 1),
        "boyut": round(IMG_SIZE / olcek, 1),
        "genislik": w,
        "yukseklik": h,
    }
    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = (arr - _MEAN) / _STD
    arr = arr.transpose(2, 0, 1)[None, ...]  # HWC -> NCHW
    return arr.astype(np.float32), kirpma


@lru_cache(maxsize=1)
def _cam_agirlik() -> np.ndarray | None:
    """Siniflandirici agirlik matrisi (45,1280) ya da dosya yoksa None."""
    if not _CAM_AGIRLIK_PATH.exists():
        return None
    return np.load(_CAM_AGIRLIK_PATH).astype(np.float32)


def _cam(ozellik: np.ndarray, sinif: int) -> list[list[float]] | None:
    """Sinif etkinlik haritasi: modelin karari icin hangi bolgeye baktigi.

    ozellik: (1,1280,7,7) GAP oncesi aktivasyon. sinif: satir indisi.

    MATEMATIK: bas kismi GAP + Linear oldugu icin
        logit[c] = ortalama_hw( toplam_k W[c,k] * A[k,h,w] ) + b[c]
    yani asagidaki carpim, logitin mekansal dagilimidir. Grad-CAM ayni sayiyi
    turevden bulur; bu mimaride turev sabit (W[c,k]/(H*W)) oldugu icin sonuc
    ayni haritadir, geri yayilim gerekmiyor.

    ReLU: negatif katkilar "bu sinifa KARSI kanit" demek. Onlari da boyamak
    "model buraya bakti" izlenimi verirdi, oysa tam tersi.
    """
    w = _cam_agirlik()
    if w is None or sinif >= w.shape[0]:
        return None
    a = ozellik[0]                              # (1280,H,W)
    harita = np.tensordot(w[sinif], a, axes=(0, 0))  # (H,W)
    harita = np.maximum(harita, 0.0)
    tepe = float(harita.max())
    if tepe <= 0.0:
        return None
    harita /= tepe
    return [[round(float(v), 3) for v in satir] for satir in harita]


def _softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def predict(image_bytes: bytes, topk: int = 3) -> dict:
    """Yaprak fotosundan hastalik tahmini. Sozlesme classifier.predict() ile ayni.

    Donen: {etiket, guven, margin, seviye, belirsiz, sebep,
            urun, urun_guven, topk[{etiket, guven}]}
      seviye = kesin / olasi / belirsiz / tanimsiz

    'tanimsiz': top-1 'diger' geldi (model bunu hedef urunlerden biri
    olarak tanimadi, teshis dayatilmaz).
    """
    if not is_available():
        raise TeshisModelYok(status())

    sess, girdi_ad, cikti_ad, ozellik_ad = _session()
    x, kirpma = _preprocess_bytes(image_bytes)
    istenen = [cikti_ad] if ozellik_ad is None else [cikti_ad, ozellik_ad]
    sonuc = sess.run(istenen, {girdi_ad: x})
    logits = sonuc[0][0]
    probs = _softmax(logits)

    labels = load_labels()
    k = min(topk, len(labels))
    idx_sorted = np.argsort(-probs)[:k]
    top = [{"etiket": labels[int(i)], "guven": round(float(probs[i]), 3)} for i in idx_sorted]

    # Urun grubu olasiligi (etiketin ilk "_" oncesinden). 'diger' ve _'siz
    # etiketler grup dagitimina girmez.
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
        seviye, sebep = "tanimsiz", "hedef_disi"
    elif top1 >= _CONF_MIN and margin >= _MARGIN_MIN:
        seviye, sebep = "kesin", None
    elif top1 >= _CONF_PROBABLE:
        seviye = "olasi"
        sebep = "cekismeli" if margin < _MARGIN_MIN else "orta_guven"
    else:
        seviye, sebep = "belirsiz", "guven_dusuk"

    # Isi haritasi TOP-1 sinif icin. Kullanicinin ekranda okudugu teshis o;
    # baska bir sinifin haritasini gostermek "model buraya bakip bunu dedi"
    # cumlesini yalanlardi.
    isi = _cam(sonuc[1], int(idx_sorted[0])) if ozellik_ad is not None else None

    return {
        "etiket": top[0]["etiket"],
        "guven": top1,
        "margin": round(margin, 3),
        "seviye": seviye,
        "belirsiz": seviye == "belirsiz",
        "sebep": sebep,
        "urun": urun,
        "urun_guven": urun_guven,
        "topk": top,
        "isi": isi,
        "kirpma": kirpma,
    }
