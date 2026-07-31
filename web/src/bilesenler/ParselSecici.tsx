/**
 * Kayitli TKGM parselleri (tapu sorgu sonuclari) icin secici.
 *
 * NEDEN IKI SEKMEDE BIRDEN
 * Secici once yalnizca Tarla takviminde duruyordu. Ama ciftcinin ilk sorusu
 * "burada ne yetisir", ikincisi "ne zaman sulayayim". Parselini ancak ikinci
 * ekranda secebilmesi, ilk ekranda kendi tarlasini haritada gozle bulmasini
 * gerektiriyordu; oysa parselin koordinati zaten elimizde. Simdi ayni bilesen
 * her iki sekmede de duruyor, secim tek noktada (App.tsx) yaziliyor.
 *
 * NEDEN CANLI TKGM SORGUSU DEGIL
 * TKGM'nin parsel sorgu ucu kurumsal erisim istiyor; istek HTML giris
 * sayfasina yonleniyor (olculdu). Bu yuzden sorgu sonuclari dosya olarak
 * duruyor ve sunucu onlari okuyor. Liste bir kez cekilir, koordinata bagli
 * degildir.
 *
 * NEDEN SECIM NOKTAYI VE ALANI BIRDEN KURAR
 * Ciftci parselini secince alani elle girmesi gerekseydi tapudaki degeri
 * hatirlamasi ya da bakmasi gerekirdi; oysa deger zaten sorgu sonucunda var
 * ve karbon karti onsuz calismiyor.
 *
 * NEDEN LISTE BOSSA HIC GORUNMEZ
 * Bos bir acilir liste, kullaniciya kendi parselinin kayitli olmadigini
 * dusundururdu. Oysa dogru bilgi "liste cekilemedi"dir ve bu, kullanicinin
 * yapabilecegi bir sey olmadigi icin ekranda yer kaplamamalidir.
 */
import { useEffect, useState } from "react";
import { api } from "../api/istemci";
import type { TkgmParsel } from "../api/istemci";

/** Listeyi bir kez ceker. Cekilemezse bos doner ve secici gizlenir. */
export function useTkgmParselleri(): TkgmParsel[] {
  const [liste, ayarla] = useState<TkgmParsel[]>([]);
  useEffect(() => {
    let iptal = false;
    api
      .tkgmParselleri()
      .then((v) => {
        if (!iptal) ayarla(v);
      })
      .catch(() => {
        /* liste yoksa secici gizlenir */
      });
    return () => {
      iptal = true;
    };
  }, []);
  return liste;
}

export default function ParselSecici({
  liste,
  onSec,
  sinif = "genis",
}: {
  liste: TkgmParsel[];
  onSec: (lat: number, lon: number, dekar: number) => void;
  // Tarla sekmesinde form izgarasinin bir hucresi ("genis"), harita
  // sekmesinde tek basina duran bir satir. Yerlesim disaridan geliyor cunku
  // bilesenin kendisi nerede durdugunu bilmiyor.
  sinif?: string;
}) {
  if (liste.length === 0) return null;
  return (
    <label className={sinif}>
      Kayıtlı parsel
      {/* value SABIT BOS: bu bir secim degil, bir komut. Secilen parsel
          uygulamanin durumu haline geliyor (nokta + alan) ve kutunun
          uzerinde asili kalmasi, kullanici haritadan baska bir yere
          tikladiginda yalan soylerdi. */}
      <select
        value=""
        onChange={(e) => {
          const p = liste.find((x) => x.etiket === e.target.value);
          if (p) onSec(p.lat, p.lon, p.dekar);
        }}
      >
        <option value="">{liste.length} tapu kaydı</option>
        {liste.map((p) => (
          <option key={p.etiket} value={p.etiket}>
            {p.etiket} · {p.dekar} da
          </option>
        ))}
      </select>
    </label>
  );
}
