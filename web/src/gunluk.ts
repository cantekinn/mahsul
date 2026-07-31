/**
 * Sezon gunlugu: ciftcinin kendi tarlasinda ne yaptigini tuttugu kayit.
 *
 * NEDEN TARAYICIDA: Tarlalarim listesiyle ayni gerekce (bkz TarlaPaneli.tsx
 * useTarlalarim yorumu). Ucretsiz barindirma katmaninda sunucu diski kalici
 * degil; oraya yazilan gunluk her uyku sonrasi silinirdi ve "hatirliyorum"
 * diyip hatirlamayan bir hafiza, hic hafiza olmamasindan kotu olurdu.
 *
 * HESAP SUNUCUDA. Bu dosya yalnizca SAKLAR. Kayitlardan cikan sayilar
 * (su acigi, tekrar eden hastalik) knowledge/gunluk.py'de hesaplanip test
 * ediliyor; ayni mantigin ikinci bir kopyasini TypeScript'te yazmak, iki
 * kopyanin zamanla ayrismasi demekti.
 *
 * KAPSAM: kayitlar KOORDINATA baglidir, tarla ADINA degil. Sebep, arayuzde
 * "su an acik olan tarla" diye bir kavramin olmamasi: kullanici haritaya
 * serbestce tiklayabiliyor, kayitli tarlayi yuklemek sadece kutulari
 * dolduruyor. Koordinat ise her durumda var.
 *
 * KABUL EDILEN SINIR: anahtar 3 ondalige yuvarlanir, yani ~110 m'lik bir
 * hucre "ayni tarla" sayilir. Haritaya 300 m oteye tiklayan kullanici bos
 * bir gunluk gorur. Bunu duzeltmek parsel siniri cizimi veya hesap sistemi
 * ister; ikisi de bu surumde yok. Yuvarlamayi buyutmek (2 ondalik, ~1.1 km)
 * ters hataya yol acardi: komsu iki tarlanin gunlugu birbirine karisir ve
 * yanlis sulama tarihiyle yanlis su acigi hesaplanirdi. Bos gunluk gormek,
 * baskasinin gunlugunu gormekten iyidir.
 */
import { useCallback, useState } from "react";

export type GunlukTur = "sulama" | "gubre" | "ilac" | "teshis" | "ekim" | "hasat";

export type GunlukKaydi = {
  /** Silme icin kimlik. Tarih tek basina yetmez: ayni gun iki kayit olabilir. */
  id: string;
  /** Hucre anahtari, "40.220,28.850" bicimi. */
  yer: string;
  /** YYYY-AA-GG. Sunucu bu bicimi bekliyor (date.fromisoformat). */
  tarih: string;
  tur: GunlukTur;
  /** Teshiste model etiketi, ilacta ilac adi. Sunucu tekrar aramasinda kullanir. */
  etiket?: string;
  not?: string;
};

export const TUR_TR: Record<GunlukTur, string> = {
  sulama: "Sulama",
  gubre: "Gübre",
  ilac: "İlaçlama",
  teshis: "Teşhis",
  ekim: "Ekim",
  hasat: "Hasat",
};

const ANAHTAR = "tarim.gunluk";

/** Koordinattan hucre anahtari. Yuvarlama gerekcesi dosya basindaki notta. */
export function yerAnahtari(lat: number, lon: number): string {
  return `${lat.toFixed(3)},${lon.toFixed(3)}`;
}

export function bugunISO(): string {
  // toISOString UTC verir; Turkiye'de aksam 22:00'de yazilan kayit bir onceki
  // gune yazilirdi. Yerel tarih alanlarindan kuruyoruz.
  const d = new Date();
  const ay = String(d.getMonth() + 1).padStart(2, "0");
  const gun = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${ay}-${gun}`;
}

function oku(): GunlukKaydi[] {
  try {
    const ham = localStorage.getItem(ANAHTAR);
    const v: unknown = ham ? JSON.parse(ham) : [];
    return Array.isArray(v) ? (v as GunlukKaydi[]) : [];
  } catch {
    // Bozuk ya da kapali depo uygulamayi ENGELLEMEMELI: gunluk yardimci bir
    // ozellik, teshis ve sulama hesabi onsuz da calisir.
    return [];
  }
}

/**
 * Secili noktanin gunlugu.
 *
 * lat/lon null ise (nokta secilmemis) liste bos doner ve ekleme yok sayilir:
 * yeri belli olmayan bir kayit, sonradan hangi tarlaya ait oldugu
 * bilinemeyecegi icin degersizdir.
 */
export function useGunluk(lat: number | null, lon: number | null) {
  const [hepsi, ayarla] = useState<GunlukKaydi[]>(oku);
  const yer = lat !== null && lon !== null ? yerAnahtari(lat, lon) : null;

  const yaz = useCallback((yeni: GunlukKaydi[]) => {
    ayarla(yeni);
    try {
      localStorage.setItem(ANAHTAR, JSON.stringify(yeni));
    } catch {
      /* kota dolu ya da depo kapali: kayit yalnizca bu oturumda yasar */
    }
  }, []);

  // Yeniden eskiye. Ciftcinin ilk bakacagi sey en son ne yaptigidir.
  const liste = hepsi
    .filter((k) => k.yer === yer)
    .sort((a, b) => b.tarih.localeCompare(a.tarih));

  const ekle = useCallback(
    (k: Omit<GunlukKaydi, "id" | "yer">) => {
      if (!yer) return;
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      yaz([...oku(), { ...k, id, yer }]);
    },
    [yer, yaz],
  );

  const sil = useCallback(
    (id: string) => yaz(oku().filter((k) => k.id !== id)),
    [yaz],
  );

  /** En son sulama tarihi (YYYY-AA-GG) ya da null. /gunluk bunu ister. */
  const sonSulama = liste.find((k) => k.tur === "sulama")?.tarih ?? null;

  /**
   * Sunucuya gonderilecek bicim. Yalnizca hesaba giren alanlar: `not` ve `id`
   * kullanicinin serbest metni/ic kimligi, sunucuda isi yok ve gonderilmez.
   */
  const sunucuIcin = () =>
    liste.map((k) => ({ tarih: k.tarih, tur: k.tur, etiket: k.etiket }));

  return { liste, ekle, sil, sonSulama, sunucuIcin, yerVar: yer !== null };
}
