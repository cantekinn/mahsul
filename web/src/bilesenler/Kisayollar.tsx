/**
 * Hizli erisim kisayollari.
 *
 * NE OLDUGU KONUSUNDA DURUST OLMAK ZORUNDAYIZ. Bu liste uygulamayi
 * hizlandirmaz. Onbellegi depoya gomulu olan noktalari gosterir, o kadar.
 * Onbellek anahtari koordinati ~1 km hucreye yuvarluyor ve dunyanin kara
 * yuzeyi ~149 milyon km2; 37 nokta rastgele bir tiklamayi yakalayamaz.
 * Bu yuzden baslikta "populer bolgeler" ya da "onerilen noktalar" YAZMIYOR:
 * ikisi de bu noktalarin bir sekilde secilmis, degerlendirilmis yerler
 * oldugunu ima ederdi. Secme olcutum tek sey: onbelleklerini onceden
 * doldurdum.
 *
 * ETIKET VERI DEGILDIR. Dugmenin ustundeki yazi benim not dusmemdir
 * (kisayol_ad). Noktaya tiklandiginda konum kartinda gorunen ad her zaman
 * OpenStreetMap'ten gelir. Ikisi ayrildiginda dogru olan OSM'inkidir;
 * ipucu balonunda ikisini birden gosteriyorum ki fark gizlenmesin.
 *
 * "HAZIR" DEMEK ICIN DORT KATMANIN DORDU DE GEREKIR. Ilk yazdigimda hazirlik
 * olcusu sadece yer adinin onbellekte olmasiydi ve UC NOKTADA YALAN
 * SOYLUYORDU: adi vardi ama iklimi yoktu (Open-Meteo saatlik kotasi dolmustu),
 * yani dugme "hazir" gorunup urun onerisi hic gelmiyordu. Simdi eksik katmani
 * olan dugme soluk gosteriliyor ve hangi katmanin eksik oldugu ipucunda yaziyor.
 */
import { useEffect, useState } from "react";
import { api } from "../api/istemci";
import type { Kisayol } from "../api/istemci";

/** Arka ucun katman anahtarlari ve kullaniciya gosterilecek karsiliklari. */
const KATMANLAR = [
  { anahtar: "yer", ad: "yer adı" },
  { anahtar: "iklim", ad: "iklim" },
  { anahtar: "toprak", ad: "toprak" },
  { anahtar: "parsel", ad: "parsel" },
] as const;

type Props = {
  onSec: (lat: number, lon: number) => void;
  secili: { lat: number; lon: number } | null;
};

export default function Kisayollar({ onSec, secili }: Props) {
  const [liste, setListe] = useState<Kisayol[] | null>(null);
  const [hata, setHata] = useState(false);

  useEffect(() => {
    let iptal = false;
    api
      .kisayollar()
      .then((l) => {
        if (!iptal) setListe(l);
      })
      .catch(() => {
        if (!iptal) setHata(true);
      });
    return () => {
      iptal = true;
    };
  }, []);

  // Kisayollar bir kolayliktir, uygulamanin isi degil. Alinamazsa harita ve
  // rastgele nokta calismaya devam ediyor; ekrani hata mesajiyla doldurup
  // kullaniciyi bozuk bir uygulamayla karsi karsiya sanmasina gerek yok.
  if (hata || !liste || liste.length === 0) return null;

  const tamHazir = liste.filter((k) => k.isitildi).length;

  return (
    <nav className="kisayollar" aria-label="Hızlı erişim noktaları">
      <span className="kisayol-baslik">Hazır noktalar</span>
      <div className="kisayol-serit">
        {liste.map((k) => {
          const acik =
            secili !== null && secili.lat === k.lat && secili.lon === k.lon;
          const eksik = KATMANLAR.filter(
            (x) => !k.hazir_katmanlar.includes(x.anahtar),
          ).map((x) => x.ad);
          return (
            <button
              key={`${k.lat},${k.lon}`}
              className={
                "kisayol" +
                (acik ? " secili" : "") +
                (k.isitildi ? "" : " yarim")
              }
              onClick={() => onSec(k.lat, k.lon)}
              title={
                [
                  k.yer_adi ? `OpenStreetMap adı: ${k.yer_adi}` : null,
                  eksik.length === 0
                    ? "Dört katman da hazır, anında açılır."
                    : `Hazır değil: ${eksik.join(", ")}. Bu katman ` +
                      "tıklayınca canlı sorgulanacak, beklemeniz gerekebilir.",
                ]
                  .filter(Boolean)
                  .join("\n")
              }
            >
              {k.kisayol_ad}
            </button>
          );
        })}
      </div>
      <p className="kisayol-alt">
        {tamHazir} noktanın verisi önceden indirildi, anında açılır. Soluk
        yazılanlarda bir katman eksik kaldı, onlar tıklayınca canlı sorgulanır.
        Bu bir öneri listesi değildir, haritada dilediğiniz yere
        tıklayabilirsiniz.
      </p>
    </nav>
  );
}
