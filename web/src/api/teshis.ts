/**
 * /teshis (multipart) icin ayri istemci.
 *
 * NEDEN AYRI DOSYA: istemci.ts al<T>() jenerik yardimcisi JSON GET icin. Bu uc
 * nokta multipart POST; FormData ile Content-Type'i tarayici setlesin diye elle
 * yaziyoruz. Ortak fetch/hata isleyisi ApiHatasi ile ayni kaliyor.
 */
import { ApiHatasi } from "./istemci";
import type { components } from "./tipler";

export type Teshis = components["schemas"]["TeshisYanit"];
export type TedaviKaydi = components["schemas"]["TedaviKaydi"];
export type TopKMadde = components["schemas"]["TopKMadde"];

const KOK =
  import.meta.env.VITE_API_KOK ?? (import.meta.env.DEV ? "http://127.0.0.1:8000" : "");

/**
 * Yaprak fotografini gonderir, teshis sonucunu doner.
 *
 * NOT: Content-Type header'i ELLE VERILMEZ. FormData verildiginde tarayici
 * "multipart/form-data; boundary=..." dizisini kendisi olusturur. Elle
 * "multipart/form-data" yazsaydik boundary eksik kalirdi ve sunucu 400 donerdi.
 */
export async function teshisEt(dosya: File): Promise<Teshis> {
  const form = new FormData();
  form.append("dosya", dosya);
  const yanit = await fetch(`${KOK}/teshis`, { method: "POST", body: form });
  if (!yanit.ok) {
    let mesaj = `Sunucu ${yanit.status} dondu`;
    try {
      const g = await yanit.json();
      if (g?.detail) mesaj = typeof g.detail === "string" ? g.detail : mesaj;
    } catch {
      /* JSON degilse varsayilan mesaj */
    }
    throw new ApiHatasi(yanit.status, mesaj);
  }
  return yanit.json() as Promise<Teshis>;
}
