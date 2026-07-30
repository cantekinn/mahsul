/**
 * Servis iscisi: uygulama KABUGUNU onbellege alir, VERIYI ASLA almaz.
 *
 * NEDEN VAR
 * Bu uygulama tarlada, zayif baglantida aciliyor. Her acilista kabuk
 * (index.html + JS + CSS + iki yazi tipi dosyasi) yeniden indiriliyordu.
 * Bunlar surum basina degismeyen, icerigi adiyla belirlenmis dosyalar;
 * agdan tekrar tekrar cekmenin hicbir karsiligi yok.
 *
 * NEDEN API ONBELLEGE GIRMIYOR
 * Uygulamanin soyledigi her sey bugunun havasi, bugunun toprak olcumu ve
 * bugunun hastalik teshisi. Bir gun onceki /oneri yanitini "calisiyor gibi
 * gostermek" icin geri vermek, ciftciye eski veriye dayanan bir karar
 * verdirir. Bozuk bir ekran, sessizce yanlis bir ekrandan iyidir.
 *
 * BU YUZDEN IZIN LISTESI, YASAK LISTESI DEGIL
 * Asagida yalnizca ADIYLA TANIDIGIMIZ dosyalar onbellege alinir. Yasak
 * listesi yazsaydik, yarin eklenen bir API ucu listeye yazilmayi unutuldugu
 * anda sessizce onbellege girerdi. Izin listesinde unutmanin cezasi
 * "onbellege girmedi"dir, "yanlis veri servis edildi" degil.
 *
 * BAYAT PAKET RISKI VE COZUMU
 * Servis iscisinin klasik tuzagi: yeni surum yayinlanir, kullanicinin
 * tarayicisi eski index.html'i onbellekten servis eder ve uygulama aylarca
 * guncellenmez. Burada index.html AG ONCELIKLI: cevrimici oldugu her an
 * sunucudan taze aliniyor, taze index.html de yeni karma adli dosyalari
 * isaret ediyor. Onbellekteki kopya SADECE ag yokken devreye giriyor.
 *
 * /assets/ ONBELLEK ONCELIKLI OLABILIR cunku Vite bu dosyalarin adina
 * icerik karmasini yaziyor (index-BjX3DmVt.css). Icerik degisirse ad da
 * degisir; ayni adin bayatlamasi mumkun degil.
 */

/* Onbellek adi. Degistirilirse acilista eski onbellek TAMAMEN silinir; bu,
   elde bir kurtarma dugmesi bulunmasi icin duruyor. Normal surum
   guncellemelerinde degistirilmesi GEREKMEZ: kabuk dosyalari karma adli
   oldugu icin bayatlayamaz, index.html zaten ag oncelikli. */
const ONBELLEK = "tarim-kabuk-v1";

/* Kok dizindeki degismez dosyalar. Vite bunlari public/'ten oldugu gibi
   kopyalar, yani adlarinda karma YOK; listeyi elle tutmak zorundayiz.
   public/ icine yeni bir dosya eklenirse buraya da yazilmali, yoksa
   cevrimdisi eksik kalir (eksik kalmasi zararsizdir, yanlis olmaz). */
const KOK_DOSYALAR = new Set([
  "/favicon.svg",
  "/icons.svg",
  "/icon-192.png",
  "/icon-512.png",
  "/icon-maskable-512.png",
  "/apple-touch-icon.png",
  "/manifest.webmanifest",
]);

/* Gezinme isteklerinin onbellekteki TEK anahtari. Uygulama tek sayfa: "/",
   "/?lat=40.1&lon=29.0" ve "/?g=teshis" sunucudan AYNI index.html'i alir.
   Istegin kendisini anahtar yapsaydik her farkli tarla icin ayri bir kopya
   birikir, onbellek sinirsiz buyurdu. */
const KABUK_ANAHTARI = "/";

self.addEventListener("install", (olay) => {
  // Bekleyen isci hemen devreye girsin. Gecikmenin bir faydasi olurdu:
  // acik sekmelerin ortasinda strateji degismezdi. Burada iki strateji de
  // (ag oncelikli gezinme, degismez varlik) sekmenin omru boyunca tutarli,
  // dolayisiyla beklemenin karsiligi yok.
  self.skipWaiting();
  olay.waitUntil(
    caches.open(ONBELLEK).then((onbellek) => onbellek.add(KABUK_ANAHTARI)),
  );
});

self.addEventListener("activate", (olay) => {
  olay.waitUntil(
    (async () => {
      const adlar = await caches.keys();
      await Promise.all(
        adlar.filter((a) => a !== ONBELLEK).map((a) => caches.delete(a)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (olay) => {
  const istek = olay.request;

  // GET disi hicbir sey. /teshis bir POST; buraya girmesi bile istenmiyor.
  if (istek.method !== "GET") return;

  const url = new URL(istek.url);

  // Baska kokenler (harita dosemeleri) dokunulmadan geciyor. Dosemeler
  // OpenStreetMap'in kendi onbellek basliklariyla yonetiliyor ve
  // kullanim kosullari toplu indirmeye izin vermiyor.
  if (url.origin !== self.location.origin) return;

  if (istek.mode === "navigate") {
    olay.respondWith(agOnce(istek));
    return;
  }

  if (url.pathname.startsWith("/assets/") || KOK_DOSYALAR.has(url.pathname)) {
    olay.respondWith(onbellekOnce(istek));
  }

  // Geri kalan her sey (yani API) hic ellenmiyor: respondWith cagrilmadigi
  // icin tarayici istegi normal yoluyla, onbelleksiz yapar.
});

/** index.html: once ag, olmazsa onbellekteki son kopya. */
async function agOnce(istek) {
  const onbellek = await caches.open(ONBELLEK);
  try {
    const yanit = await fetch(istek);
    if (yanit.ok) {
      const kopya = yanit.clone();
      await onbellek.put(KABUK_ANAHTARI, kopya.clone());
      await eskileriBuda(onbellek, kopya);
    }
    return yanit;
  } catch (hata) {
    const eski = await onbellek.match(KABUK_ANAHTARI);
    if (eski) return eski;
    // Onbellekte de yoksa hata yutulmuyor: tarayicinin kendi "baglanti yok"
    // ekrani, bizim uyduracagimiz bos sayfadan daha dogru bir bilgi verir.
    throw hata;
  }
}

/**
 * Onceki surumden kalan paket dosyalarini siler.
 *
 * NEDEN GEREKLI: karma adli dosyalar bayatlamaz ama BIRIKIR. Her yayin ~390 KB
 * JS ve ~43 KB CSS ekliyor (olculdu); temizlenmezse onbellek surum sayisiyla
 * dogru orantili buyur. Kullanicinin telefonundaki yeri "eski surumler icin"
 * harcamanin bir karsiligi yok, hicbiri bir daha istenmeyecek.
 *
 * NEDEN SADECE .js VE .css: bu iki tur index.html'in ICINDE adiyla geciyor,
 * yani taze HTML "hangileri hala gerekli" sorusunun tam cevabini veriyor.
 * Yazi tipleri HTML'de gecmez (CSS'ten yuklenirler) ve adlari surumler
 * arasinda degismez; onlari da budamaya sokmak, her yayinda 133 KB'lik yazi
 * tipini bos yere yeniden indirtirdi.
 */
async function eskileriBuda(onbellek, htmlYaniti) {
  const html = await htmlYaniti.text();
  const gerekli = new Set(
    [...html.matchAll(/\/assets\/[\w.-]+\.(?:js|css)/g)].map((e) => e[0]),
  );
  const anahtarlar = await onbellek.keys();
  await Promise.all(
    anahtarlar.map((anahtar) => {
      const yol = new URL(anahtar.url).pathname;
      if (!/^\/assets\/.+\.(js|css)$/.test(yol)) return undefined;
      if (gerekli.has(yol)) return undefined;
      return onbellek.delete(anahtar);
    }),
  );
}

/** Karma adli varliklar: onbellekte varsa oradan, yoksa agdan ve saklanir. */
async function onbellekOnce(istek) {
  const onbellek = await caches.open(ONBELLEK);
  const bulunan = await onbellek.match(istek);
  if (bulunan) return bulunan;
  const yanit = await fetch(istek);
  // Sadece 200 saklaniyor. StaticFiles(html=True) bilinmeyen yolda
  // index.html donuyor; bu yanit da 200 olur ama zaten var olmayan bir
  // varlik icin istek atilmiyor, bu yol pratikte bos.
  if (yanit.ok) await onbellek.put(istek, yanit.clone());
  return yanit;
}
