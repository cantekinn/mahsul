# Tarım Asistanı

Küçük çiftçi için çok agentli yapay zeka tarım danışmanı.
Google YZTA 2026 - 14. Grup (Yapay Zeka). SDG 1, 2, 13.

**Canlı:** https://mahsul-ulro.onrender.com

**Sprint raporları:** üç sprintin raporu da bu sayfada, sırayla
[Sprint 1](#-sprint-1-raporu), [Sprint 2](#-sprint-2-raporu) ve
[Sprint 3](#-sprint-3-raporu). Ayrı dosya hâlleri `docs/` altında
([sprint2.md](docs/sprint2.md), [sprint3.md](docs/sprint3.md)). Sprint 1'de
çizilen hedef mimari ile teslim edilen gerçek mimari arasındaki farklar ve
gerekçeleri [7. Mimarı Yapı](#7-mimarı-yapı) bölümünde.

---

## 🚀 Sprint 1 Raporu

### 1. Backlog Dağıtma Mantığı
Takımımız 3 kişiden oluşmakta olup Sprint 1 için planlanan toplam iş hacmimiz 31 SP (Story Point) olarak belirlenmiştir. İş bölümü takım üyelerimizin yetkinliklerine ve odaklanacakları katmanlara göre dengeli (Sıla: 10 SP, Özlem: 10 SP, Can: 8 SP, Ortak: 3 SP) bir şekilde dağıtılmıştır. 

İlk sprintte projenin omurgasını ayağa kaldırmak ve temel makine öğrenmesi tahmin altyapısını kurmak hedeflendiği için en yüksek puanlı iş yükü olan "Crop Recommendation GBDT Modeli Eğitimi" (8 SP) önceliklendirilmiştir. Story'ler alt görevlere bölünerek Miro üzerinden şeffaf bir şekilde takip edilmektedir.

| İş / Görev | SP | Sorumlu | Durum |
| :--- | :---: | :---: | :---: |
| Crop Recommendation GBDT Modeli Eğitimi | 8 | Sıla | Done |
| Tarla Profili DB Şeması ve Hafıza Temeli | 5 | Özlem | Done |
| Toprak ve İklim API İstemcileri (SoilGrids + Open-Meteo) | 5 | Can | Done |
| MEGSİS Parsel İstemcisi Entegrasyonu ve Koordinat Çıkarımı | 5 | Özlem | Done |
| Proje Repo İskeleti ve LangGraph Orkestratör Kabuğu | 3 | Can | Done |
| Basit UI MVP: Parsel Girişi ve Ürün Önerisi Ekranı | 3 | Birlikte | Done |
| Antalya Ürün Bilgi Tabanı Oluşturulması (crop_params.yaml) | 2 | Sıla | Done |

<img width="2936" height="1692" alt="WhatsApp Image 2026-07-05 at 15 26 36" src="https://github.com/user-attachments/assets/7e3aebc8-8b29-4363-95d9-eb91df498652" />


---

### 2. Daily Scrum Notları
Takımımız, sınav haftası yoğunlukları ve üyelerin çalışma takvimlerinin esnekliği nedeniyle bu sprint boyunca her gün senkronize toplantılar yapmak yerine, periyodik aralıklarla asenkron bir iletişim modeli yürütmüştür. İlerleme durumları, teknik blokajlar ve görev geçişleri takım içi mesajlaşma kanallarımız üzerinden yazılı olarak aktarılmış ve süreç Can (SM) koordinasyonunda sorunsuz yönetilmiştir.

**Sprint Ortası Durum Güncelleme Özeti:**
* **Can (Scrum Master / Developer):** "Projenin temel mimari iskeletini ve LangGraph orkestratör kabuğunu ayağa kaldırdım, repo yapısı modüler olarak hazır durumda. Toprak ve iklim verilerini çekeceğimiz dış veri istemcilerini (SoilGrids ve Open-Meteo API bağlantılarını) başarıyla kodladım. Şu an basit UI üzerinde çalışıyorum; parsel girildiğinde ürün önerisi ekranının çalışabilmesi için Özlem and Sıla'nın çıktılarını bekliyorum, ardından arayüz entegrasyonunu birlikte tamamlayacağız. Önümde bir engel yok."
* **Sıla (Product Owner / Developer):** "Model geliştirme tarafında veri setini temizledim, feature engineering adımlarını uygulayarak eksik SoilGrids verilerini modelledim. Bugün itibarıyla projenin kalbi olan Crop Recommendation LightGBM baseline modelinin eğitimini yüksek doğrulukla tamamladım. Antalya bölgesine ait ürün parametre tabanını da hazırlayarak DB katmanına entegre edilmek üzere hazır hale getirdim. Önümde herhangi bir engel yok."
* **Özlem (Developer):** "MEGSİS entegrasyonu tarafında ada/parsel sorgularından GeoJSON verisi dönmeyi başardım, şu an merkez koordinat çıkarımı üzerinde çalışıyorum. Tek engelim TKGM servislerindeki rate-limit belirsizliği; eğer çok sıkıntı yaşarsak harita üzerinde manuel çizim yapılmasına olanak tanıyacak bir yedek planı Sprint 2'ye devredecek şekilde planlıyorum. Tarla profili DB şemasının hafıza temelini ise tamamladım."

---

### 3. Sprint Board Updates
Sprint başında "ToDo" sütununda yer alan iş paketlerimizin büyük bir kısmı tamamlanarak "Done" sütununa taşınmış ve sprint hedeflerimizin veri ve model omurgasını içeren aşamaları başarıyla kapatılmıştır. Sprint sonu itibarıyla güncel Scrum Board görünümümüz şu şekildedir:

* **Done (5 Görev - 23 SP):** Model eğitimi, ürün parametre tabanı, veri tabanı hafıza katmanı, temel API istemcileri ve proje genel mimari iskeleti başarıyla tamamlanmıştır.
* **In Progress (2 Görev - 8 SP):** MEGSİS entegrasyonu üzerindeki test süreçleri ve kullanıcı arayüzü entegrasyon çalışmaları devam etmektedir. Bir sonraki sprintin başında "Done" durumuna çekilmesi planlanmıştır.

<img width="2936" height="1692" alt="WhatsApp Image 2026-07-05 at 15 26 36" src="https://github.com/user-attachments/assets/4faf29fe-d92a-4b91-8bc7-9411478e56fd" />


---

### 4. Ürün Durumu (Product Status)
Sprint 1 sonu itibarıyla projemizin çekirdek veri omurgası ve yapay zeka tahmin katmanı başarıyla ayağa kaldırılmıştır. Kullanıcı arayüzü (UI) çalışmaları entegrasyon aşamasında olup, sistemin arka plan kodları uçtan uca veri akışını sağlayacak şekilde çalışmaktadır.

**Sprint 1 Çıktıları ve Mevcut Yetenekler:**
* **Veri Omurgası Entegrasyonu:** `SoilGrids` ve `Open-Meteo` API istemcileri tamamlanmıştır. Koordinat bazlı toprak (pH, doku, azot, organik karbon) ve anlık hava durumu (sıcaklık, yağış, nem) verileri dinamik olarak çekilebilmektedir.
* **Hafıza Katmanı:** Çekilen coğrafi ve agronomik verilerin sisteme kaydedilmesi için SQLite/Postgres tabanlı `tarla_profili_db.py` veri tabanı şeması kurulmuştur.
* **Yapay Zeka Modeli:** Toprak ve iklim verilerini işleyerek en uygun ürün önerisini sunan GBDT (LightGBM) baseline model eğitimi başarıyla tamamlanmış ve `crop_params.yaml` bilgi tabanı ile ilişkilendirilmiştir.
* **Çalışma Akışı (MVP):** Sistem şu anda parsel verisini aldığında (MEGSİS entegrasyon testleri paralelinde) ilgili koordinatın toprak/iklim analizini yapıp, LightGBM modeli üzerinden Antalya bölgesi için domates, biber veya patates ürün uygunluk skorunu ve ekim penceresini başarıyla hesaplayabilmektedir.

<img width="1600" height="841" alt="WhatsApp Image 2026-07-05 at 20 50 46 (1)" src="https://github.com/user-attachments/assets/08f8b676-d2ba-43a4-bf54-de3d86d43f3c" />
<img width="1600" height="841" alt="WhatsApp Image 2026-07-05 at 20 50 46" src="https://github.com/user-attachments/assets/beab46f0-c663-4331-ae05-d69dc39e5198" />
<img width="1600" height="840" alt="WhatsApp Image 2026-07-05 at 20 50 47" src="https://github.com/user-attachments/assets/df27de2d-8348-4d3c-9a16-847298e2db71" />


---

### 5. Sprint Review
Sprint 1 sonunda planlanan hedefler ve teslim kapsamı başarıyla gözden geçirilmiş, sistemin temel yapı taşları mentor değerlendirmesine sunulacak olgunluğa ulaştırılmıştır.

* **Teslim Edilen Ürün Kapsamı:** Projenin çekirdek veri omurgası (MEGSİS/SoilGrids/Open-Meteo API entegrasyonları), tarla profili veri tabanı hafızası, ilk eğitilmiş GBDT (LightGBM) makine öğrenmesi modeli ve temel arayüz (UI) altyapısı başarıyla teslim edilmiştir.
* **Demo Özeti:** Antalya bölgesine ait örnek bir parsel verisi üzerinden sistem simüle edilmiştir. Girilen koordinata ait anlık toprak ve iklim verilerinin API'ler üzerinden çekilerek veri tabanına kaydedildiği ve LightGBM modelinin bu verilere dayanarak domates/biber/patates için ürün uygunluk ve ekim penceresi önerisini başarıyla ürettiği canlı olarak gösterilmiştir.
* **Hedef Değerlendirmesi:** Sprint başında taahhüt edilen "Parsel bilgisi girildiğinde toprak ve iklim verilerinin çekilmesi, bu verilere göre yapay zeka tabanlı ürün önerisinin üretilmesi" kilometre taşı (milestone) %100 başarıyla karşılanmıştır.

---

### 6. Sprint Retrospective
Sprint 1 sonunda takım içi süreçlerin ve mühendislik pratiklerinin kalitesini artırmak adına gerçekleştirdiğimiz retrospektif toplantısı çıktılarımız şu şekildedir:

* **İyi Giden Yönler:** Dış veri istemcilerinin (SoilGrids ve Open-Meteo API bağlantıları) beklenen süreden çok daha hızlı tamamlanması. Makine öğrenmesi katmanında LightGBM baseline modelinin ilk aşamada yüksek doğruluk oranlarına ulaşması. 3 kişilik optimize ekibimiz sayesinde kararların ve entegrasyon süreçlerinin çok hızlı bir şekilde yürütülmesi.
* **Zorlanılan Noktalar:** MEGSİS API erişimindeki dönemsel yavaşlıklar ve servis belirsizlikleri. Sınav haftası ve yoğun takvimler nedeniyle 3 kişi arasındaki iş yükü dengesini ve zaman yönetimini koruma zorluğu.
* **Gelecek Sprint İçin Aksiyon Planı (Sprint 2):** MEGSİS tarafındaki belirsizlik riskine karşı harita üzerinde manuel çizim yapılmasını sağlayacak yedek planın geliştirilmesine erken başlanması. Sprint 2 hedeflerinde yer alan görüntü işleme (hastalık teşhis) modeli eğitimi için Google Colab GPU süreçlerinin önden optimize edilmesi ve iş paketlerinin daha küçük task'lere bölünerek takip edilmesi.
* Sprint 2 için Product Backlog'a şimdiden 5 görev (görüntü işleme tabanlı hastalık teşhis modeli, RAG+LLM tabanlı danışman agent, iklim/risk ve sulama agent yapıları, vektör hafıza katmanı, WhatsApp/Twilio entegrasyonu) eklenerek bir sonraki sprintin planlama sürecine hız kazandırılmıştır.

### 7. Mimarı Yapı

Aşağıdaki ağaç repodaki **gerçek** dizin yapısıdır; Sprint 1'de çizilen hedef
mimari değildir. Planla teslim arasındaki farklar ve gerekçeleri ağacın altında.

```
tarim-asistani/
  api/
    main.py               # FastAPI: 19 uç nokta (tek servis, arayüzü de sunar)
    requirements.txt      # canlı ortamın bağımlılıkları (repo kökündekinden ayrı)
  web/                    # React + TypeScript + Vite arayüzü
    src/
      App.tsx             # üç sekme: ürün önerisi / tarla takvimi / hastalık teşhisi
      gunluk.ts           # sezon günlüğü (localStorage)
      stil.css            # tasarım sistemi (jeton tabanlı)
      api/
        istemci.ts        # JSON GET istemcisi
        teshis.ts         # multipart POST (fotoğraf yükleme)
        tipler.ts         # OpenAPI'den ÜRETİLİR, elle yazılmaz
      bilesenler/         # Harita, KonumKarti, ToprakKarti, ParselKarti,
                          # OneriListesi, TarlaPaneli, TeshisPaneli, SoruKutusu,
                          # ParselSecici, Kisayollar, Durum
  agents/                 # uzman düğümleri (LangGraph YOK, düz fonksiyon)
    router.py             # anahtar kelime tabanlı niyet yönlendirici
    orchestrator.py
    irrigation_agent.py   # FAO-56 sulama
    climate_risk_agent.py # 16 günlük tahminden ürüne özel risk
    pest_agent.py         # gün-derece zararlı eşikleri
    diagnosis_agent.py
    advisor_agent.py
    carbon_agent.py       # IPCC 2019 Tier 1
    state.py
  models/
    crop_reco/
      global_reco.py      # kural + GAEZ kalibrasyonlu skorlama (canlıda bu çalışır)
      gbdt.py             # LightGBM baseline (eğitildi, canlıya alınmadı)
      recommender.py
    disease/
      classifier_onnx.py  # canlı çıkarım (onnxruntime, torch YOK)
      classifier.py       # eğitim/yerel çıkarım (torch)
      efficientnetv2_plant.onnx   # 45 sınıf, 16 ürün
      cam_agirlik.npy     # sınıf aktivasyon ağırlıkları
      tedavi.py           # etiket -> treatments.yaml eşleştirici
      train.py, eval_field.py, train_colab.ipynb
  data/                   # dış veri istemcileri + önbellek
    global_location.py    # konum/toprak/parsel katman düzeni
    open_meteo.py         # ET0, yağış, tahmin, geçmiş seri
    soilgrids.py, soilgrids_wcs.py
    gaez_lookup.py        # FAO GAEZ v4 uygunluk ızgarası
    megsis.py             # TKGM/MEGSİS (canlı servis erişilemedi, bkz. aşağısı)
    parcel_files.py       # kayıtlı 48 tapu parseli
  knowledge/              # bilgi tabanları ve saf hesap modülleri
    crop_params_global.yaml  # 115 ürün
    fao56.py              # Kc, ETc, etkili yağış
    besin.py              # toprak besin karnesi
    gunluk.py             # sezon günlüğünden biriken su açığı
    karbon.py             # IPCC 2019 Tier 1 envanteri
    degree_day.py, climate_risk.py, kapsam.py, treatments.yaml
  memory/
    farm_profile_db.py    # SQLite (yerelde çalışır, canlıda KULLANILMIYOR)
  core/                   # config, şemalar
  tests/                  # pytest, 327 test
  scripts/                # model dönüşümü, önbellek ısıtma, yayın paketi
  docs/                   # sprint1.md, sprint2.md, sprint3.md
  app/streamlit_app.py    # Sprint 1'in ilk arayüzü (web/ ile değiştirildi)
  Dockerfile              # tek imaj + kurulum sonrası duman testi
```

**Plandan sapmalar ve ölçülmüş gerekçeleri**

| Planda vardı | Ne oldu | Gerekçe |
| --- | --- | --- |
| `app/whatsapp/` | Yapılmadı | Render ücretsiz kademesi 15 dakika sonra uykuya geçiyor; webhook'un ilk mesajı düşerdi. Kullanıcının cevabı beklediği bir kanalda bu kabul edilebilir değil. |
| `memory/vector_store.py` (Chroma) | Yapılmadı | Aranacak serbest metin yok: günlük kayıtları tarih + tür + etiketten ibaret, hepsi tam eşleşmeyle bulunuyor. Vektör arama buraya "eklenmiş olsun diye" eklenmiş olurdu. |
| `memory/` canlıda hafıza | Tarayıcıya taşındı | Render ücretsiz kademesinde disk kalıcı değil; SQLite her yeniden başlatmada sıfırlanırdı. Günlük `localStorage`'a yazılıyor, **hesap sunucuda** kalıyor (`knowledge/gunluk.py`). |
| LangGraph orkestrasyon | Düz fonksiyon yönlendirici | LangGraph kurulumu imaja 13 MB ekliyordu; graf tek adımlık ve dallanmasız olduğu için karşılığı yoktu. `agents/router.py` aynı işi yapıyor. |
| `models/crop_reco/` GBDT canlıda | Kural + GAEZ kalibrasyonu | GBDT süreç belleğine +139 MB RSS ekledi (ölçüldü); 512 MB sınırında öneri motorunun tamamını riske atıyordu. |
| `models/climate_risk/`, `models/weed/` | Yapılmadı | İklim riski eşik tabanlı hesapla çözüldü, ayrı model gerekmedi. Yabancı ot (YOLO) zaten faz 2 olarak işaretliydi. |
| `data/megsis.py` canlı sorgu | Kayıtlı parsel dosyaları | TKGM parsel sorgu API'si kurumsal erişim istiyor; istek 302 ile HTML giriş sayfasına düşüyor. 48 gerçek parsel sorgu sonucu dosya olarak tutuluyor. |
| `knowledge/rag_docs/` | `treatments.yaml` | Tedavi bilgisi anahtar tabanlı ve sonlu (45 hastalık); RAG'ın getireceği tek şey belirsizlikti. |
| `data/nasa_power.py` | Yapılmadı | Open-Meteo hem geçmişi hem tahmini veriyor; ikinci bir kaynak aynı veriyi iki farklı sayıyla gösterme riskiydi. |

---

## 🚀 Sprint 2 Raporu

**Bootcamp:** Google YZTA 2026 - 14. Grup (Yapay Zeka)
**Proje:** Küçük çiftçi için çok agentli yapay zeka tarım danışmanı
**Kalkınma hedefleri (SDG):** 1 Yoksulluğa Son, 2 Açlığa Son, 13 İklim Eylemi
**Sprint süresi:** 6 Temmuz - 20 Temmuz 2026 (2 hafta)
**Takım:** Can Tekin, Özlem, Sıla (3 kişi)

---

### 1. Sprint 2 İçinde Yer Alan Konuların Belirlenmesi ve Bağlantı Kurulması

Takımımız 3 kişiden oluşuyor ve Sprint 2 için planladığımız toplam iş hacmi **28 SP (Story Point)** olarak belirlendi; hedefler teknik zorluk derecelerine göre dengeli dağıtıldı. Sprint 1'deki katman ayrımını koruduk: yapay zeka/görüntü katmanı Sıla'da, iklim ve su katmanı Özlem'de, orkestrasyon ve fenoloji katmanı Can'da.

Bu sprintin en yüksek efor gerektiren işi olan görüntü tabanlı hastalık teşhis modeli Sıla (8 SP) tarafından üstlenildi. Can (SM) ve Özlem uzman agent algoritmalarını ve bunların LangGraph orkestratörüne bağlanmasını yürüttü.

| İş / Görev | SP | Sorumlu | Durum |
| :--- | :---: | :---: | :---: |
| Hastalık Teşhis Modeli Eğitimi (EfficientNetV2-S + Grad-CAM) | 8 | Sıla | Done |
| Yabancı Yaprak Reddi için "Diğer" OOD Sınıfı | 3 | Sıla | Done |
| Teşhis Agent + Tedavi Bilgi Tabanı (treatments.yaml) | 4 | Sıla & Can | Done |
| Sulama Agent (FAO-56 Penman-Monteith) | 3 | Özlem | Done |
| Kural Tabanlı İklim Riski Agent | 2 | Özlem | Done |
| Zararlı Agent (Derece-Gün / GDD Fenoloji) | 4 | Can | Done |
| LangGraph Orkestratör Bağlama + Arayüz | 4 | Can & Özlem | Done |

**Toplam planlanan:** 28 SP &nbsp;|&nbsp; **Tamamlanan:** 28 SP &nbsp;|&nbsp; **Sprint hedefine ulaşma:** %100

**Teknik tercih notu (dürüstlük):** İmkânsız veya maliyetli hiçbir bileşen kullanmadık. Hastalık teşhisinde ConvNeXt yerine **EfficientNetV2-S** seçildi (CPU'da daha hızlı, transfer öğrenmede aynı seviye; darboğaz mimari değil veri). Tedavi bilgisi için RAG/LLM yerine **treatments.yaml yapılı tabanı** kullanıldı (9 sabit hastalık için daha ucuz, deterministik, API anahtarı gerektirmez). İklim riskinde LightGBM yerine **kural tabanlı** yaklaşım seçildi çünkü etiketli iklim-riski verisi yok; kural tabanlı yöntem şeffaf ve savunulabilir.

---

### 2. Daily Scrum Notları

Üyelerin yaz stajı tempoları nedeniyle her gün senkron toplantı yerine periyodik asenkron bir iletişim modeli yürüttük. İlerlemeler WhatsApp kanalında Can (SM) koordinasyonunda yazılı aktarıldı; LangGraph state yapısındaki veri tipi uyuşmazlıkları ve foto-teşhis yönlendirmesi anlık çözüldü.

Sprint ortası ve kapanış durum güncellemeleri:

* **Can (Scrum Master / Developer):** "Orkestratörü stub durumdan çıkarıp tüm gerçek agent'ları bağladım; gelen soruya (ya da fotoğraf varlığına) göre doğru uzmana yönlendiriyor. Open-Meteo istemcisini genişlettim, artık FAO-56 ET0 ve 16 günlük tahmin serisi dönüyor. Derece-gün (GDD) zararlı fenoloji modülünü ve agent'ını yazdım. Arayüze dört hızlı aksiyon butonu ve yaprak fotoğraf yükleyici ekledim. Kritik bir hata buldum: profil orkestratöre parsel bilgisi olmadan gidiyordu, düzelttim. Önümde engel yok."
* **Sıla (Product Owner / Developer):** "Hastalık modelini kurdum: EfficientNetV2-S transfer öğrenme, Grad-CAM ısı haritası. PlantVillage laboratuvar verisiyle val doğruluğu %97.8 oldu. Ancak gerçek tarla fotoğraflarında güven düşüktü (lab-saha uçurumu), bu yüzden PlantDoc saha fotoğraflarını ekleyip yeniden eğittim; lab %98.6, saha doğruluğu %31.7'den %61.9'a çıktı. Son olarak modelin yalnızca 9 sınıf bildiği için yabancı yaprağı (ör. narenciye) zorla domates/patates'e itmesi sorununu çözdüm: 'diğer' adında bir OOD sınıfı ekleyip 11 hedef-dışı yaprak türüyle eğittim; artık bilmediği yaprağı reddediyor. Önümde engel yok."
* **Özlem (Developer):** "Sulama tarafında FAO-56 Penman-Monteith modülünü yazdım; ET0 ders kitabı değerleriyle birebir doğrulandı (es(20)=2.338, delta(20)=0.145). Sulama agent'ı parselin konumundan ET0 çekip ürün katsayısı Kc ve etkili yağış ile net litre/gün veriyor. İklim riski modülünü kural tabanlı olarak yeniden yazdım: artık sadece eşik değil, gün sayısı (şiddet) ve ürün uygunluk kararı da veriyor; böylece her ürün için risk gerçekten farklılaşıyor (sıcak dalgasında patates 16/16 gün uygun değil, zeytin sadece 3/16 orta). Önümde engel yok."


---

### 3. Sprint Board Updates

Sprint başında "To Do" sütununda yer alan iş paketlerimizin tamamı tamamlanarak "Done" sütununa taşınmış ve Sprint 2 hedefimiz olan dört uzman agent'ın orkestrasyona canlı bağlanması başarıyla kapatılmıştır. Sprint sonu itibarıyla güncel Scrum Board görünümümüz şu şekildedir:

* **Done (5 Görev - 28 SP):** Hastalık teşhis CNN'i (EfficientNetV2-S + Grad-CAM, eğitildi), yabancı yaprağı reddeden "diğer" OOD sınıfı, treatments.yaml tedavi tabanlı teşhis agent'ı, FAO-56 sulama agent'ı, derece-gün zararlı agent'ı, kural tabanlı iklim riski agent'ı ve tüm agent'ları tek arayüzden yöneten LangGraph orkestratörü başarıyla tamamlanmıştır.
* **In Progress (0 Görev):** Bu sprintte devam eden kart kalmadı; hedeflere %100 ulaşıldı.
* **To Do (Sprint 3'e devir):** Karbon ayak izi agent'ı bilinçli olarak Sprint 3'e bırakılan bir stub olarak duruyor. Ayrıca narenciye/zeytin/muz için gerçek hastalık sınıfları, WhatsApp entegrasyonu ve çoklu parsel/premium bir sonraki sprintin backlog'una alındı.

<img width="2938" height="1582" alt="WhatsApp Image 2026-07-18 at 11 06 32 (1)" src="https://github.com/user-attachments/assets/2e7024a1-1213-4bd3-b25f-f1ee0af59f9e" />
<img width="2940" height="1586" alt="WhatsApp Image 2026-07-18 at 11 08 15" src="https://github.com/user-attachments/assets/8e341a96-9593-432b-bd70-29c6ba1b1504" />


---

### 4. Ürün Durumu (Product Status)

Sprint 2 kapanışında sistem, Sprint 1 iskeletinin üstüne dört uzman agent eklenmiş çalışan bir MVP durumunda:

* **Görüntü İşleme Katmanı:** Çiftçinin yüklediği yaprak fotoğrafından (domates, biber, patates) hastalık teşhisi yapan ve Grad-CAM ile hasarlı bölgeyi işaretleyen CNN. Model önce **ürünü** (domates/biber/patates) belirler, sonra hastalığı önerir. Fotoğraf hedef ürünlerden biri değilse ("diğer") teşhis dayatmaz, "bu yaprak eğittiğim ürünlerden değil" der; yanlış teşhisi önler.
* **Tedavi Bilgi Tabanı:** Teşhis edilen hastalığa karşı `treatments.yaml` içinden doğal ve kimyasal (etken madde sınıfı + yasal uyarı) tedavi öneren danışman altyapısı. Maliyetsiz, API'siz, deterministik.
* **Akıllı Uzman Agent'lar:** FAO-56 ile net sulama ihtiyacını litre/gün hesaplayan Sulama Agent'ı, don/sıcaklık stresi/yağış/kuraklık risklerini gün sayısı ve uygunluk kararıyla veren İklim Agent'ı, derece-gün modeliyle böcek nesil/evresini hesaplayan Zararlı Agent'ı.
* **Orkestrasyon (LangGraph):** Tüm alt agent'ları tek arayüzden kullanıcı niyetine (intent) göre yönlendiren state graph mimarisi uçtan uca çalışıyor. Altı niyet (ürün önerisi, sulama, iklim riski, zararlı, teşhis, danışman) doğru yönlendiriliyor.

**Modelin ölçülen durumu (dürüst rakamlar):**

| Metrik | Değer |
| :--- | :---: |
| Laboratuvar val doğruluğu | **%98.6** |
| Gerçek saha fotoğrafı doğruluğu (sadece lab) | %31.7 |
| Gerçek saha fotoğrafı doğruluğu (lab + PlantDoc saha) | **%61.9** |
| Saha doğruluğu ("diğer" sınıfı takasıyla) | %57 |
| Yabancı yaprak (eğitimde görülmeyen tür) reddi | **%81** |

<img width="1919" height="871" alt="Ekran görüntüsü 2026-07-20 044652" src="https://github.com/user-attachments/assets/d1d698f1-539d-4d8b-a18f-c154d127b1fa" />

<img width="1919" height="869" alt="Ekran görüntüsü 2026-07-20 045756" src="https://github.com/user-attachments/assets/6601b025-c6ef-43c5-9fd0-18324579371a" />

<img width="1919" height="865" alt="Ekran görüntüsü 2026-07-20 045812" src="https://github.com/user-attachments/assets/50b1f98f-b5ed-444d-871b-03ae15d87982" />

<img width="1919" height="867" alt="Ekran görüntüsü 2026-07-20 045901" src="https://github.com/user-attachments/assets/198071c9-4fc6-46d3-8559-e2ba4d34e35d" />

<img width="1919" height="870" alt="Ekran görüntüsü 2026-07-20 045834" src="https://github.com/user-attachments/assets/01d21c5d-aa2e-470e-99a7-e588270dd9e3" />

---

### 5. Sprint Review

Sprint 2 hedefi olan "dört uzman agent'ın orkestrasyona canlı bağlanması" tam teslim edildi. Altı niyetin tamamı uçtan uca test edildi ve gerçek açık veriyle çalıştı: Antalya koordinatında domates için net 7.37 mm/gün sulama, Temmuz'da Tuta absoluta 4. nesil, 41.4 C sıcaklık stresi yüksek riski gibi gerçekçi çıktılar üretildi. Hastalık modeli gerçekten eğitildi (lab %98.6) ve gerçek tarla fotoğraflarına PlantDoc ile uyarlandı; ayrıca yabancı yaprağı reddeden "diğer" sınıfıyla yanlış teşhis riski büyük ölçüde giderildi.

Tüm karar mekanizmaları (FAO-56 fizik, GDD fenoloji, kural tabanlı risk, treatments.yaml) şeffaf ve savunulabilir; hiçbiri lisanslı veri veya API anahtarı gerektirmiyor (SDG uyumlu, sıfıra yakın maliyet).

**Demo senaryosu:** Serik parseli seç → "domates sulama planı" (ET0 ve litre/gün) → "zararlı tahmini" (Tuta absoluta nesli) → "iklim riski" (sıcaklık stresi uyarısı) → yaprak fotoğrafı yükle (doğru teşhis + ürün + Grad-CAM), ardından yabancı yaprak yükle ("tanımadım" reddi).

---

### 6. Sprint Retrospective

**İyi giden yönler:**
- Sprint 1 iskeleti sayesinde agent'lar mevcut düğümlere takılarak hızlı eklendi.
- Her agent'ın kararı fizik/agronomi ile savunulabilir; kara kutu yok.
- Hiçbir özellik lisanslı veri veya ödemeli API gerektirmiyor (SDG uyumlu).
- Model gerçek saha verisiyle eğitildi ve yabancı yaprağı reddetmeyi öğrendi; sunumda güven/doğruluk avantajı.

**Zorlanılan noktalar:**
- Lab-saha uçurumu: PlantVillage laboratuvar fotoğrafları gerçek tarlayı temsil etmiyordu; PlantDoc saha verisiyle kapatıldı ama saha doğruluğu %90'a değil %57-62 seviyesine ulaştı (sınıf başına ~75 saha fotoğrafı sınırı). Dürüst tavan.
- Yabancı yaprak sorunu: model 9 sınıf bildiği için narenciye yaprağını zorla yanlış sınıflandırıyordu; "diğer" OOD sınıfı eğitilerek çözüldü.
- Kimyasal tedavi önerilerinde yasal sorumluluk: etken madde sınıfı + uyarı ile sınırlandı, reçete yerine geçmez.

**Sprint 3 aksiyonları:**
- Narenciye/zeytin/muz için gerçek hastalık sınıfları (veri toplama + yeniden eğitim).
- Karbon ayak izi agent (stub'ın gerçeklenmesi).
- WhatsApp entegrasyonu (sahada erişim).
- Saha doğruluğunu artırmak için ek saha verisi.



---

## 🚀 Sprint 3 Raporu

**Bootcamp:** Google YZTA 2026 - 14. Grup (Yapay Zeka)
**Proje:** Küçük çiftçi için çok agentli yapay zeka tarım danışmanı
**Kalkınma hedefleri (SDG):** 1 Yoksulluğa Son, 2 Açlığa Son, 13 İklim Eylemi
**Sprint süresi:** 21 Temmuz - 3 Ağustos 2026 (2 hafta)
**Takım:** Can Tekin (Scrum Master / Developer), Sıla (Product Owner / Developer), Özlem (Developer)
**Canlı adres:** https://mahsul-ulro.onrender.com
**Ayrıntılı sprint raporu:** [docs/sprint3.md](docs/sprint3.md)

---

### 1. Backlog Dağıtma Mantığı

Sprint 3 için planlanan toplam iş hacmi **34 SP** olarak belirlendi. Sprint 1 ve
Sprint 2'nin sonunda elimizde çalışan ama **yalnızca yerel makinede** çalışan bir
sistem vardı: hastalık teşhis modeli eğitilmişti fakat webde yoktu, dört uzman
agent orkestratöre bağlıydı fakat kullanıcının göreceği bir arayüzde karşılığı
yoktu. Bu yüzden Sprint 3'ün tek bir hedefi oldu ve backlog buna göre bölündü:
**her şey gerçek bir kullanıcının tarayıcıdan açabileceği bir adreste
çalışacak.** Bir özellik canlıda çalışmıyorsa bu sprintte "Done" sayılmadı.

Katman ayrımı önceki sprintlerdeki gibi korundu: yapay zeka ve görüntü katmanı
Sıla'da, su/iklim/karbon katmanı Özlem'de, orkestrasyon, veri katmanı ve yayın
altyapısı Can'da.

| İş / Görev | SP | Sorumlu | Durum |
| :--- | :---: | :---: | :---: |
| Hastalık teşhisini webe alma (PyTorch -> ONNX, `/teshis` + Teşhis sekmesi) | 6 | Sıla | Done |
| Ürün kapsamını 45 sınıf / 16 ürüne genişletme (Colab GPU'da yeniden eğitim) | 5 | Sıla | Done |
| Sprint 2 agent'larını webe alma (`/sulama`, `/iklim-riski`, `/zararli` + Tarla takvimi sekmesi) | 5 | Özlem | Done |
| FAO GAEZ v4 ile ürün öneri skorunun kalibrasyonu | 4 | Can | Done |
| Karbon ayak izi agent'ının gerçeklenmesi (IPCC 2019 Tier 1, `/karbon`) | 3 | Özlem | Done |
| Serbest metin soru yönlendirici (`/sor`) ve kapsam şeffaflığı (`/kapsam`) | 3 | Can | Done |
| Tapu parseli seçici (48 gerçek TKGM kaydı) + Tarlalarım | 2 | Can | Done |
| Tasarım sistemi (tipografi/boşluk jetonları, odak halkası, form denetimleri) | 2 | Özlem | Done |
| Otomatik test paketi (`tests/`, pytest) | 2 | Can | Done |
| Toprak besin karnesi (`/besin`) | 1 | Can | Done |
| Sezon günlüğü ve hafızanın cevaba bağlanması (`/gunluk`) | 1 | Can | Done |

**Kişi bazında dağılım:** Sıla 11 SP &nbsp;|&nbsp; Can 13 SP &nbsp;|&nbsp; Özlem 10 SP
**Toplam planlanan:** 34 SP &nbsp;|&nbsp; **Tamamlanan:** 34 SP &nbsp;|&nbsp; **Sprint hedefine ulaşma:** %100

**Teknik tercih notu (dürüstlük):** Bu sprintte aldığımız kararların çoğu "ne
ekleyelim" değil **"neyi eklemeyelim"** kararıydı ve hepsi bir ölçüme dayandı.
Reddedilen işlerin listesi ve her birinin ölçülmüş gerekçesi 5. bölümdeki
tablodadır.

<!-- SS1: Sprint 3 backlog / görev tablosu ekran görüntüsü -->

---

### 2. Sprint 2'den Sprint 3'e Ne Değişti

Sprint 3 sıfırdan bir şey kurmadı; Sprint 1 ve 2'de yazılan her hesabı
kullanıcının erişebileceği bir yere taşıdı ve yolda birkaç bileşeni değiştirmek
zorunda kaldı.

| Konu | Sprint 2 sonunda | Sprint 3 sonunda |
| :--- | :--- | :--- |
| Arayüz | Streamlit, yalnızca yerel | React + TypeScript, üç sekmeli tek servis, canlı adres |
| Hastalık modeli | PyTorch, 9 sınıf / 3 ürün, sadece yerel | ONNX (torch'suz çıkarım), **45 sınıf / 16 ürün**, canlı `/teshis` |
| Isı haritası | Grad-CAM (torch geri yayılımı) | Önceden çıkarılmış sınıf aktivasyon ağırlıklarıyla forward-only ısı haritası |
| Öneri motoru | GBDT (LightGBM) baseline, 3 ürün | Kural + **FAO GAEZ v4** kalibrasyonu, **115 ürün** |
| Sulama | FAO-56, tek ürün grubu | FAO-56 Tablo 12'den **84 ürün** için Kc |
| Karbon agent | Stub (boş iskelet) | **IPCC 2019 Tier 1** emisyon envanteri, `/karbon` |
| Orkestrasyon | LangGraph state graph | `agents/router.py` düz fonksiyon yönlendirici (13 MB kazanç) |
| Parsel | MEGSİS canlı sorgu denemesi | 48 gerçek TKGM tapu kaydı, listeden seçilebilir |
| Hafıza | SQLite (yerel disk) | Sezon günlüğü tarayıcıda, **hesap sunucuda** |
| Test | Yok | **327 otomatik test** |
| Dağıtım | Yok | Docker imajı + kurulum sonrası duman testi, Render'da canlı |

---

### 3. Daily Scrum Notları

Asenkron iletişim modeli korundu; ilerlemeler WhatsApp kanalında Can (SM)
koordinasyonunda yazılı aktarıldı. Bu sprintte tartışmaların merkezinde
**Render ücretsiz kademesinin 512 MB RAM sınırı** vardı: her yeni özellik önce
"canlıda sığar mı" sorusundan geçti, sığmayan bileşen kütüphane değiştirilerek
ya da hesabı yeniden yazılarak sığdırıldı.

* **Can (Scrum Master / Developer):** "Öneri skorunu FAO GAEZ v4 uygunluk
  ızgarasıyla kalibre ettim; artık skor bizim uydurduğumuz bir ağırlık değil,
  FAO'nun ölçtüğü uygunlukla hizalı. Serbest metin soru kutusunu yazdım:
  çiftçinin cümlesi hangi hesabın işiyse oraya gidiyor, gitmiyorsa doğru sekmeye
  yönlendiriyor, 'anlamadım' demiyor. 48 gerçek tapu parselini seçilebilir hale
  getirdim; kullanıcı haritada gözle tarla aramak yerine kendi kaydını seçiyor,
  alan da tapudan geliyor. Sprint sonunda pytest paketini kurdum, toprak besin
  karnesini ve sezon günlüğünü bağladım. Önümde engel yok."
* **Sıla (Product Owner / Developer):** "Modeli 45 sınıf / 16 ürüne genişletip
  Colab GPU'da yeniden eğittim. Asıl iş modeli webe sokmaktı: PyTorch canlı
  imaja sığmıyordu, modeli ONNX'e çevirip `onnxruntime` ile torch'suz çıkarım
  yaptım. Grad-CAM torch geri yayılımı istediği için canlıda kullanılamıyordu,
  yerine sınıf aktivasyon ağırlıklarını önceden çıkarıp forward-only ısı
  haritası ürettim, yani çiftçi modelin yaprağın neresine baktığını hâlâ
  görüyor. Teşhis sekmesi mobilde doğrudan kamerayı açıyor. Önümde engel yok."
* **Özlem (Developer):** "Sprint 2'de yazdığımız üç agent'ı üç uç noktaya ve tek
  bir Tarla takvimi sekmesine bağladım. Kc kapsamını FAO-56 Tablo 12'den 84
  ürüne çıkardım. Karbon agent'ının stub'ını IPCC 2019 Tier 1 emisyon
  faktörleriyle gerçekledim; gübre, yakıt ve kalıntı yakma kalemleri ayrı ayrı
  görünüyor. Sprint sonunda tasarım sistemini kurdum: tipografi ve boşluk
  jetonları, tek bir odak halkası, dokunmatikte 44 piksel hedefler. Önümde engel
  yok."

<!-- SS2: Daily Scrum (WhatsApp) yazışma ekran görüntüsü -->

---

### 4. Sprint Board Updates

Sprint başında "To Do" sütununda duran 11 kartın tamamı "Done" sütununa taşındı
ve hepsi canlı adreste çalışır durumda.

* **Done (11 Görev - 34 SP):** Hastalık teşhisinin ONNX ile webe alınması, 45
  sınıflık yeniden eğitim, GAEZ kalibrasyonu, üç Sprint 2 agent'ının webe
  alınması, karbon agent'ının gerçeklenmesi, soru yönlendirici, kapsam uç
  noktası, tapu parseli seçici, tasarım sistemi, 327 testlik pytest paketi,
  toprak besin karnesi ve sezon günlüğü.
* **In Progress (0 Görev):** Bu sprintte devam eden kart kalmadı.
* **To Do (bilinçli olarak alınmayanlar):** Freemium/ödeme duvarı ve Chroma
  vektör hafıza backlog'dan **çıkarıldı**, ertelenmedi; gerekçeleri 6. bölümdeki
  tabloda. WhatsApp entegrasyonu ertelendi.

<!-- SS3: Sprint sonu Sprint Board görünümü (hepsi Done sütununda) -->

---

### 5. Ürün Durumu (Product Status)

Sprint 3 kapanışında ürün, tarayıcıdan açılan tek bir servis. Üç sekme var ve
her sekme kendi hesabını gerçek, ölçülmüş veriyle yapıyor.

**Ölçülen kapsam (canlı sistemden okundu, tahmin değil):**

| Ne | Kaç |
| :--- | :---: |
| HTTP uç noktası | **19** |
| Ürün önerisi bilgi tabanı | **115 ürün** (55'i çok yıllık) |
| İklim riski kapsamı | **116 ürün** |
| FAO-56 sulama (Kc tanımlı) | **84 ürün** |
| Derece-gün zararlı modeli | **5 zararlı** |
| Hastalık teşhis sınıfı | **45 sınıf / 16 ürün** |
| Tedavi kaydı (`treatments.yaml`) | **24 hastalık** |
| Kayıtlı TKGM tapu parseli | **48** |
| Haritadaki hazır tarım noktası | **37** |
| Otomatik test | **327** |

**Sekme sekme ne var:**

* **Ürün önerisi:** Dünyanın herhangi bir noktasına tıklanır. Konum, toprak
  (SoilGrids), tapu parseli ve öneri katmanları **ayrı ayrı** yüklenir; ekran en
  yavaş katmanın hızına inmez. Skor FAO GAEZ v4 uygunluk ızgarasıyla kalibre
  edilmiştir, her ürün için ekim penceresi ve gerekçe gösterilir.
* **Tarla takvimi:** Sulama (FAO-56 ET0 ve Kc ile litre/dekar), iklim riski (16
  günlük tahminden don, sıcaklık stresi, kuraklık), zararlı (derece-gün ile
  nesil ve evre), karbon ayak izi (IPCC 2019 Tier 1), toprak besin karnesi ve
  sezon günlüğü kartları.
* **Hastalık teşhisi:** Yaprak fotoğrafı yüklenir veya mobilde doğrudan çekilir.
  ONNX çıkarımı, **kademeli güven** (kesin / olası / belirsiz / tanımsız), sınıf
  aktivasyon ısı haritası ve tedavi kartı (belirti, doğal, kimyasal, korunma).
  Model tanımadığı yaprağı reddeder, teşhis dayatmaz.
* **Soru kutusu (her sekmede):** Serbest cümle doğru uzmana gider; hesabı
  yapılamıyorsa doğru sekmeye yönlendirir.

<!-- SS4: Ürün önerisi sekmesi - harita üzerinde seçili nokta + öneri listesi -->
<!-- SS5: Tarla takvimi sekmesi - sulama, iklim riski ve zararlı kartları -->
<!-- SS6: Karbon ayak izi ve toprak besin karnesi kartları -->
<!-- SS7: Hastalık teşhisi sekmesi - fotoğraf, teşhis, ısı haritası, tedavi kartı -->
<!-- SS8: Soru kutusu - serbest metin sorusu ve dönen cevap -->

**Hafıza katmanı (bu sprintin son işi):** Sezon günlüğü tarayıcıda
(`localStorage`) tutulur, **hesap sunucuda** yapılır. Günlüğün cevabı gerçekten
değiştirdiği iki yer var ve ikisi de hafıza olmadan hesaplanamaz:

1. `/gunluk` - son sulamadan bu yana biriken **net su açığı**. `/sulama`
   önümüzdeki 7 günün tahminine bakıp "günde kaç mm ver" der; bu ise geçmişe
   bakıp "en son suladığın günden bu yana ne kadar borç birikti" der. Ölçülen
   örnek (Bursa Karacabey, domates, son sulama 25 Temmuz):
   `ETc 46.1 mm - etkili yağış 0.0 mm = 46.1 mm açık = dekara 46.100 litre`.
2. `/teshis` - aynı hastalık günlükte daha önce var mı, arada kaç ilaçlama
   yazılmış. İki olgu yan yana konur, **hüküm verilmez**: "ilaç işe yaramadı"
   demiyoruz, çünkü bunu ölçmedik.

<!-- SS9: Sezon günlüğü kaydı ve biriken su açığı kartı -->
<!-- SS10: Mobil (telefon) görünümü -->

**Çalıştırma:**
```bash
# Sunucu
pip install -r api/requirements.txt
uvicorn api.main:app --host 127.0.0.1 --port 8000

# Arayüz (geliştirme)
cd web && npm install && npm run dev

# Testler
pytest -q

# Yayın paketi
py -m scripts.yayin_hazirla    # -> _yayin/
```

<!-- SS11: pytest çıktısı (327 test geçti) -->
<!-- SS12: /docs Swagger arayüzü (19 uç nokta listesi) -->

---

### 6. Sprint Review

Sprint hedefi olan "her şey canlıda çalışacak" maddesi tam teslim edildi. Sprint
1 ve Sprint 2'de yazılan hiçbir hesap yerelde kalmadı.

**Bu sprintte REDDEDİLEN işler ve ölçülmüş gerekçeleri.** Bunlar "yetişmedi"
değil, "ölçtük ve almamaya karar verdik" kalemleridir:

| Reddedilen | Ölçüm | Karar |
| :--- | :--- | :--- |
| PyTorch'un canlıya alınması | CPU-only kurulum bile ~200 MB; 512 MB sınırında öneri motorunu riske atıyordu | ONNX + `onnxruntime`, torch canlıdan tamamen düşürüldü |
| GBDT (LightGBM) öneri motoru | Süreç belleğine **+139 MB RSS** ekledi | Kural + GAEZ kalibrasyonu canlıda kaldı |
| LangGraph orkestrasyon | İmaja **13 MB** ekliyordu, graf tek adımlık ve dallanmasız | `agents/router.py` (düz fonksiyon) aynı işi yapıyor |
| Canlı MEGSİS/TKGM parsel sorgusu | İstek **302 ile HTML giriş sayfasına** düşüyor (kurumsal erişim isteniyor) | 48 gerçek sorgu sonucu dosya olarak tutuldu |
| Sunucu tarafı kullanıcı kaydı | Render ücretsiz kademesinde **disk kalıcı değil**; her yeniden başlatmada sıfırlanırdı | Günlük tarayıcıda, hesap sunucuda |
| Chroma vektör hafıza | Aranacak serbest metin yok: kayıtlar tarih + tür + etiket, tam eşleşmeyle bulunuyor | Alınmadı |
| Freemium / ödeme duvarı | Ürünün hiçbir maliyeti kullanıcı başına artmıyor (lisanslı veri yok, LLM çağrısı yok) | Alınmadı |
| WhatsApp entegrasyonu | Render ücretsiz kademesi **15 dakika** sonra uykuya geçiyor; webhook'un ilk mesajı düşerdi | Ertelendi |
| Gübre dozu önerisi | Doz = ürünün kaldırdığı azot - toprağın verdiği azot; **ikisi de** elimizdeki uzaktan algılama ölçümlerinden hesaplanamıyor | Besin karnesi doz vermiyor, ölçümü ve laboratuvar testi öneriyor |
| Grad-CAM (torch) | `torch.backward` gerektiriyor, canlıda torch yok | Önceden çıkarılmış sınıf aktivasyon ağırlıklarıyla forward-only ısı haritası |

Bootcamp değerlendirme ölçütü olan **"eklenmiş olsun diye eklenmiş özellik puan
kırar"** kuralını bu sprintte özellik eklemek kadar özellik reddetmek için de
kullandık.

**Demo senaryosu:** Tapu kaydını listeden seç (nokta ve alan birlikte kurulur)
-> ürün önerisi listesi -> Tarla takvimi sekmesinde sulama, iklim riski,
zararlı, karbon ve besin kartları -> günlüğe sulama tarihi yaz, biriken su açığı
kartı belirir -> Teşhis sekmesinde yaprak fotoğrafı yükle, teşhis, ısı haritası
ve tedavi gelsin -> soru kutusuna "domatese kaç litre su vermeliyim" yaz, plan
ve günlükten gelen birikmiş açık birlikte gelsin.

<!-- SS13: Render dashboard - canlı servis çalışıyor -->

---

### 7. Sprint Retrospective

**İyi giden yönler:**
- "Canlıda çalışmıyorsa Done değil" kuralı sprint boyunca tek ölçüt oldu ve
  yarım kalmış iş bırakmadı.
- Her reddedilen özelliğin arkasında bir sayı var (RSS, MB, HTTP kodu, saniye);
  hiçbiri "gerek görmedik" ile geçiştirilmedi.
- Kurulum sonrası **duman testi** Dockerfile'a gömülü: uç noktaların varlığı,
  model dosyasının imaja girmesi, kısayol ve parsel sayıları ve üç hesabın
  (karbon, besin, günlük) doğru sonuç ürettiği imaj kurulurken doğrulanıyor.
  Bozuk bir imaj deploy edilemiyor.
- Sprint 3'ün sonunda 327 otomatik test var; Sprint 2 sonunda sıfırdı.

**Zorlanılan noktalar:**
- 512 MB RAM sınırı sprintin en büyük kısıtıydı ve iki büyük bileşenin (torch,
  GBDT) canlıya alınmasını engelledi. İkisinin de yerine geçen çözüm bulundu ama
  bu, planlanandan fazla iş demekti.
- `scripts/yayin_hazirla.py` ile `Dockerfile` arasındaki dosya listesi tek yönlü
  kontrol ediliyor: biri güncellenip diğeri unutulursa imaj eksik dosyayla
  kurulabilir. Şimdilik duman testi bu boşluğu kapatıyor, ama iki listenin tek
  kaynaktan üretilmesi gerekiyor.
- Sezon günlüğü koordinat hücresine (3 ondalık, ~110 m) bağlı. 300 m ötedeki bir
  tıklama boş günlük gösterir. 2 ondalığa (~1.1 km) çıkarmak komşu tarlaları
  birleştirir ve **başkasının sulama tarihinden yanlış bir açık** hesaplardı;
  boş günlük görmek buna tercih edildi. Bilinen ve kabul edilmiş sınır.
- Saha doğruluğu tavanı Sprint 2'den devam ediyor: laboratuvar %98.6, gerçek
  tarla fotoğrafı %61.9. Sınıf başına yaklaşık 75 saha fotoğrafı sınırı.

**Sonraki adımlar:**
- `yayin_hazirla.py` ve `Dockerfile` dosya listelerinin tek kaynaktan
  üretilmesi.
- Saha doğruluğunu artırmak için ek saha verisi toplanması.
- Öneri skorunun kırılım grafiği (hangi etken kaç puan) ve çevrimdışı açılış
  için PWA önbelleği.
- WhatsApp kanalı (ücretsiz kademedeki 15 dakikalık uyku sorunu çözüldüğünde).
