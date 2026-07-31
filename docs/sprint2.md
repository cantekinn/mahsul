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

<!-- 📸 Buraya Daily Scrum (WhatsApp) ekran görüntülerini ekleyin -->
<!-- <img width="900" alt="Daily Scrum WhatsApp" src="EKRAN_GORUNTUSU_LINKI" /> -->

---

### 3. Sprint Board Updates

Sprint başında "To Do" sütununda yer alan iş paketlerimizin tamamı tamamlanarak "Done" sütununa taşınmış ve Sprint 2 hedefimiz olan dört uzman agent'ın orkestrasyona canlı bağlanması başarıyla kapatılmıştır. Sprint sonu itibarıyla güncel Scrum Board görünümümüz şu şekildedir:

* **Done (5 Görev - 28 SP):** Hastalık teşhis CNN'i (EfficientNetV2-S + Grad-CAM, eğitildi), yabancı yaprağı reddeden "diğer" OOD sınıfı, treatments.yaml tedavi tabanlı teşhis agent'ı, FAO-56 sulama agent'ı, derece-gün zararlı agent'ı, kural tabanlı iklim riski agent'ı ve tüm agent'ları tek arayüzden yöneten LangGraph orkestratörü başarıyla tamamlanmıştır.
* **In Progress (0 Görev):** Bu sprintte devam eden kart kalmadı; hedeflere %100 ulaşıldı.
* **To Do (Sprint 3'e devir):** Karbon ayak izi agent'ı bilinçli olarak Sprint 3'e bırakılan bir stub olarak duruyor. Ayrıca narenciye/zeytin/muz için gerçek hastalık sınıfları, WhatsApp entegrasyonu ve çoklu parsel/premium bir sonraki sprintin backlog'una alındı.

<!-- 📸 Buraya Sprint Board (Miro / Trello) ekran görüntüsünü ekleyin -->
<!-- <img width="2936" alt="Sprint Board" src="EKRAN_GORUNTUSU_LINKI" /> -->

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

<!-- 📸 Buraya çalışan arayüz ve model çıktıları ekran görüntülerini ekleyin -->

**Çalıştırma:**
```bash
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

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
