import { Kart, KatmanKabugu } from "./Durum";
import type { Katman } from "./Durum";
import type { Parseller } from "../api/istemci";

export default function ParselKarti({ katman }: { katman: Katman<Parseller> }) {
  return (
    <KatmanKabugu
      baslik="Çevredeki tarım parselleri"
      katman={katman}
      bekleyen="Parseller aranıyor (OpenStreetMap)..."
    >
      {(p) => (
        <Kart
          baslik="Çevredeki tarım parselleri"
          etiket={<span className="rozet">{p.sure_s.toFixed(1)} sn</span>}
        >
          {/* BOS LISTE TEK BASINA "PARSEL YOK" DEMEK DEGILDIR. Overpass 429
              dondugunde de liste bos gelir. Bu yuzden "kesin" bayragi
              olmadan asla "parsel bulunamadi" yazilmaz. */}
          {!p.kesin && p.adet === 0 ? (
            <p className="hata">
              Parsel sorgusu tamamlanamadı ({p.durum}). Burada parsel olmadığı
              anlamına gelmez.
            </p>
          ) : p.adet === 0 ? (
            <p className="bekleyen">
              1.5 km yarıçapta kayıtlı tarım parseli yok.
            </p>
          ) : (
            <>
              <p className="alt">
                {p.adet} parsel bulundu, haritada yeşille çizildi.
              </p>
              <ul className="parsel-liste">
                {p.parseller.slice(0, 8).map((x) => (
                  <li key={x.osm_id}>
                    <span>{x.ad ?? x.tur_tr}</span>
                    <span className="yok">
                      {x.alan_dekar ? `${x.alan_dekar} dekar` : "alan bilinmiyor"}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Kart>
      )}
    </KatmanKabugu>
  );
}
