# Sprint 1 Raporu

**Bootcamp:** Google YZTA 2026 - 14. Grup (Yapay Zeka)
**Proje:** Kucuk ciftci icin cok agentli AI tarim danismani
**Kalkinma hedefleri (SDG):** 1 Yoksulluga Son, 2 Acliga Son, 13 Iklim Eylemi
**Sprint suresi:** 22 Haziran - 5 Temmuz 2026 (2 hafta)
**Takim:** Can Tekin, Ozlem, Sila (3 kisi)

---

## 1. Urun / Proje Ozeti

Kucuk olcekli ciftcilerin uretim kararlarini ucretsiz ve acik verilerle
destekleyen, birden cok uzman agent'in ortak hafiza uzerinden calistigi bir
tarim danismani. Ciftci parselini tanitir (koordinat ya da MEGSIS ada/parsel),
sistem o konumun toprak ve iklim profilini cikarir; kural tabanli oneri motoru
ekilebilecek en uygun urunleri gerekcesiyle siralar. Cekirdek ozellikler
ucretsizdir (SDG), ileri analiz (toprak analizi N/P/K hassasiyeti, coklu parsel,
B2B) premium olarak konumlanir.

**Neden bu proje:** Girdi maliyeti, yanlis urun secimi ve iklim riski kucuk
ciftcinin gelirini dogrudan vurur. Pahali veri satin almadan, yalnizca acik
kaynaklarla (Open-Meteo, SoilGrids, TKGM/MEGSIS, NASA POWER) gercek bir karar
destegi kurulabilir. Bu yuzden proje hem hayat gecirilebilir hem dusuk
maliyetlidir.

---

## 2. Sprint 1 Hedefi

> "Bir parseli tanitinca o konumun toprak ve iklim profilini cikarip, kural
> tabanli bir motorla gerekcelendirilmis urun onerisi ureten uctan uca calisan
> bir demo iskeleti."

Yani Sprint 1'de amaC: **veri altyapisi + oneri motoru + orkestrasyon iskeleti +
calisan demo arayuzu**. Diagnoz/sulama/iklim riski gibi diger agent'lar sonraki
sprintlere birakildi (bilinçli kapsam sinirlamasi).

---

## 3. Backlog ve Puanlama (Story Points)

Puanlama Fibonacci (1,2,3,5,8) ile yapildi. Referans (1 puan) = tek dosyalik,
dis bagimliligi olmayan yardimci fonksiyon.

| # | Is (User Story) | Sorumlu | Puan | Durum |
|---|-----------------|---------|------|-------|
| 1 | Repo iskeleti + config + veri semalari (pydantic) | Can | 3 | Done |
| 2 | LangGraph orkestrator + niyet yonlendirici + agent state | Can | 5 | Done |
| 3 | Open-Meteo iklim istemcisi (son 1 yil ozeti) | Can | 3 | Done |
| 4 | SoilGrids toprak istemcisi (pH, azot, tekstur) | Can | 3 | Done |
| 5 | MEGSIS GeoJSON cozumleme (merkez koordinat + alan) | Ozlem | 5 | Done |
| 6 | Yerel parsel dosya yukleyici (indirilmis TKGM JSON) | Ozlem | 3 | Done |
| 7 | SQLite tarla hafizasi (profil kaydet/getir) | Ozlem | 5 | Done |
| 8 | Ornek parsel tohumlama scripti + veri seti | Ozlem | 3 | Done |
| 9 | Antalya bilgi tabani (crop_params.yaml) | Sila | 3 | Done |
| 10 | Kural tabanli urun oneri motoru (skor + gerekce) | Sila | 5 | Done |
| 11 | GBDT modeli egitimi (Kaggle Crop Recommendation) | Sila | 5 | Done |
| 12 | GBDT ikinci gorus entegrasyonu | Sila | 3 | Done |
| 13 | Streamlit demo arayuzu (uctan uca akis) | Birlikte | 5 | Done |

**Toplam planlanan:** 51 puan
**Tamamlanan:** 51 puan
**Sprint hedefine ulasma:** %100

**Backlog dagitma mantigi:** Isler uc ana katmana ayrildi: (a) veri toplama ve
orkestrasyon iskeleti Can'da, (b) parsel/mekan ve hafiza katmani Ozlem'de,
(c) yapay zeka/oneri katmani Sila'da. Arayuz herkesin ciktisini birlestirdigi
icin "birlikte" isi olarak tutuldu. Boylece her uye baska bir klasorde calisti,
GitHub'da cakisma yasanmadan paralel ilerlendi.

---

## 4. Daily Scrum Notlari

Ilk hafta uyelerin final sinav donemine denk geldigi icin toplanti ritmi
dusuktu; ikinci hafta gunluk async (WhatsApp) + haftada 2 sesli toplanti ile
yurutuldu. Ozet notlar:

**23 Haziran (Pzt):** Kapsam netlestirildi. Karar: Sprint 1 sadece urun onerisi
uctan uca calissin; diagnoz/sulama sonraki sprint. Il olarak Antalya secildi
(en fazla acik veri ve hedef urun ortusmesi).

**25 Haziran (Car):** Can - schemas ve config hazir, orchestrator iskeleti kuruldu
ve 3 test sorgusu dogru yonlendi. Ozlem - MEGSIS GeoJSON yapisi cozuldu, alan +
merkez hesabi test edildi. Sila - crop_params.yaml ilk 6 urunle dolduruldu.

**28 Haziran (Cmt):** Can - Open-Meteo ve SoilGrids istemcileri canli Antalya
koordinatiyla test edildi, veri geliyor. Ozlem - SQLite tarla hafizasi
kaydet/getir calisiyor. Sila - kural motoru skorlama + gerekce ureten hale geldi.

**1 Temmuz (Sal):** TKGM'den 4 ilceye ait ~49 parsel JSON indirildi (sorgu
limiti icinde), parcel_files yukleyici bunlari dogrudan okuyor. GBDT modeli
egitildi, ikinci gorus olarak arayuze baglandi.

**3-4 Temmuz:** Streamlit arayuzu tum parcalari birlestirdi. Uctan uca akis
(parsel sec -> veri getir -> oneri -> hafizaya kaydet) dogrulandi. Dokumantasyon
ve Sprint Review hazirligi.

> Kanit: WhatsApp grup ekran goruntuleri (SS1-SS4) ekte.

---

## 5. Sprint Board Durumu

| To Do | In Progress | Done |
|-------|-------------|------|
| (Sprint 2) Hastalik teshis CNN | - | Repo + orchestrator iskeleti |
| (Sprint 2) Sulama agent (FAO-56) | - | Open-Meteo + SoilGrids istemcileri |
| (Sprint 2) Iklim riski (don/kurak) | - | MEGSIS parsel cozumleme |
| (Sprint 2) WhatsApp entegrasyonu | - | SQLite tarla hafizasi |
| (Sprint 2) LLM danisman (RAG) | - | Kural tabanli oneri motoru |
| | | GBDT ikinci gorus |
| | | Streamlit demo arayuzu |

Sprint 1 sonunda In Progress bos; tum planlanan isler Done.

> Kanit: Trello/Notion board ekran goruntusu (SS5) ekte.

---

## 6. Urun Durumu (Product Status)

Su an calisan ozellikler:

1. **Parsel tanitma - 2 yol:** (a) indirilmis MEGSIS parsel dosyalarindan secim
   (Aksu, Serik/Bogazkent, Alanya/Turkler, Gazipasa/Beyobasi), (b) elle koordinat.
2. **Otomatik toprak profili:** SoilGrids'ten pH, azot, kil/kum/silt, organik
   karbon (0-5 cm).
3. **Otomatik iklim profili:** Open-Meteo arsivinden son ~1 yil ortalama
   sicaklik, nem, yillik yagis.
4. **Urun onerisi:** kural tabanli motor en uygun 4 urunu skor + uygunluk +
   faktor bazli gerekce ile siralar.
5. **GBDT ikinci gorus:** Kaggle veri setinde egitilmis model destekleyici
   tahmin verir (birincil karar kural motorunda kalir).
6. **Tarla hafizasi:** parsel + toprak + iklim SQLite'a kaydedilir, sonraki
   oturumda hatirlanir.
7. **Orkestrasyon iskeleti:** LangGraph niyet yonlendirici, gelen soruyu dogru
   agent'a yonlendirir (diger agent'lar Sprint 2'de icerikle dolacak stub).

> Kanit: Uygulama ekran goruntuleri (SS6-SS8) ekte.

Calistirma:
```
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

---

## 7. Sprint Review

Sprint 1 hedefi olan "uctan uca calisan urun onerisi demosu" tam olarak
teslim edildi. Bir parsel secildiginde sistem gercek acik verilerle o konumun
toprak/iklim profilini cikariyor ve gerekcelendirilmis urun onerisi veriyor.
Iki bagimsiz veri kaynagi (toprak, iklim) hata toleransli baglandi: biri
kesilse digeri yine sonuc uretiyor. Mimari katmanli (core/data/memory/models/
agents/app) oldugu icin Sprint 2 agent'lari mevcut iskelete takilarak eklenecek.

**Demoda gosterilecek senaryo:** Serik ovasindan bir parsel sec -> sicak kiyi
iklimi + toprak profili gelir -> domates/biber ust siralarda; ardindan Elmali
(yayla) parseli sec -> serin iklim -> patates one cikar. Ayni motorun konuma
gore farkli oneri uretmesi gosterilir.

---

## 8. Sprint Retrospective

**Iyi giden:**
- Katmanli klasor yapisi sayesinde 3 kisi cakismadan paralel calisti.
- Tum veri ucretsiz ve acik kaynaklardan; proje sifira yakin maliyetle
  hayata gecirilebilir durumda (SDG hedefiyle uyumlu).
- Kapsam bilincli sinirlandi; "eklemek icin eklenen" ozellik yok, her parca
  Sprint 1 hedefine hizmet ediyor.

**Zorlanilan / gelistirilecek:**
- Ilk hafta final sinavlariyla cakisti, aktif calisma 2. haftaya sikisti.
  Aksiyon: Sprint 2'de ilk gunden gunluk async check-in.
- SoilGrids bazi kiyi/kentsel hucrelerde veri dondurmuyor. Aksiyon: uyari
  mesaji eklendi; Sprint 2'de NASA POWER ile yedekleme dusunulecek.
- TKGM canli sorgu limiti var. Aksiyon: parseller yerel dosyadan okunuyor;
  ileride resmi erisim/izin arastirilacak.

**Sprint 2 aksiyonlari:**
- Yaprak fotografindan hastalik teshisi (CNN transfer ogrenme).
- Sulama agent (FAO-56 Penman-Monteith, fizik tabanli).
- Iklim riski agent (don/kurak uyarisi).
- Danisman agent (RAG + LLM, Turkce).

---

## Ekler
- SS1-SS4: Daily Scrum (WhatsApp) ekran goruntuleri
- SS5: Sprint Board (Trello/Notion)
- SS6-SS8: Uygulama ekran goruntuleri
