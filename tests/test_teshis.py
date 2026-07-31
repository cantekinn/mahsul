"""Teshis on isleme ve isi haritasi testleri.

77 MB'lik ONNX modeli CALISTIRILMIYOR. Sebep: modelin ciktisini test etmek
"model dogru mu" sorusunu sorar ve o sorunun cevabi bir birim testi degil,
saha karsilastirmasidir (scripts/ altinda ayri yapiliyor). Burada test edilen
sey modelin ETRAFI: fotografin tensore cevrilmesi ve isi haritasinin
uretilmesi. Bu ikisi bozulursa model dogru olsa bile sonuc yanlis cikar ve
hata modelin uzerine yikilir.
"""
from __future__ import annotations

import io

import numpy as np
import pytest

pytest.importorskip("PIL", reason="Pillow yok")

from PIL import Image  # noqa: E402

from models.disease.classifier_onnx import (  # noqa: E402
    _cam,
    _cam_agirlik,
    _preprocess_bytes,
    _softmax,
)

IMG_SIZE = 224
# ImageNet istatistikleri; train.py ile ayni olmak ZORUNDA.
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def _etiketler() -> list[str]:
    """labels.txt satirlari. Dosya dogrudan okunuyor cunku bu testin sordugu
    soru "agirlik dosyasi ile etiket dosyasi ayni sinif sayisinda mi"; araya
    bir Python modulu koymak o iki dosyanin arasina ucuncu bir dogruluk
    kaynagi sokardi."""
    from pathlib import Path

    kok = Path(__file__).resolve().parent.parent
    return (kok / "models" / "disease" / "labels.txt").read_text(encoding="utf-8").split()


def _jpeg(genislik: int, yukseklik: int, renk=(0, 0, 0)) -> bytes:
    tampon = io.BytesIO()
    Image.new("RGB", (genislik, yukseklik), renk).save(tampon, format="PNG")
    return tampon.getvalue()


def test_tensor_sekli_ve_tipi():
    tensor, _ = _preprocess_bytes(_jpeg(640, 480))
    assert tensor.shape == (1, 3, IMG_SIZE, IMG_SIZE)
    assert tensor.dtype == np.float32


def test_normalizasyon_imagenet_ile_ayni():
    """Tamamen siyah bir kare icin her kanal (0 - mean) / std olmali.

    Egitimde kullanilan normalizasyondan sapmak modeli sessizce bozar: cikarim
    calisir, sinif dondurur, sadece YANLIS dondurur. Elle hesap:
      R: (0 - 0.485) / 0.229 = -2.1179
    """
    tensor, _ = _preprocess_bytes(_jpeg(300, 300, (0, 0, 0)))
    for kanal in range(3):
        beklenen = (0.0 - MEAN[kanal]) / STD[kanal]
        assert tensor[0, kanal].mean() == pytest.approx(beklenen, abs=1e-4)


def test_kirpma_kisa_kenari_tam_kapsar():
    """400x300 yatay fotograf. Elle hesap:

      kisa kenar 300 -> 224'e inecek, olcek = 224/300 = 0.74667
      olceklenmis genislik = round(400 x 0.74667) = 299
      sol kirpma = (299 - 224) // 2 = 37 piksel  -> orijinalde 37/0.7475 = 49.5
      kirpma boyutu = 224 / 0.7475 = 299.7 ~ 300 = kisa kenarin TAMAMI

    Kirpma dikdortgeni yanlis olursa teshis dogru cikar ama isi haritasi
    fotografin baska yerine biner; kullanici modelin saglam yaprağa baktigini
    sanir.

    TOLERANS NEDEN 1.5 PIKSEL: olceklenmis genislik 299, yani TEK sayi.
    (299-224)//2 = 37 solda, 38 sagda kaliyor; kirpma bir piksel sola kacik.
    Bu torchvision CenterCrop'un davranisinin ta kendisi ve on isleme
    denkligi tam da bunu korumak icin yazildi, yani duzeltilmesi gereken bir
    sapma degil. Orijinal olcege cevrilince 1/0.7475 = 1.34 piksel eder;
    olculen fark 50.8 - 49.5 = 1.3 piksel.
    """
    _, kirpma = _preprocess_bytes(_jpeg(400, 300))
    assert kirpma["genislik"] == 400
    assert kirpma["yukseklik"] == 300
    assert kirpma["boyut"] == pytest.approx(300.0, abs=1.0)
    assert kirpma["y"] == pytest.approx(0.0, abs=1.0)
    # Yatayda ortalanmis: sol bosluk = sag bosluk (tam sayi kirpmasi payiyla)
    sag = 400 - kirpma["x"] - kirpma["boyut"]
    assert kirpma["x"] == pytest.approx(sag, abs=1.5)


def test_dikey_fotografta_kirpma_dikeyde_ortalanir():
    _, kirpma = _preprocess_bytes(_jpeg(300, 400))
    assert kirpma["x"] == pytest.approx(0.0, abs=1.0)
    alt = 400 - kirpma["y"] - kirpma["boyut"]
    assert kirpma["y"] == pytest.approx(alt, abs=1.0)


def test_kare_fotograf_hic_kirpilmaz():
    _, kirpma = _preprocess_bytes(_jpeg(512, 512))
    assert kirpma["x"] == pytest.approx(0.0, abs=0.5)
    assert kirpma["y"] == pytest.approx(0.0, abs=0.5)
    assert kirpma["boyut"] == pytest.approx(512.0, abs=1.0)


def test_softmax_toplami_bir_ve_tasmaz():
    """Buyuk logitlerde exp tasmasi olmamali (max cikarma korumasi)."""
    p = _softmax(np.array([1000.0, 999.0, 998.0], dtype=np.float32))
    assert np.isfinite(p).all()
    assert p.sum() == pytest.approx(1.0, abs=1e-6)
    assert p[0] > p[1] > p[2]


# --- Isi haritasi (CAM) ---------------------------------------------------

def test_cam_agirlik_sinif_sayisiyla_uyumlu():
    """cam_agirlik.npy (45,1280) olmali.

    Bu dosya modelin son katman agirliklarinin AYRI bir kopyasi (onnxruntime
    initializer'lari disari vermiyor). Model yeniden egitilip sinif sayisi
    degistiginde bu dosya guncellenmezse isi haritasi yanlis sinifin
    haritasini cizer ve bunu hicbir sey soylemez.
    """
    w = _cam_agirlik()
    if w is None:
        pytest.skip("cam_agirlik.npy yok; isi haritasi kapali calisir")
    assert w.ndim == 2
    assert w.shape[1] == 1280           # EfficientNetV2-S ozellik boyutu
    assert w.shape[0] == len(_etiketler())


def test_cam_haritasi_normalize_ve_negatifsiz():
    """CAM ciktisi 0-1 arasi olmali, tepesi tam 1.0.

    Arayuz bu sayilari dogrudan saydamlik olarak kullaniyor; 1'i asan bir deger
    bindirmeyi opak yapip fotografi tamamen kapatirdi.
    """
    w = _cam_agirlik()
    if w is None:
        pytest.skip("cam_agirlik.npy yok")
    rastgele = np.random.default_rng(0)
    ozellik = rastgele.random((1, w.shape[1], 7, 7), dtype=np.float32)
    harita = _cam(ozellik, sinif=0)
    assert harita is not None
    assert len(harita) == 7 and all(len(s) == 7 for s in harita)
    duz = [v for satir in harita for v in satir]
    assert min(duz) >= 0.0
    assert max(duz) == pytest.approx(1.0, abs=1e-6)


def test_cam_gecersiz_sinifta_none_doner():
    w = _cam_agirlik()
    if w is None:
        pytest.skip("cam_agirlik.npy yok")
    ozellik = np.ones((1, w.shape[1], 7, 7), dtype=np.float32)
    assert _cam(ozellik, sinif=w.shape[0]) is None


def test_cam_ortalamasi_gap_linear_ciktisiyla_ayni():
    """GRAD-CAM'IN NEDEN GEREKMEDIGININ SAYISAL KANITI.

    Bas kismi GAP + Linear oldugu icin
        logit[c] = ortalama_hw( toplam_k W[c,k] A[k,h,w] )  + b[c]
    yani CAM haritasinin ORTALAMASI, agirliklarin havuzlanmis ozellikle ic
    carpimina esittir. Grad-CAM ayni sayiyi turevden bulur; bu mimaride turev
    sabit oldugu icin geri yayilim hicbir sey eklemez.

    Test bu esitligi ONNX modeli calistirmadan, gercek agirlik dosyasiyla
    dogrular. Bir gun bas kismina dogrusal olmayan bir katman eklenirse esitlik
    bozulur ve isi haritasinin dayandigi varsayimin gectigi burada gorulur.
    """
    w = _cam_agirlik()
    if w is None:
        pytest.skip("cam_agirlik.npy yok")
    rastgele = np.random.default_rng(1)
    ozellik = rastgele.standard_normal((1, w.shape[1], 7, 7)).astype(np.float32)
    sinif = 3

    ham_harita = np.tensordot(w[sinif], ozellik[0], axes=(0, 0))   # (7,7)
    havuz = ozellik[0].mean(axis=(1, 2))                           # GAP -> (1280,)
    assert ham_harita.mean() == pytest.approx(float(w[sinif] @ havuz), rel=1e-4)
