"""EfficientNetV2 PyTorch checkpoint -> ONNX FP32.

NEDEN ONNX: Render free tier 512 MB RAM. Torch install ~800 MB (CPU-only bile
~200 MB) kabi patlatir. onnxruntime (~50 MB dep) + FP32 model (77 MB) ile
ayni model 512 MB'da rahat calisir (olculdu: ~150 MB peak).

NEDEN QUANTIZE DEGIL:
- Int8 dinamik quantize denendi: 20 orneklem field_benchmark'ta 10 puan
  dogruluk kaybettirdi (torch 80% -> onnx int8 70%). 3 puan tavani asildi.
- FP16 denendi: efficientnetv2'nin Cast operatorlerinde sema hatasi verdi
  (bilinen onnxconverter-common issue). keep_io_types=True/False farksiz.
- Kalibrasyon setli statik quantize dogruluk kayipsiz olabilir ama
  kalibrasyon veri seti hazirligi ek is. FP32 ~130 MB imaj artisi kabul
  edilebilir; MVP icin en dogru sagalama yolu.

TEK KEZ CALISIR (gelistirici makinesi). Ciktisi `models/disease/*.onnx`
depoya girer, torch runtime'da hic yok.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

BURADA = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BURADA))

from models.disease.classifier import IMG_SIZE, MODEL_NAME, load_labels


CKPT = BURADA / "models" / "disease" / "efficientnetv2_plant.pt"
ONNX_OUT = BURADA / "models" / "disease" / "efficientnetv2_plant.onnx"

# 90 MB tavan. FP32 model ~77 MB. Render imajinda 130 MB'lik artis kabul
# edilebilir (12 GB image limit); RAM peak ~150 MB (512 MB'in %30'u).
BOYUT_TAVANI = 90 * 1024 * 1024


def torch_export() -> None:
    """PyTorch checkpoint -> ONNX FP32."""
    import timm
    import torch

    labels = load_labels()
    n = len(labels)
    print(f"[1/2] Model kuruluyor: {MODEL_NAME}, num_classes={n}")

    model = timm.create_model(MODEL_NAME, pretrained=False, num_classes=n)
    state = torch.load(CKPT, map_location="cpu", weights_only=False)
    model.load_state_dict(state.get("model", state))
    model.eval()

    dummy = torch.randn(1, 3, IMG_SIZE, IMG_SIZE)
    print(f"[1/2] ONNX disa aktariliyor: {ONNX_OUT.name}")
    torch.onnx.export(
        model,
        (dummy,),
        str(ONNX_OUT),
        input_names=["girdi"],
        output_names=["cikti"],
        opset_version=17,
        dynamic_axes={"girdi": {0: "batch"}, "cikti": {0: "batch"}},
    )
    boyut = ONNX_OUT.stat().st_size
    boyut_mb = boyut / (1024 * 1024)
    print(f"[1/2] Boyut: {boyut_mb:.1f} MB")
    if boyut > BOYUT_TAVANI:
        raise SystemExit(
            f"HATA: ONNX model {boyut_mb:.1f} MB, tavan {BOYUT_TAVANI/(1024*1024):.0f} MB")


def sanity_check() -> None:
    """ONNX modelin gecerli oldugunu ve rasgele girdiye 45-boyutlu cikis
    verdigini dogrula."""
    import numpy as np
    import onnxruntime as ort

    print("[2/2] Model yukleme + rasgele girdi testi")
    sess = ort.InferenceSession(str(ONNX_OUT), providers=["CPUExecutionProvider"])
    girdi = sess.get_inputs()[0]
    cikti = sess.get_outputs()[0]
    print(f"       Girdi: {girdi.name} {girdi.shape} {girdi.type}")
    print(f"       Cikti: {cikti.name} {cikti.shape} {cikti.type}")

    x = np.random.randn(1, 3, IMG_SIZE, IMG_SIZE).astype(np.float32)
    y = sess.run([cikti.name], {girdi.name: x})[0]
    print(f"       Rasgele girdi -> cikti sekli: {y.shape}")
    n = len(load_labels())
    if y.shape != (1, n):
        raise SystemExit(f"HATA: beklenen (1,{n}) sekilli cikti, gelen {y.shape}")
    print("       Yapi kontrolu tamam.")


def main() -> None:
    if not CKPT.exists():
        raise SystemExit(f"HATA: checkpoint yok: {CKPT}")

    torch_export()
    sanity_check()

    # Onceki denemelerden kalan int8/fp16 varsa temizle
    for ad in ("efficientnetv2_plant.int8.onnx", "efficientnetv2_plant.fp16.onnx"):
        eski = BURADA / "models" / "disease" / ad
        if eski.exists():
            eski.unlink()
            print(f"[cleanup] {ad} silindi (dogruluk/sema nedeniyle terkedildi)")

    print("\nTAMAM. Ciktisi:", ONNX_OUT)
    print("Sonraki adim: classifier_onnx.py ile bu dosyayi cikarim icin kullan.")


if __name__ == "__main__":
    main()
