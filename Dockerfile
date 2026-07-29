# Tek imaj: API + arayuz. Herhangi bir Docker barindiricisinda calisir.
#
# PORT SABIT DEGIL, ORTAMDAN OKUNUYOR. Her saglayici baska port bekliyor:
# Render PORT degiskenini veriyor (varsayilan 10000), Hugging Face 7860'i
# disariya aciyor, Koyeb 8000 kullaniyor. Porta sabit yazsaydik imaj tek bir
# saglayiciya kilitlenirdi ve tasinmak yeniden kurulum gerektirirdi.
# Varsayilani 7860 biraktim: degisken tanimsizken de calissin.
#
# NEDEN TEK IMAJ: arayuzu ayri bir yere koyunca (Pages, Netlify) tarayici
# baska kokene istek atar, CORS listesini elle guncel tutmak gerekir ve her
# alan adi degisiminde arayuz sessizce bozulur. Ayni servisten sunuldugunda
# koken tek oldugu icin CORS hic devreye girmiyor. Ayrica tek dagitim adimi,
# tek hesap, tek URL.
#
# NEDEN ARAYUZ IMAJIN ICINDE DERLENIYOR: web/dist bir derleme ciktisi, depoya
# konmuyor (bkz .gitignore). Derlenmis dosyayi elle isleseydik, kaynak degisip
# dist guncellenmedigi anda canli surum eski arayuzu gostermeye devam ederdi
# ve bunu fark etmek zor olurdu. Burada her kurulum kaynaktan derliyor.

# --------------------------------------------------------------------------
# Asama 1: React arayuzunu derle
# --------------------------------------------------------------------------
FROM node:20-slim AS arayuz
WORKDIR /kaynak

# NPM SURUMU SABITLENIYOR. node:20-slim icinde npm 10.8.2 geliyor, bizim
# package-lock.json'i ise npm 11.5.2 uretti. Olctuk: npm 10.8.2 ile "npm ci"
# su hatayla patliyor
#   npm error `npm ci` can only install packages when your package.json and
#   package-lock.json are in sync.
#   npm error Missing: @emnapi/core@2.0.0-alpha.3 from lock file
# Ayni kilit dosyasi npm 11.5.2 ile sorunsuz kuruluyor (81 paket, 9 s). Yani
# kilit dosyasi bozuk degil, iki npm surumu istege bagli (optional) platform
# paketlerini farkli cozuyor. Kilidi ureten surumu kullanmak dogru cozum;
# "npm install"a dusmek ise surumleri yukari yuvarlayip canli surumu benim
# olctugumden farkli paketlerle calistirirdi.
RUN npm install -g npm@11.5.2

# npm ci, package-lock.json'daki surumleri BIREBIR kurar (npm install gibi
# yukari yuvarlamaz). Canli surumun benim olctugum surumlerle calismasi icin.
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY web/ ./
# "npm run build" once tsc -b calistirir; tip hatasi varsa imaj kurulmaz.
# Bu bilincli bir tercih: bozuk arayuzun canliya cikmasindansa kurulum patlasin.
#
# src/api/tipler.ts DEPODA DURUYOR, burada uretilmiyor. Uretmek icin ayakta
# bir API gerekir ve derleme sirasinda oyle bir sey yok. Tipleri guncellemek
# gelistiricinin isi: "npm run tipler".
RUN npm run build

# --------------------------------------------------------------------------
# Asama 2: Python servisi
# --------------------------------------------------------------------------
FROM python:3.11-slim

# NEDEN SECICI KOPYALAMA: depo 546 MB ve bunun 468 MB'si data/plantvillage,
# 71 MB'si data/field_benchmark. Ikisi de hastalik teshis modelinin egitim
# verisi; HTTP servisi bunlara HIC dokunmuyor. Tum depoyu kopyalasaydik imaj
# yarim gigabayti asar, ucretsiz kademede her kurulum dakikalar surerdi.

RUN useradd -m -u 1000 kullanici
USER kullanici
ENV HOME=/home/kullanici \
    PATH=/home/kullanici/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR $HOME/uygulama

# Bagimliliklar once: kod degisince pip katmani onbellekten gelsin.
COPY --chown=kullanici api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir --user -r api/requirements.txt

# api/main.py'nin import zincirine giren her sey, baska hicbir sey.
COPY --chown=kullanici core/       core/
COPY --chown=kullanici knowledge/  knowledge/
COPY --chown=kullanici api/        api/
COPY --chown=kullanici models/__init__.py                models/__init__.py
COPY --chown=kullanici models/crop_reco/__init__.py      models/crop_reco/__init__.py
COPY --chown=kullanici models/crop_reco/global_reco.py   models/crop_reco/global_reco.py
COPY --chown=kullanici models/crop_reco/recommender.py   models/crop_reco/recommender.py
# gbdt.py SERVIS TARAFINDAN CAGRILMIYOR ama models/crop_reco/__init__.py onu
# import ediyor, yani paketi import etmek icin dosyanin BULUNMASI sart.
# Olctuk: kopyalanmadiginda kap acilista sonuyordu
#   ModuleNotFoundError: No module named 'models.crop_reco.gbdt'
#
# gbdt_model.txt (9.5 MB) ve lightgbm BILEREK GETIRILMIYOR. gbdt.py lightgbm'i
# ancak model dosyasi VARSA import ediyor; dosya yoksa model_available()
# duzgunce False donuyor. Modeli koyup lightgbm'i koymamak ise tam tersine
# ModuleNotFoundError uretirdi. Yani buradaki durum sessiz bir bozukluk degil,
# tanimli ve dogru bir durum: GBDT ikinci gorusu bu servise dahil degil.
COPY --chown=kullanici models/crop_reco/gbdt.py          models/crop_reco/gbdt.py
COPY --chown=kullanici data/__init__.py         data/__init__.py
COPY --chown=kullanici data/global_location.py  data/global_location.py
COPY --chown=kullanici data/open_meteo.py       data/open_meteo.py
COPY --chown=kullanici data/soilgrids_wcs.py    data/soilgrids_wcs.py
COPY --chown=kullanici data/one_cikan.py        data/one_cikan.py
COPY --chown=kullanici data/gaez_lookup.py      data/gaez_lookup.py

# Hastalik teshis (ONNX cikarim). Torch KANITLI OLARAK YOK: onnxruntime (~50 MB)
# ile FP32 model dosyasi (77 MB) beraber calisir. classifier.py'yi de aliyoruz
# cunku CROP_TR ve label_display sabitleri orada; module-level importlari
# (importlib.util, functools, pathlib) torch'a dokunmaz, ancak train/Grad-CAM
# fonksiyonlari lazy. Egitim aciligi asla cagrilmadigi surece torch olmadan
# guvenle acilir. Model dosyasi ~77 MB imajin en agir tek parcasi.
COPY --chown=kullanici models/disease/__init__.py                    models/disease/__init__.py
COPY --chown=kullanici models/disease/classifier.py                  models/disease/classifier.py
COPY --chown=kullanici models/disease/classifier_onnx.py             models/disease/classifier_onnx.py
COPY --chown=kullanici models/disease/tedavi.py                      models/disease/tedavi.py
COPY --chown=kullanici models/disease/labels.txt                     models/disease/labels.txt
COPY --chown=kullanici models/disease/efficientnetv2_plant.onnx      models/disease/efficientnetv2_plant.onnx

# ONBELLEK IMAJIN ICINE GIRIYOR (155 dosya / 463 KB). Ucretsiz barindirmada
# disk kalici degil: Space uykudan kalkinca calisma anindaki onbellek silinir.
# Depoya gomulu kopya her acilista geri gelir, boylece kisayol noktalari
# kutudan cikar cikmaz hazir olur. Calisma aninda yazilan yeni noktalar ise
# sonraki uykuya kadar yasar; bu kabul edilen bir sinir, gizlenmiyor.
COPY --chown=kullanici data/_onbellek/  data/_onbellek/

# Asama 1'in ciktisi. api/main.py bu dizini gorurse arayuzu "/" altinda sunar.
COPY --from=arayuz --chown=kullanici /kaynak/dist  web/dist

# KURULUM ZAMANI DUMAN TESTI.
# Secici kopyalama tek bir dosya unutuldugunda kabi ACILISTA soldurur ve bunu
# ancak uzak sunucunun kayitlarina bakarak anlarsin. Nitekim tam olarak oyle
# oldu: models/crop_reco/gbdt.py eksikti, imaj sorunsuz kuruldu ve kap
# calistiginda ModuleNotFoundError ile cikti.
# Burada uygulamayi import edip yaniti da uretiyoruz. Bir dosya eksikse
# KURULUM patlar; bozuk imaj hic uretilmez, dolayisiyla canliya da cikamaz.
#
# fastapi.testclient KULLANILMIYOR: o httpx istiyor ve httpx'i yalnizca
# kurulum testi ugruna calisma zamani bagimliligina eklemek istemiyorum.
# Asagisi ayni sorulari dis paket olmadan yanitliyor.
RUN python -c "\
from api.main import app, kisayollar; \
from models.disease.classifier_onnx import is_available as teshis_hazir, _session; \
yollar = {r.path for r in app.routes}; \
[__import__('sys').exit(f'uc nokta eksik: {y}') for y in \
 ('/saglik', '/konum', '/toprak', '/parseller', '/oneri', '/kisayollar', '/teshis') \
 if y not in yollar]; \
k = kisayollar(); \
assert len(k) == 37, f'kisayol sayisi beklenen 37 degil: {len(k)}'; \
h = sum(1 for x in k if x.isitildi); \
assert h >= 25, f'gomulu onbellek imaja girmemis, tam hazir nokta: {h}'; \
assert any(getattr(r, 'name', '') == 'arayuz' for r in app.routes), \
       'arayuz mount edilmemis: web/dist imaja girmemis'; \
assert teshis_hazir(), 'teshis modeli hazir degil (onnxruntime veya .onnx eksik)'; \
_session(); \
print(f'duman testi tamam: {len(k)} kisayol, {h} tam hazir, teshis modeli yuklu')"

EXPOSE 7860

# --host 0.0.0.0 ZORUNLU: 127.0.0.1'e baglanan sunucu kabin DISINDAN gorunmez.
#
# --workers 1: ucretsiz kademede darbogaz CPU degil, dis servislerin gecikmesi
# (WCS 0.9-2.5 s, Overpass 25 s'ye kadar) ve bunlar zaten thread havuzunda
# paralel akiyor. Buna karsilik onbellek DISK uzerinde ve iki isci ayni 1 km
# hucresini ayni anda yazabilir. Tek isci bu yarisi tamamen ortadan kaldiriyor.
# Ayrica Render'in ucretsiz kademesi 512 MB; olctuk, tek isci 102 MB yiyor.
#
# LISTE DEGIL KABUK BICIMI: ${PORT} ancak kabuk tarafindan genisletilir.
# Liste biciminde yazsaydik uvicorn'a "${PORT}" dizesi aynen gider ve
# "Invalid value for '--port'" ile acilista olurdu.
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
