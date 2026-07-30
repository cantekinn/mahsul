# Tarım Asistanı

Dünyanın herhangi bir koordinatı için toprak, iklim, tarım parselleri ve
ürün önerisi. Haritada bir noktaya tıklayın.

Üç sekme var:

- **Ürün önerisi**: seçili noktada ne yetişir (FAO EcoCrop + SoilGrids + iklim
  normali).
- **Tarla takvimi**: aynı nokta için FAO-56 sulama ihtiyacı, 16 günlük iklim
  riski ve derece-gün ile zararlı evresi.
- **Hastalık teşhisi**: yaprak fotoğrafından 45 sınıflı teşhis ve tedavi
  önerisi (sunucuda ONNX, PyTorch yok).

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

## Uç noktalar

`/docs` adresinde tamamı var. Arayüz aynı adresten sunuluyor, bu yüzden
CORS devreye girmiyor. Sağlık yoklaması: `/saglik`.
