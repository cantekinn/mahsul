"""ONNX modeline CAM (sinif etkinlik haritasi) icin gereken iki seyi ekler.

NEDEN GRAD-CAM DEGIL, DUZ CAM
Grafigin kuyrugu su sirada:
    Mul (1,1280,7,7) -> GlobalAveragePool -> Flatten -> Gemm(classifier.weight)
Bas kismi GAP + Linear oldugunda Grad-CAM agirliklari, siniflandirici
agirliklarinin H*W'ye bolunmus haline TAM ESITTIR (turev sabit cikar). Yani
geri yayilim yapmanin ek bir bilgisi yok; torch'u sirf ayni sayiyi uzun yoldan
bulmak icin imaja koymak gerekmiyor. Score-CAM'in yuzlerce ileri gecisi de
ayni sebeple gereksiz.

NEDEN CALISMA ZAMANINDA DEGIL, BIR KEZ BURADA
Ara katmani cikti yapmak icin protobuf'u acip yeniden yazmak gerekiyor. Bunu
sunucu acilisinda yapsaydik 80 MB'lik modeli Python tarafinda ikinci kez
bellege alirdik; Render'in 512 MB'lik kademesinde bu bosa harcanan ~160 MB
demek. Dosyayi bir kez yamalayip oyle yayinliyoruz.

NEDEN AGIRLIKLAR AYRI .npy
classifier.weight modelin ICINDE bir initializer; onnxruntime onu disari
vermez. Okumak icin `onnx` paketi (protobuf) gerekir ve o paket sadece bunun
icin canliya girmemeli. 45x1280 float32 = 230 KB'lik bir .npy ile ayni bilgi
`onnx` bagimliligi olmadan tasiniyor.

Calistirma:  py -m scripts.model_cam_ciktisi
Cikti:       models/disease/efficientnetv2_plant.onnx (yamali, boyut degismez)
             models/disease/cam_agirlik.npy
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_KOK = Path(__file__).resolve().parent.parent
_MODEL = _KOK / "models" / "disease" / "efficientnetv2_plant.onnx"
_AGIRLIK = _KOK / "models" / "disease" / "cam_agirlik.npy"

# Son evrisim blogunun aktivasyonu (GAP'in hemen ONCESI). Bu tensor secilir
# cunku GAP'ten sonrasi mekansal bilgiyi tamamen kaybeder.
OZELLIK_TENSOR = "/bn2/act/Mul_output_0"
AGIRLIK_ADI = "classifier.weight"


def main() -> int:
    import onnx
    from onnx import TensorProto, helper, numpy_helper

    if not _MODEL.exists():
        print(f"Model yok: {_MODEL}", file=sys.stderr)
        return 1

    onceki_boyut = _MODEL.stat().st_size
    model = onnx.load(str(_MODEL))
    g = model.graph

    adlar = {o.name for o in g.output}
    if OZELLIK_TENSOR in adlar:
        print(f"Zaten yamali: {OZELLIK_TENSOR} cikti listesinde.")
    else:
        uretilenler = {c for n in g.node for c in n.output}
        if OZELLIK_TENSOR not in uretilenler:
            print(f"Tensor bulunamadi: {OZELLIK_TENSOR}", file=sys.stderr)
            return 1
        # Sekli None birakiyoruz: girdi partisi dinamik, sabit sekil yazmak
        # farkli parti boyutlarinda dogrulama hatasi verirdi.
        g.output.append(
            helper.make_tensor_value_info(OZELLIK_TENSOR, TensorProto.FLOAT, None)
        )
        onnx.save(model, str(_MODEL))
        print(f"Cikti eklendi: {OZELLIK_TENSOR}")

    ilk = [i for i in g.initializer if i.name == AGIRLIK_ADI]
    if not ilk:
        print(f"Agirlik bulunamadi: {AGIRLIK_ADI}", file=sys.stderr)
        return 1
    w = numpy_helper.to_array(ilk[0]).astype(np.float32)
    np.save(_AGIRLIK, w)

    sonraki_boyut = _MODEL.stat().st_size
    print(f"Agirlik yazildi: {_AGIRLIK.name} sekil={w.shape} {_AGIRLIK.stat().st_size / 1e3:.0f} KB")
    print(f"Model boyutu: {onceki_boyut / 1e6:.1f} MB -> {sonraki_boyut / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
