"""Yayina hazir, kucuk bir dagitim dizini olusturur.

Calistirma: py -m scripts.yayin_hazirla

NEDEN AYRI BIR DIZIN: bu proje deposunda Streamlit arayuzu, ajanlar, egitim
scriptleri ve 540 MB'lik egitim verisi var. Servisin ihtiyaci olan dosyalar
0.8 MB. Tum depoyu yayin saglayicisina baglamak her dagitimda yarim gigabayt
tasimak demekti. Burada yalnizca gereken dosyalar ayri bir dizine kopyalaniyor
ve o dizin kendi git deposu oluyor.

NEDEN ELLE DEGIL SCRIPT ILE: dosya listesini elle tasisaydim, kaynak
degistiginde kopyalamayi unutmak isten bile degildi ve canli surum sessizce
eski kodu calistirmaya devam ederdi. Bu proje o hatayi zaten yasadi.

NEDEN SAGLAYICIYA OZGU DOSYA YOK: burada render.yaml da, Hugging Face YAML
basligi da uretilmiyor. Ikisi de tek bir saglayiciya kilitler ve o saglayici
kosullarini degistirdiginde (Hugging Face Docker Spaces'i 8 Temmuz 2026'da
ucretliye cevirdi) dosya sessizce yaniltici hale gelir. Dockerfile standart,
port ortamdan okunuyor; servis panelden kuruluyor.

NE URETMEZ: bu script dagitimi YAPMAZ. Sonunda calistirilacak git komutlarini
yazar. Kimlik dogrulama gerektiren adimi sessizce yapmasini istemiyorum.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
HEDEF = KOK / "_yayin"

# Dockerfile hangi dosyalari COPY ediyorsa burada da o dosyalar olmali.
# Ikisi ayrisirsa kurulum "dosya yok" diye patlar; sessiz bir yanlis yerine
# gurultulu bir hata, tercih edilen davranis.
DOSYALAR = [
    "Dockerfile",
    ".dockerignore",
    "api/",
    "core/",
    "knowledge/",
    "models/__init__.py",
    "models/crop_reco/__init__.py",
    "models/crop_reco/global_reco.py",
    "models/crop_reco/recommender.py",
    # Servis cagirmiyor ama models/crop_reco/__init__.py import ediyor.
    # Kopyalanmadiginda kap acilista ModuleNotFoundError ile soluyor.
    "models/crop_reco/gbdt.py",
    "data/__init__.py",
    "data/global_location.py",
    "data/open_meteo.py",
    "data/soilgrids_wcs.py",
    "data/one_cikan.py",
    "data/gaez_lookup.py",
    # Kayitli tapu parselleri: okuyucu + geometri + sorgu sonuclari.
    # Bolge klasorleri KOKTE duruyor cunku parcel_files.py onlari orada ariyor.
    "data/megsis.py",
    "data/parcel_files.py",
    "aksu/",
    "alanya_turkler/",
    "gazipasa_beyobasi/",
    "serik_bogazkent/",
    "data/_onbellek/",
    # Hastalik teshis (ONNX cikarim, torch YOK).
    # classifier.py DAHIL EDILMIYOR: torch+timm gerektirir, canliya girmez.
    # classifier_onnx.py classifier.py'den sadece sabitleri import ediyor;
    # bu importlar lazy oldugu icin torch olmadan da guvenle yuklenir. Ancak
    # api/main.py'nin dogrudan cagirdigi label_display/CROP_TR de classifier.py'de
    # tanimli; bu iki sembol modul acilirken torch'a dokunmuyor (dogrulandi),
    # o yuzden classifier.py'yi de canliya alabilirdik AMA icinde train() ve
    # Grad-CAM koduna dokunan seyler var. En temiz cozum: label_display,
    # CROP_TR ve sabitleri tasidigimiz classifier.py aynen kopyalanir; timm
    # ve torch canlida yok, o fonksiyonlar cagrilmadan classifier.py acilabilir.
    "models/disease/__init__.py",
    "models/disease/classifier.py",
    "models/disease/classifier_onnx.py",
    "models/disease/tedavi.py",
    "models/disease/labels.txt",
    "models/disease/efficientnetv2_plant.onnx",
    # Isi haritasi (CAM) icin siniflandirici agirliklari. Ayni sayilar modelin
    # ICINDE initializer olarak da duruyor ama onnxruntime initializer'lari
    # disari vermiyor; okumak icin `onnx` (protobuf) paketi gerekirdi ve o
    # paket sirf bunun icin canliya girmemeli. 231 KB'lik bu dosya ayni bilgiyi
    # bagimlilik olmadan tasiyor. Eksik olursa teshis calisir, sadece isi
    # haritasi null doner (bkz. classifier_onnx._cam_agirlik).
    "models/disease/cam_agirlik.npy",
    # Ajanlar. orchestrator.py (langgraph) ve diagnosis_agent.py (torch)
    # BILEREK yok; gerekce Dockerfile'daki ayni blokta. Niyet yonlendirmesi
    # orchestrator'dan agents/router.py'ye ayrildi, o bagimliliksiz.
    "agents/__init__.py",
    "agents/state.py",
    "agents/router.py",
    "agents/irrigation_agent.py",
    "agents/climate_risk_agent.py",
    "agents/pest_agent.py",
    "agents/carbon_agent.py",
    "agents/advisor_agent.py",
    "web/",
]

# Kaynakta olup dagitima GITMEYECEKLER.
ATLA = {"__pycache__", "node_modules", "dist", ".vite"}

BENIOKU = """# Tarım Asistanı

Dünyanın herhangi bir koordinatı için toprak, iklim, tarım parselleri ve
ürün önerisi. Haritada bir noktaya tıklayın.

Üç sekme var:

- **Ürün önerisi**: seçili noktada ne yetişir (FAO EcoCrop + SoilGrids + iklim
  normali).
- **Tarla takvimi**: aynı nokta için FAO-56 sulama ihtiyacı, 16 günlük iklim
  riski, derece-gün ile zararlı evresi ve IPCC 2019 karbon ayak izi.
- **Hastalık teşhisi**: yaprak fotoğrafından 45 sınıflı teşhis ve tedavi
  önerisi (sunucuda ONNX, PyTorch yok).

Her sekmenin üstünde bir soru kutusu var: serbest metin yazınca sunucu niyeti
bulup ilgili uzmanın hesabını çalıştırır ya da doğru sekmeye yönlendirir.

## Çalıştırma

Tek imaj, hem API'yi hem arayüzü aynı adresten sunar.

    docker build -t tarim-asistani .
    docker run -p 7860:7860 tarim-asistani

Port ortamdan okunuyor (`PORT`), varsayılan 7860. Barındırıcı başka bir port
veriyorsa değişiklik gerekmez.

## Veri kaynakları

Hepsi ücretsiz, hepsi anahtarsız, hiçbiri ödemeli katmana geçmiyor.

| Katman | Kaynak | Notu |
| --- | --- | --- |
| Toprak | SoilGrids 2.0 (ISRIC), WCS kapısı | REST kapısı ISRIC tarafından askıya alındı, WCS aynı rasteri okuyor |
| İklim | Open-Meteo arşivi | 30 yıllık normal |
| Yer adı, yükselti | OpenStreetMap Nominatim, Open-Meteo | |
| Parsel | OpenStreetMap Overpass | |
| Ürün eşikleri | FAO EcoCrop | 91 ürün |
| Sulama | FAO-56 Penman-Monteith | Open-Meteo ET0 + 7 günlük yağış tahmini |
| Zararlı fenolojisi | Derece-gün (GDD) | Literatür eşikleri, 5 zararlı |
| Sera gazı | IPCC 2019 Refinement Tier 1 | EF1/EF4/EF5, AR6 GWP100 = 273 |
| Parsel (tapu) | TKGM parsel sorgu sonuçları | 49 dosya, canlı servis kurumsal erişim istiyor |

## Bilinen sınırlar

Bunları gizlemek yerine yazıyorum, çünkü kullanıcının ne kadar
güvenebileceğini bilmesi gerekiyor.

- **Puan uygunluk puanıdır, kârlılık değildir.** Pazar fiyatı, sözleşmeli
  tarım ve sulama altyapısı EcoCrop'ta yok. "Burada ne yetişir" sorusunu
  yanıtlar, "burada en çok ne kazandırır" sorusunu değil.
- **Hızlı erişim kısayolları bir öneri listesi değildir.** Sadece önbelleği
  önceden doldurulmuş noktalardır. Uygulamayı genel olarak hızlandırmazlar:
  önbellek anahtarı koordinatı yaklaşık 1 km hücreye yuvarlıyor ve dünyanın
  kara yüzeyi ~149 milyon km2.
- **Ücretsiz barındırmada disk kalıcı değil.** Servis uykudan kalkınca
  çalışma anında biriken önbellek silinir; yalnızca depoya gömülü kopya geri
  gelir.
- **Ücretsiz barındırmada servis uykuya dalar.** Uzun süre istek gelmezse
  sonraki ilk istek soğuk açılışı beklemek zorunda kalır.
- **Open-Meteo saatlik istek kotası var.** Kota dolduğunda ürün önerisi boş
  liste değil HTTP 503 döner ve sunucunun kendi gerekçesi ekranda yazar. Boş
  liste döndürmek "burada hiçbir ürün yetişmez" anlamına gelirdi.
- **Dış servis sessizliği "veri yok" sayılmaz.** Toprak veya parsel katmanı
  alınamazsa arayüz "yok" değil "bilinmiyor" yazar.
- **Sulama sayısı net ihtiyaçtır, uygulanacak su değildir.** Toprak nemi,
  sulama yönteminin verimi ve tuzluluk yıkama payı FAO-56'nın bu adımında
  yoktur.
- **İklim riski listesi boşsa "eşik aşımı yok" demektir**, "risk yok"
  demek değildir. Eşikler ürünün EcoCrop sıcaklık aralığından gelir.
- **Zararlı takvimi bir ilaçlama reçetesi değildir.** Derece-gün yalnızca
  sıcaklığa bakar; karar tuzak sayımıyla doğrulanmalıdır.
- **Karbon sayısı gübre ve yakıt girilmediğinde "gösterge"dir.** O durumda
  tablo varsayılanı kullanılır ve yanıt bunu açıkça işaretler. Toprak organik
  karbonu, kireçleme, üre hidrolizi ve makine imalatı kapsam dışıdır; kart
  bunları "Hesabın sınırları" başlığı altında sayar.
- **Kayıtlı tarlalar tarayıcıda durur.** Ücretsiz barındırmada disk kalıcı
  olmadığı için sunucuya yazılan bir liste her yayında silinirdi. Bunun
  bedeli: kayıtlar başka cihazda görünmez.
- **Tapu parselleri kayıtlı sorgu sonuçlarıdır, canlı TKGM sorgusu değildir.**
  TKGM'nin parsel API'si kurumsal erişim ister; istek HTML giriş sayfasına
  yönleniyor (ölçüldü).

## Uç noktalar

`/docs` adresinde tamamı var. Arayüz aynı adresten sunuluyor, bu yüzden
CORS devreye girmiyor. Sağlık yoklaması: `/saglik`.
"""


def _kopyala(kaynak: Path, hedef: Path) -> int:
    """Kopyalanan dosya sayisini doner."""
    if kaynak.is_file():
        hedef.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kaynak, hedef)
        return 1
    sayi = 0
    for yol in kaynak.rglob("*"):
        if any(p in ATLA for p in yol.parts):
            continue
        if yol.is_file():
            varis = hedef / yol.relative_to(kaynak)
            varis.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(yol, varis)
            sayi += 1
    return sayi


def _dockerfile_tutarli_mi() -> list[str]:
    """Dockerfile'in COPY ettigi her yol DOSYALAR listesinde var mi.

    Bu kontrol olmasaydi Dockerfile'a yeni bir COPY eklendiginde bu script onu
    kopyalamaz ve kurulum uzak sunucuda patlardi. Burada, yerelde, saniyesinde
    yakalaniyor.
    """
    metin = (KOK / "Dockerfile").read_text(encoding="utf-8")
    eksik = []
    for satir in metin.splitlines():
        s = satir.strip()
        if not s.startswith("COPY ") or "--from=" in s:
            continue
        parcalar = [p for p in s.split() if not p.startswith("--") and p != "COPY"]
        if len(parcalar) < 2:
            continue
        kaynak = parcalar[0]
        # Bir yol, ya listede AYNEN varsa ya da listedeki bir DIZININ altinda
        # kaliyorsa kapsanmis sayilir. Ornek: "api/requirements.txt" ayrica
        # yazilmasa da "api/" kopyalandigi icin dagitima gidiyor.
        kapsandi = any(
            kaynak.rstrip("/") == d.rstrip("/")
            or (d.endswith("/") and kaynak.startswith(d))
            for d in DOSYALAR
        )
        if not kapsandi:
            eksik.append(kaynak)
    return eksik


def _dockerignore_engelliyor_mu() -> list[str]:
    """Dockerfile'in COPY ettigi bir yolu .dockerignore eliyor mu.

    DOSYALAR kontrolu yetmiyor: dosya _yayin'a kopyalanmis VE git'e girmis
    olsa bile .dockerignore onu kurulum baglamindan atarsa COPY "not found"
    ile coker. Tam olarak bu oldu: "agents/" satiri dururken Dockerfile'a
    agents/*.py COPY'leri eklendi, kurulum uzak sunucuda patladi ve eski imaj
    canlida kaldi (yani hata sessizdi).
    """
    yol = KOK / ".dockerignore"
    if not yol.exists():
        return []
    desenler = [
        s.strip() for s in yol.read_text(encoding="utf-8").splitlines()
        if s.strip() and not s.strip().startswith("#")
    ]
    metin = (KOK / "Dockerfile").read_text(encoding="utf-8")
    catisan = []
    for satir in metin.splitlines():
        s = satir.strip()
        if not s.startswith("COPY ") or "--from=" in s:
            continue
        parcalar = [p for p in s.split() if not p.startswith("--") and p != "COPY"]
        if len(parcalar) < 2:
            continue
        kaynak = parcalar[0].rstrip("/")
        for d in desenler:
            dd = d.rstrip("/")
            if kaynak == dd or kaynak.startswith(dd + "/"):
                catisan.append(f"{parcalar[0]} <- .dockerignore: {d}")
    return catisan


def main() -> None:
    eksik = _dockerfile_tutarli_mi()
    if eksik:
        print("HATA: Dockerfile su yollari COPY ediyor ama DOSYALAR listesinde "
              "yoklar. Kopyalanmazlarsa kurulum uzak sunucuda patlar:")
        for e in eksik:
            print(f"  {e}")
        sys.exit(1)

    catisan = _dockerignore_engelliyor_mu()
    if catisan:
        print("HATA: .dockerignore, Dockerfile'in COPY ettigi yollari eliyor. "
              "Kurulum 'not found' ile coker:")
        for c in catisan:
            print(f"  {c}")
        sys.exit(1)

    if HEDEF.exists():
        # .git DIZINI KORUNUYOR. Hedef zaten uzak depoya bagli bir git deposu;
        # silseydik her calistirmada remote'u ve gecmisi yeniden kurmak
        # gerekirdi ve dagitim gecmisi kaybolurdu.
        for yol in HEDEF.iterdir():
            if yol.name == ".git":
                continue
            shutil.rmtree(yol) if yol.is_dir() else yol.unlink()
    else:
        HEDEF.mkdir(parents=True)

    toplam = 0
    for ad in DOSYALAR:
        kaynak = KOK / ad.rstrip("/")
        if not kaynak.exists():
            print(f"HATA: {ad} bulunamadi")
            sys.exit(1)
        n = _kopyala(kaynak, HEDEF / ad.rstrip("/"))
        toplam += n
        print(f"  {ad:40s} {n:5d} dosya")

    (HEDEF / "README.md").write_text(BENIOKU, encoding="utf-8")
    toplam += 1

    # Yayin dizininde yerel duman testi calistirinca Python __pycache__ uretiyor
    # ve bunlar dagitim commit'ine karisiyordu. Bu dosya her calistirmada
    # yeniden yaziliyor, cunku dizin (.git haric) tamamen siliniyor; kaynakta
    # tutulmazsa her seferinde elle geri koymak gerekirdi.
    (HEDEF / ".gitignore").write_text("__pycache__/\n*.pyc\n", encoding="utf-8")
    toplam += 1

    # .git HARIC. Once dahildi ve sayi giderek yalan soyluyordu: ONNX modeli
    # her degistiginde eski surumu de depoda kaldigi icin .git tek basina
    # 154 MB'a cikmisti ve "233 MB paket" yaziyordu, oysa yayina giden dosyalar
    # 82 MB. Dosya sayisi zaten yalnizca kopyalananlari sayiyordu; iki sayidan
    # biri digerini yalanliyorsa yanlis olan, olcumu genisletendir.
    boyut = sum(
        y.stat().st_size
        for y in HEDEF.rglob("*")
        if y.is_file() and ".git" not in y.relative_to(HEDEF).parts
    )
    print(f"\n{toplam} dosya, {boyut / 1024 / 1024:.1f} MB -> {HEDEF}")

    onbellek = len(list((HEDEF / "data/_onbellek").rglob("*.json")))
    print(f"Gomulu onbellek: {onbellek} nokta dosyasi")

    if (HEDEF / ".git").exists():
        print(f"""
SONRAKI ADIM (dizin zaten bir git deposu):

  cd "{HEDEF}"
  git add -A
  git commit -m "Guncelleme"
  git push

Render kendisi yeniden kuracak.

DIKKAT: burasi "yayin" dalina bagli. Ayni depodaki "main" dali Sprint 1 ve
Sprint 2 teslimini tutuyor ve bu dizinden ASLA guncellenmemeli. Buradaki
dosyalar turetilmis ciktidir, kaynak degildir.
""")
    else:
        print(f"""
SONRAKI ADIMLAR (kimlik dogrulama gerektirdigi icin script yapmiyor):

  1. GitHub'da depo hazir olmali. Render yalnizca bir git deposundan
     kurabiliyor, bu yuzden bu adim atlanamaz.

     Depoda BASKA IS VARSA (ornegin Sprint teslimi), bu anlik goruntuyu
     main'e degil AYRI BIR DALA it. Yoksa oradaki calismanin uzerine yazar.

  2. Asagidakileri calistir:

     cd "{HEDEF}"
     git init
     git remote add origin https://github.com/<kullanici>/<depo>.git
     git add -A
     git commit -m "Tarim Asistani: API + arayuz"
     git branch -M yayin
     git push -u origin yayin

  3. dashboard.render.com -> New -> Web Service -> depoyu sec
     - Branch: yayin             <-- main DEGIL
     - Language / Runtime: Docker
     - Instance Type: Free        <-- ONEMLI, varsayilan ucretli gelebiliyor
     - Health Check Path: /saglik
     Port ayari GEREKMIYOR, Dockerfile ${{PORT}} okuyor.

  4. Ilk kurulum arayuzu de derledigi icin birkac dakika surer. Servis
     acildiktan sonra soguk acilis ve uyku suresini olcup rapor edecegim.
""")


if __name__ == "__main__":
    main()
