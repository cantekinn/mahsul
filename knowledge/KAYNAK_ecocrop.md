# Urun parametrelerinin kaynagi

`knowledge/crop_params_global.yaml` icindeki sicaklik, yagis, pH ve doku
esikleri **FAO EcoCrop** veritabanindan otomatik uretilmistir.

- Veri: EcoCrop_DB.csv, https://github.com/OpenCLIM/ecocrop
- Kurum: FAO (Birlesmis Milletler Gida ve Tarim Orgutu), 2568 tur
- EcoCrop 2015'te durduruldu, veri GAEZ v4 portali uzerinden yasiyor

Bu dosyada 91 urun var. Secim ve Turkce adlandirma bize aittir;
SAYILAR EcoCrop'tan geldigi gibidir, tahmin edilmemistir.

Yeniden uretmek icin: `py -m scripts.build_crop_kb`
