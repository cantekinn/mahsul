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
export type Sulama = components["schemas"]["SulamaYanit"];
export type IklimRisk = components["schemas"]["IklimRiskYanit"];
export type Zararli = components["schemas"]["ZararliYanit"];
export type Kapsam = components["schemas"]["KapsamYanit"];
export type Karbon = components["schemas"]["KarbonYanit"];
export type Soru = components["schemas"]["SoruYanit"];
export type TkgmParsel = components["schemas"]["TkgmParsel"];

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
  // ADET NEDEN 12 DEGIL: liste artik uc bolume ayriliyor (simdi ekilebilir,
  // baska mevsimde, cok yillik). 12 urunle Bursa'da "baska mevsimde" bolumu
  // bos cikiyordu, cunku ilk 12'nin hepsi zaten simdi ekilebilir olanlardi;
  // yani bolum var ama icerigi yok gibi gorunuyordu. 60 ile ucu de doluyor.
  oneri: (lat: number, lon: number, adet = 60) =>
    al<OneriKumesi>("/oneri", { lat, lon, adet }),
  rastgele: () => al<Konum>("/rastgele"),
  kisayollar: () => al<Kisayol[]>("/kisayollar"),
  // Tarla takvimi. Uc uc nokta ayri cunku ucu de Open-Meteo'ya farkli sorgu
  // atiyor; ayri tutulunca hangisi once gelirse o once ekrana yaziliyor.
  sulama: (lat: number, lon: number, urun: string, asama: string, alan_m2?: number) =>
    al<Sulama>("/sulama", { lat, lon, urun, asama, alan_m2 }),
  iklimRisk: (lat: number, lon: number, urun: string) =>
    al<IklimRisk>("/iklim-riski", { lat, lon, urun }),
  zararli: (lat: number, lon: number, urun: string) =>
    al<Zararli>("/zararli", { lat, lon, urun }),
  // Hangi hesabin hangi urunu cevapladigi. Uc hesabin siniri ayni DEGIL
  // (iklim 116, sulama 84, zararli 5 urun); arayuz kapsam disi urunu
  // gizlemek yerine sebebiyle isaretlesin diye sunucudan cekiliyor.
  kapsam: () => al<Kapsam[]>("/kapsam"),
  // Karbon ayak izi. Gubre/yakit VERILMEZSE sunucu tablo varsayilanini kullanip
  // yaniti "gosterge" isaretler; arayuz o bayraga bakip sayiyi kesin bir olcum
  // gibi sunmaz.
  karbon: (
    lat: number,
    lon: number,
    urun: string,
    alan_m2: number,
    ek: {
      sezon_gun?: number;
      azot_kg_da?: number | null;
      dizel_l_da?: number | null;
      sulama_yontemi?: string;
      su_kaynagi?: string;
    } = {},
  ) => al<Karbon>("/karbon", { lat, lon, urun, alan_m2, ...ek }),
  // Serbest metin sorusu. Nokta secili degilse de cagrilabilir: sunucu o zaman
  // cevap yerine "once nokta secin" yonlendirmesi doner (yonlendirme=true).
  sor: (soru: string, lat?: number | null, lon?: number | null, alan_m2?: number) =>
    al<Soru>("/sor", { soru, lat, lon, alan_m2 }),
  // Kayitli TKGM parselleri. Tek seferlik, konumdan bagimsiz liste.
  tkgmParselleri: () => al<TkgmParsel[]>("/parseller/tkgm"),
};
