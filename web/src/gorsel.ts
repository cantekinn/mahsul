/**
 * Yukleme oncesi tarayicida fotograf kucultme ve yon duzeltme.
 *
 * NEDEN KUCULTUYORUZ: bu bir ciftci uygulamasi ve tarlada baglanti genelde
 * mobil. Telefon kamerasi 3-5 MB JPEG uretiyor; kirsal baglantida bunu
 * yuklemek uzun surer ve 6 MB sunucu tavanina takilabilir.
 *
 * NEDEN DOGRULUK KAYBI YOK: model girdiyi zaten kisa kenari 224 piksele
 * indirip 224x224 kirpiyor (classifier_onnx._preprocess_bytes). 1280 piksellik
 * uzun kenar, 4:3 bir fotografta 960 piksellik kisa kenar demek; modelin
 * istedigi 224'un dort kati. Yani atilan pikselleri model hicbir kosulda
 * gormeyecekti.
 *
 * YAN FAYDA, EXIF DONUKLUGU: telefonlar fotografi fiziksel olarak dondurmez,
 * donme bilgisini EXIF Orientation etiketinde tutar. Sunucudaki
 * PIL.Image.open() bu etiketi UYGULAMAZ; yani yan tutularak cekilmis bir
 * fotograf modele yan gidiyordu. createImageBitmap(..., {imageOrientation:
 * "from-image"}) donusu uygular ve canvas ciktisinda EXIF hic bulunmaz, boylece
 * sunucu her zaman dogru yonu gorur. Bu, kucultmeden bagimsiz bir duzeltme.
 */

/** Uzun kenar ust siniri. Modelin ihtiyaci 224; 1280 genis bir emniyet payi. */
const MAX_KENAR = 1280;

/** JPEG kalitesi. 0.85 gozle farkedilmeyen, boyutu ~4 kat dusuren nokta. */
const KALITE = 0.85;

/**
 * Fotografi kucultur ve EXIF donusunu uygular.
 *
 * HATA DURUMUNDA ORIJINALI DONER: eski bir tarayici createImageBitmap
 * secenegini desteklemiyorsa kullaniciyi engellemek yerine dosyayi oldugu gibi
 * gondeririz. Sunucudaki 6 MB kontrolu son savunma olarak zaten duruyor.
 */
export async function kucult(dosya: File): Promise<File> {
  try {
    const bitmap = await createImageBitmap(dosya, { imageOrientation: "from-image" });
    const { width: g, height: y } = bitmap;

    // Olcek 1'i gecmez: kucuk fotografi buyutmek bilgi eklemez, sadece boyut sisirir.
    const olcek = Math.min(1, MAX_KENAR / Math.max(g, y));
    const yeniG = Math.round(g * olcek);
    const yeniY = Math.round(y * olcek);

    const tuval = document.createElement("canvas");
    tuval.width = yeniG;
    tuval.height = yeniY;
    const ctx = tuval.getContext("2d");
    if (!ctx) {
      bitmap.close();
      return dosya;
    }
    ctx.drawImage(bitmap, 0, 0, yeniG, yeniY);
    bitmap.close();

    const blob = await new Promise<Blob | null>((coz) =>
      tuval.toBlob(coz, "image/jpeg", KALITE),
    );
    if (!blob) return dosya;

    // Yeniden kodlama nadiren dosyayi BUYUTUR (zaten agresif sikistirilmis
    // kucuk bir JPEG'de olur). O durumda orijinali korumak daha dogru; ama
    // yon duzeltmesi gerekiyorsa (olcek 1 degilse zaten kuculttuk) yeni
    // dosyayi tutariz.
    if (blob.size >= dosya.size && olcek === 1) return dosya;

    return new File([blob], _jpgAdi(dosya.name), {
      type: "image/jpeg",
      lastModified: Date.now(),
    });
  } catch {
    // createImageBitmap secenegi yok, bozuk dosya, bellek yetersiz vb.
    return dosya;
  }
}

/** "IMG_0421.HEIC" -> "IMG_0421.jpg". Cikti her zaman JPEG. */
function _jpgAdi(ad: string): string {
  const nokta = ad.lastIndexOf(".");
  return (nokta > 0 ? ad.slice(0, nokta) : ad) + ".jpg";
}
