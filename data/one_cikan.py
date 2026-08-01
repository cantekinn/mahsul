"""Onceden isitilan "one cikan tarim bolgeleri" listesi.

NEDEN VAR
=========
Ucretsiz barindirmada disk her yeniden baslatmada silinir, yani onbellek
kaybolur ve her tiklama soguk olur (olculdu: toprak 3-6 s, parsel 25 s'ye
kadar). Cozum bu noktalarin onbellegini depoya GOMMEK.

BU LISTENIN SINIRI ACIKCA SOYLENMELIDIR
=======================================
Onbellek anahtari koordinati 2 ondaliga yuvarlar, yani yaklasik 1 km'lik bir
hucreye. Dunyanin kara yuzeyi ~149 milyon km2; birkac yuz noktayi isitmak
rastgele bir tiklamayi yakalamaz. Yani bu liste "uygulamayi hizlandirmaz",
SADECE buradaki noktalarin aninda gelmesini saglar. Arayuzde de tam olarak bu
sekilde sunulur: hizli erisim kisayollari olarak, "populer" ya da "onerilen"
diye degil.

KOORDINATLAR NIYET BEYANIDIR, ETIKET DEGIL
==========================================
Buradaki "ad" alani sadece benim not dusmemdir. Uygulamanin gosterdigi yer adi
her zaman OpenStreetMap'ten gelir. Kendi etiketimi veri diye sunmam, cunku
koordinati yanlis yazmis olabilirim ve o yanlis sessizce dogru gibi gorunur.
"""
from __future__ import annotations

# (benim notum, lat, lon) - gorunen ad OSM'den gelir
#
# NOT ALANI TURKCE KARAKTERLIDIR cunku dogrudan dugmenin uzerinde yaziliyor.
# Kaynak kodun geri kalaninda ASCII kullaniyorum (Windows konsolu cp1254'te
# cokuyor), ama KULLANICIYA GORUNEN metinde kisaltilmis Turkce yazmam.
# Konsola basarken scripts/onbellek_isit.py bu satirlari zaten temizliyor.
ONE_CIKANLAR: list[tuple[str, float, float]] = [
    # Turkiye
    ("Antalya - Aksu ovası", 36.92, 30.83),
    ("Konya ovası", 38.10, 32.80),
    ("Çukurova - Adana", 37.00, 35.50),
    ("Şanlıurfa - Harran ovası", 36.90, 39.00),
    ("Manisa - Gediz ovası", 38.60, 27.60),
    # Koordinat 2 ondalikta yaziliyor cunku onbellek anahtari da 2 ondalik
    # (bkz. data/open_meteo.py). Daha fazla basamak yazmak dugmeyi isitilan
    # hucrenin disina dusurebilirdi; kazanci ~18 m, bedeli soguk istek.
    ("Bursa - Nilüfer ovası", 40.17, 28.80),
    ("Amasya - Yeşilırmak", 40.60, 35.90),
    ("Bafra ovası - Samsun", 41.50, 35.90),
    ("Iğdır ovası", 39.90, 44.00),
    # Akdeniz havzasi
    ("Endülüs - Sevilla", 37.40, -5.90),
    ("Po ovası - İtalya", 45.10, 10.80),
    ("Provence - Fransa", 44.13, 4.81),
    ("Nil deltası - Mısır", 30.80, 31.00),
    ("Bekaa vadisi - Lübnan", 33.85, 35.90),
    # Bati ve Orta Avrupa
    ("Beauce - Fransa", 48.20, 1.80),
    ("Flevoland - Hollanda", 52.50, 5.60),
    ("Macaristan ovası", 46.90, 20.20),
    # Kuzey Amerika
    ("Iowa - ABD Ortabatı", 42.03, -93.63),
    ("Kansas buğday kuşağı", 38.50, -98.30),
    ("Central Valley - Kaliforniya", 36.70, -119.80),
    ("Alberta - Kanada", 52.20, -113.50),
    # Guney Amerika
    ("Pampa - Arjantin", -34.60, -61.20),
    ("Santa Fe - Arjantin", -30.42, -61.63),
    ("Sao Paulo şeker kamışı", -21.17, -47.81),
    ("Mendoza bağları", -33.02, -68.79),
    # Afrika
    ("Nakuru - Kenya", -0.30, 36.08),
    ("Etiyopya yaylaları", 9.00, 38.70),
    ("Kaduna - Nijerya", 10.30, 7.80),
    ("Free State - Güney Afrika", -28.50, 26.80),
    # Asya
    ("Pencap - Hindistan", 30.55, 75.60),
    ("Ganj ovası - Uttar Pradesh", 26.80, 80.90),
    ("Fergana vadisi - Özbekistan", 40.55, 71.60),
    ("Kuzey Çin ovası", 35.50, 114.50),
    ("Mekong deltası - Vietnam", 10.00, 105.80),
    ("Java pirinç tarlaları", -7.30, 110.40),
    ("Hokkaido - Japonya", 43.30, 141.80),
    # Okyanusya
    ("Riverina - Avustralya", -34.75, 146.05),
    ("Canterbury - Yeni Zelanda", -43.80, 172.00),
]
