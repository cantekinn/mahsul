/**
 * API istemcisi.
 *
 * TIPLER ELLE YAZILMAZ. src/api/tipler.ts dosyasi FastAPI'nin kendi
 * /openapi.json ciktisindan uretilir (npm run tipler). Gerekcesi bu projede
 * defalarca yasanan hata: arayuz ile arka ucun sessizce ayrisms olmasi. Alan
 * adini elle yazarsak, arka uc alani yeniden adlandirdiginda arayuz hata
 * vermez, sadece "undefined" gosterir; yani yanlis bilgi.
 */
import type { components } from "./tipler";

export type Konum = components["schemas"]["KonumYanit"];
export type Toprak = components["schemas"]["ToprakYanit"];
export type Parseller = components["schemas"]["ParsellerYanit"];
export type Parsel = components["schemas"]["ParselYanit"];
export type OneriKumesi = components["schemas"]["OneriKumesi"];
export type Oneri = components["schemas"]["OneriYanit"];
export type Kisayol = components["schemas"]["KisayolYanit"];

/**
 * API'nin koku.
 *
 * URETIMDE VARSAYILAN BOS DIZGIDIR, yani "ayni koken". Derlenmis arayuz
 * FastAPI'nin kendisi tarafindan sunuluyor (bkz api/main.py sonu), dolayisiyla
 * /konum zaten dogru sunucuya gider ve CORS hic devreye girmez.
 *
 * GELISTIRMEDE ise Vite 5173'te, API 8000'de calisiyor; iki ayri koken. O
 * yuzden ayrim import.meta.env.DEV ile yapiliyor, elle ayarlanan bir bayrakla
 * degil: elle ayar unutuldugunda uretim derlemesi sessizce 127.0.0.1'e
 * istek atar ve uygulama SADECE benim makinemde calisirdi.
 *
 * VITE_API_KOK verilirse ikisini de ezer (API baska bir yerde barinirsa).
 */
const KOK =
  import.meta.env.VITE_API_KOK ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

/** Sunucunun anlamli hata mesajini tasiyan hata tipi. */
export class ApiHatasi extends Error {
  // Alan acikca tanimlanir: yapici parametresine "public" yazmak TypeScript'e
  // ozgu bir kisayoldur ve bu proje "erasableSyntaxOnly" ile derleniyor
  // (yani tipler silinince gecerli JavaScript kalmali).
  kod: number;
  constructor(kod: number, mesaj: string) {
    super(mesaj);
    this.kod = kod;
  }
}

async function al<T>(yol: string, params: Record<string, unknown> = {}): Promise<T> {
  const sorgu = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) sorgu.set(k, String(v));
  }
  const yanit = await fetch(`${KOK}${yol}?${sorgu}`);
  if (!yanit.ok) {
    // Sunucu 503 dondugunde govdede NEDEN yaziyor (orn. iklim servisi
    // cevap vermedi). Bunu yutup "bir hata olustu" demek, kullaniciyi
    // sorunun gecici mi kalici mi oldugundan habersiz birakirdi.
    let mesaj = `Sunucu ${yanit.status} dondu`;
    try {
      const g = await yanit.json();
      if (g?.detail) mesaj = typeof g.detail === "string" ? g.detail : mesaj;
    } catch {
      /* govde JSON degilse varsayilan mesaj kalir */
    }
    throw new ApiHatasi(yanit.status, mesaj);
  }
  return yanit.json() as Promise<T>;
}

export const api = {
  konum: (lat: number, lon: number) => al<Konum>("/konum", { lat, lon }),
  toprak: (lat: number, lon: number) => al<Toprak>("/toprak", { lat, lon }),
  parseller: (lat: number, lon: number, yaricap_m = 1500) =>
    al<Parseller>("/parseller", { lat, lon, yaricap_m }),
  oneri: (lat: number, lon: number, adet = 12) =>
    al<OneriKumesi>("/oneri", { lat, lon, adet }),
  rastgele: () => al<Konum>("/rastgele"),
  kisayollar: () => al<Kisayol[]>("/kisayollar"),
};
