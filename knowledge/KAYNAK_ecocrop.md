# Urun parametrelerinin kaynagi

`knowledge/crop_params_global.yaml` icindeki sicaklik, yagis, pH ve doku
esikleri **FAO EcoCrop** veritabanindan otomatik uretilmistir.

- Veri: EcoCrop_DB.csv, https://github.com/OpenCLIM/ecocrop
- Kurum: FAO (Birlesmis Milletler Gida ve Tarim Orgutu), 2568 tur
- EcoCrop 2015'te durduruldu, veri GAEZ v4 portali uzerinden yasiyor

Bu dosyada 115 urun var. Secim ve Turkce adlandirma bize aittir.
Sicaklik, yagis, pH ve doku sayilari EcoCrop'tan geldigi gibidir.

## Kis dayanikligi (`don_dinlenme_c`) bir istisnadir

Her kaydin yaninda `don_dinlenme_kaynak` alani vardir ve uc deger alir:

- `ecocrop` : dogrudan EcoCrop KTMPR alanindan.
- `elle`    : EcoCrop'ta bu alan BOSTU. Bos birakmak "sinirsiz dayanikli"
  anlamina geliyordu; olctugumuzde Antalya'ya ananas onerildi.
- `duzeltme`: EcoCrop'ta alan DOLU ama YANLIS. Yaprak doken ilıman iklim
  meyvelerinde (Prunus turleri, findik) EcoCrop kis dinlenmesi alanina
  cicek donu degerini kopyalamis: Prunus persica icin KTMP ve KTMPR ikisi
  de -5. Karsilastirma icin elma -2/-30, armut -9/-34. Duzeltilmis degerler
  Michigan State Extension'in kis dayanikligi siralamasina dayanir ve
  EcoCrop'un dogru oldugu iki uca (armut -34, elma -30) gore yerlestirilmistir.

Yani sayilarin cogunlugu EcoCrop'tan gelir, ama HEPSI degil. Hangisinin
nereden geldigi YAML'da her urun icin ayri ayri yazilidir.

Yeniden uretmek icin: `py -m scripts.build_crop_kb`
