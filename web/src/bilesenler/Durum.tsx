/**
 * Katman durumu ve ortak kart kabugu.
 *
 * NEDEN AYRI BIR "hata" DURUMU VAR: bu projenin en pahali hatasi, dis servis
 * susunca bunu "veri yok" diye gostermekti. Arayuzde de ayni ayrim korunur:
 * "bulunamadi" ile "sorulamadi" ASLA ayni goruntuyu vermez.
 */
import type { ReactNode } from "react";

export type Katman<T> =
  | { durum: "bos" }
  | { durum: "yukleniyor" }
  | { durum: "ok"; veri: T }
  | { durum: "hata"; hata: string };

export function Kart({
  baslik,
  etiket,
  children,
}: {
  baslik: string;
  etiket?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="kart">
      <div className="kart-bas">
        <h2>{baslik}</h2>
        {etiket}
      </div>
      {children}
    </div>
  );
}

/** Yukleniyor / hata durumlarini tek yerden basar, gerisi cagirana kalir. */
export function KatmanKabugu<T>({
  baslik,
  katman,
  bekleyen,
  children,
}: {
  baslik: string;
  katman: Katman<T>;
  bekleyen: string;
  children: (veri: T) => ReactNode;
}) {
  if (katman.durum === "bos") return null;
  if (katman.durum === "yukleniyor") {
    return (
      <Kart baslik={baslik}>
        {/* Iskelet, bekleme METNININ YERINE DEGIL YANINDA duruyor. Metin
            "Parseller aranıyor (OpenStreetMap)" gibi HANGI SERVISIN
            beklendigini soyler; bu proje dis servis sessizligini gizlememek
            uzerine kurulu, dolayisiyla o cumle kaybolamaz. Iskeletin isi
            baska: kartin kaplayacagi yeri onceden ayirip veri gelince
            sayfanin ziplamasini onlemek. */}
        <div className="iskelet" aria-hidden="true">
          <span className="iskelet-satir" />
          <span className="iskelet-satir kisa" />
          <span className="iskelet-satir" />
        </div>
        <p className="bekleyen" role="status">
          {bekleyen}
        </p>
      </Kart>
    );
  }
  if (katman.durum === "hata") {
    return (
      <Kart baslik={baslik}>
        {/* Hatanin metni sunucudan gelir ve NEDENI soyler. "Bir hata olustu"
            demek, kullaniciya sorunun gecici mi kalici mi oldugunu
            gizlemek olurdu. */}
        <p className="hata">{katman.hata}</p>
      </Kart>
    );
  }
  return <>{children(katman.veri)}</>;
}

/** Sayiyi bilinmiyorsa "bilinmiyor" diye yazar, 0 diye degil. */
export function sayi(v: number | null | undefined, birim = "", basamak = 1) {
  if (v === null || v === undefined) return <span className="yok">bilinmiyor</span>;
  return (
    <>
      {v.toFixed(basamak)}
      {birim}
    </>
  );
}
