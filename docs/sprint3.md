## Sprint 3 Raporu

**Bootcamp:** Google YZTA 2026 - 14. Grup (Yapay Zeka)
**Proje:** Küçük çiftçi için çok agentli yapay zeka tarım danışmanı
**Kalkınma hedefleri (SDG):** 1 Yoksulluğa Son, 2 Açlığa Son, 13 İklim Eylemi
**Sprint süresi:** 21 Temmuz - 3 Ağustos 2026 (2 hafta)
**Takım:** Can Tekin, Özlem, Sıla (3 kişi)
**Canlı adres:** https://mahsul-ulro.onrender.com

---

### 1. Sprint 3 İçinde Yer Alan Konuların Belirlenmesi ve Bağlantı Kurulması

Sprint 3 için planlanan iş hacmi **34 SP** olarak belirlendi. Sprint 1 ve 2'nin
sonunda elimizde çalışan ama **yalnızca yerel makinede** çalışan bir sistem
vardı: hastalık modeli eğitilmişti fakat webde yoktu, dört uzman agent
orkestratöre bağlıydı fakat arayüzde karşılığı yoktu. Bu sprintin tek hedefi
belirlendi: **her şey gerçek bir kullanıcının açabileceği bir adreste
çalışacak.** Bir özellik canlıda çalışmıyorsa bu sprintte "Done" sayılmadı.

| İş / Görev | SP | Sorumlu | Durum |
| :--- | :---: | :---: | :---: |
| Hastalık teşhisini webe alma (PyTorch -> ONNX, `/teshis` + Teşhis sekmesi) | 6 | Sıla | Done |
| Ürün kapsamını 45 sınıf / 16 ürüne genişletme (yeniden eğitim) | 5 | Sıla | Done |
| FAO GAEZ v4 ile öneri skorunun kalibrasyonu | 4 | Can | Done |
| Sprint 2 agent'larını webe alma (`/sulama`, `/iklim-riski`, `/zararli` + Tarla takvimi) | 5 | Özlem | Done |
| Karbon ayak izi agent'ının gerçeklenmesi (IPCC 2019 Tier 1, `/karbon`) | 3 | Özlem | Done |
| Serbest metin soru yönlendirici (`/sor`) ve kapsam şeffaflığı (`/kapsam`) | 3 | Can | Done |
| Tapu parseli seçici (48 gerçek TKGM kaydı) + Tarlalarım | 2 | Can | Done |
| Tasarım sistemi (tipografi/boşluk jetonları, odak halkası, form denetimleri) | 2 | Özlem | Done |
| Otomatik test paketi (`tests/`, pytest) | 2 | Can | Done |
| Toprak besin karnesi (`/besin`) | 1 | Can | Done |
| Sezon günlüğü ve hafızanın cevaba bağlanması (`/gunluk`) | 1 | Can | Done |

**Toplam planlanan:** 34 SP &nbsp;|&nbsp; **Tamamlanan:** 34 SP &nbsp;|&nbsp; **Sprint hedefine ulaşma:** %100

**Teknik tercih notu (dürüstlük):** Bu sprintte alınan kararların çoğu "ne
ekleyelim" değil "neyi eklemeyelim" kararıydı ve hepsi ölçüme dayandı; ölçümler
5. bölümdeki tabloda.

---

### 2. Daily Scrum Notları

Asenkron model korundu; ilerlemeler WhatsApp kanalında Can (SM) koordinasyonunda
yazılı aktarıldı. Bu sprintte tartışmaların merkezinde **Render ücretsiz
kademesinin 512 MB RAM sınırı** vardı: her yeni özellik önce "canlıda sığar mı"
sorusundan geçti.

* **Can (Scrum Master / Developer):** "Öneri skorunu FAO GAEZ v4 uygunluk
  ızgarasıyla kalibre ettim; artık skor bizim uydurduğumuz bir ağırlık değil,
  FAO'nun ölçtüğü uygunlukla hizalı. Serbest metin soru kutusunu yazdım:
  çiftçinin cümlesi hangi hesabın işiyse oraya gidiyor, gitmiyorsa doğru sekmeye
  yönlendiriyor. 48 gerçek tapu parselini seçilebilir hale getirdim; kullanıcı
  haritada gözle tarla aramak yerine kendi kaydını seçiyor, alan da tapudan
  geliyor. Sprint sonunda pytest paketini kurdum ve sezon günlüğünü bağladım.
  Beklediğim tek şey Sıla'nın ONNX çıktısının boyutu: model imaja sığmazsa
  öneri motorunu da beraberinde düşürür, o yüzden önce onu ölçüp sonra kalan
  bütçeye göre ilerliyorum."
* **Sıla (Product Owner / Developer):** "Modeli 45 sınıf / 16 ürüne genişletip
  Colab GPU'da yeniden eğittim. Asıl iş modeli webe sokmaktı: PyTorch canlı
  imaja sığmıyordu, ONNX'e çevirdim ve `onnxruntime` ile torch'suz çıkarım
  yaptım. Grad-CAM torch geri yayılımı istediği için canlıda yerine sınıf
  aktivasyon ağırlıklarını (`cam_agirlik.npy`) önceden çıkarıp forward-only ısı
  haritası ürettim. Teşhis sekmesi mobilde doğrudan kamerayı açıyor. Açık
  kalan bir konu var: saha doğruluğu Sprint 2'deki tavanda duruyor, bunu bu
  sprintte kapatamayacağız, sınıf başına daha fazla gerçek tarla fotoğrafı
  gerekiyor."
* **Özlem (Developer):** "Sprint 2'de yazdığımız üç agent'ı üç uç noktaya ve tek
  bir Tarla takvimi sekmesine bağladım. Kc kapsamını FAO-56 Tablo 12'den 84
  ürüne çıkardım. Karbon agent'ının stub'ını IPCC 2019 Tier 1 emisyon
  faktörleriyle gerçekledim. Sprint sonunda tasarım sistemini kurdum: tipografi
  ve boşluk jetonları, tek bir odak halkası, dokunmatikte 44 piksel hedefler.
  Can'dan kapsam uç noktasına karbon kaleminin de eklenmesini bekliyorum, yoksa
  kullanıcı neyin hesaplandığını tek yerden göremiyor."

---

### 3. Sprint Board Updates

* **Done (11 Görev - 34 SP):** Yukarıdaki tablonun tamamı canlıya alındı ve
  https://mahsul-ulro.onrender.com adresinde çalışıyor.
* **In Progress (0 Görev):** Bu sprintte devam eden kart kalmadı.
* **To Do (bilinçli olarak alınmayanlar):** Freemium/ödeme duvarı ve Chroma
  vektör hafıza backlog'dan **çıkarıldı** (gerekçeleri 5. bölümde). WhatsApp
  entegrasyonu ertelendi.

---

### 4. Ürün Durumu (Product Status)

Sprint 3 kapanışında sistem, tarayıcıdan açılan tek bir servis. Üç sekme var ve
her sekme kendi hesabını gerçek ölçülmüş veriyle yapıyor.

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
| Haritadaki hazır tarım noktası | **38** |
| Otomatik test | **332** |

**Sekme sekme ne var:**

* **Ürün önerisi:** Dünyanın herhangi bir noktasına tıklanır. Konum, toprak
  (SoilGrids), parsel ve öneri katmanları **ayrı ayrı** yüklenir; ekran en yavaş
  katmanın hızına inmez. Skor FAO GAEZ v4 uygunluk ızgarasıyla kalibre.
* **Tarla takvimi:** Sulama (FAO-56), iklim riski (16 günlük tahmin), zararlı
  (derece-gün), karbon ayak izi (IPCC 2019 Tier 1), toprak besin karnesi ve
  sezon günlüğü kartları.
* **Hastalık teşhisi:** Yaprak fotoğrafı yüklenir veya mobilde doğrudan çekilir.
  ONNX çıkarımı, kademeli güven (kesin / olası / belirsiz / tanımsız), sınıf
  aktivasyon ısı haritası ve tedavi kartı.
* **Soru kutusu (her sekmede):** Serbest cümle doğru uzmana gider; gitmiyorsa
  doğru sekmeye yönlendirir. "Anlamadım" demez.

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

Aynı `son_sulama` tarihi `/sor` uç noktasına da gider; sulama sorusuna verilen
plan **değişmez**, üzerine biriken açık cümlesi eklenir.

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

---

### 5. Sprint Review

Sprint hedefi olan "her şey canlıda çalışacak" maddesi tam teslim edildi.
Sprint 1 ve 2'de yazılan hiçbir hesap yerelde kalmadı.

**Bu sprintte REDDEDİLEN işler ve ölçülmüş gerekçeleri.** Bunlar "yetişmedi"
değil, "ölçtük ve almamaya karar verdik" kalemleri:

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
kırar"** kuralı, bu sprintte özellik eklemek kadar özellik reddetmek için de
kullanıldı.

**Demo senaryosu:** Tapu kaydını listeden seç (nokta ve alan birlikte kurulur)
-> ürün önerisi listesi -> Tarla takvimi sekmesinde sulama, iklim riski,
zararlı, karbon ve besin kartları -> günlüğe sulama tarihi yaz, biriken su açığı
kartı belirir -> Teşhis sekmesinde yaprak fotoğrafı yükle, teşhis + ısı haritası
+ tedavi -> soru kutusuna "domatese kaç litre su vermeliyim" yaz, plan ve
günlükten gelen birikmiş açık birlikte gelsin.

---

### 6. Sprint Retrospective

**İyi giden yönler:**
- "Canlıda çalışmıyorsa Done değil" kuralı, sprint boyunca tek ölçüt oldu ve
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
  GBDT) canlıya alınmasını engelledi. İkisinin de yerine geçen çözüm bulundu
  ama bu, planlanandan fazla iş demekti.
- `scripts/yayin_hazirla.py` ile `Dockerfile` arasındaki dosya listesi tek yönlü
  kontrol ediliyor: biri güncellenip diğeri unutulursa imaj eksik dosyayla
  kurulabilir. Şimdilik duman testi bu boşluğu kapatıyor, ama iki listenin tek
  kaynaktan üretilmesi gerekiyor.
- Sezon günlüğü koordinat hücresine (3 ondalık, ~110 m) bağlı. 300 m ötedeki bir
  tıklama boş günlük gösterir. 2 ondalığa (~1.1 km) çıkarmak komşu tarlaları
  birleştirir ve **başkasının sulama tarihinden yanlış bir açık** hesaplardı;
  boş günlük görmek buna tercih edildi. Bilinen ve kabul edilmiş sınır.

---

### 7. Kapanış

Sprint 3 bootcamp sürecinin son sprintidir. Üç sprintte planlanan 93 SP'nin
tamamı teslim edildi ve ürün kurulum gerektirmeden açılabilen bir adreste
çalışıyor: **https://mahsul-ulro.onrender.com**

Teslim ettiğimiz sınırları gizlemiyoruz: saha fotoğrafı doğruluğu %61.9,
gübre dozu hesaplanamadığı için verilmiyor, sezon günlüğü 110 metrelik
koordinat hücresine bağlı, WhatsApp kanalı ücretsiz barındırmanın uyku
davranışı yüzünden açılmadı. Hepsinin gerekçesi ölçülmüş ve 5. bölümdeki
tabloda yazılı.

Ürünün tamamı açık veriyle çalışıyor: lisanslı veri seti, ödemeli API ve LLM
çağrısı yok. Kullanıcı başına maliyet sıfır olduğu için çiftçinin ödemesi
gereken bir şey de yok. SDG 1, 2 ve 13 ile kurduğumuz bağ tam olarak burada.
