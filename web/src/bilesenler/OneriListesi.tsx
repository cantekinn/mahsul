/**
 * Urun onerileri, gruplara ayrilmis.
 *
 * NEDEN GRUPLU: duz siralamada ilk on siraya ayni aileden urunler doluyor
 * (olculdu: Antalya'da ust siralar bastan asagi sebze). Ciftciye "sunlardan
 * birini sec" demek icin cesitlilik gerekir; tahil, baklagil, meyve, yag
 * bitkisi ayri ayri gorunmeli.
 */
import { useMemo, useState } from "react";
import { KatmanKabugu } from "./Durum";
import type { Katman } from "./Durum";
import type { Oneri, OneriKumesi } from "../api/istemci";

function skorRengi(skor: number) {
  if (skor >= 85) return "cok-iyi";
  if (skor >= 70) return "iyi";
  if (skor >= 55) return "orta";
  return "zayif";
}

function UrunKarti({ o }: { o: Oneri }) {
  const [acik, setAcik] = useState(false);
  return (
    <li className={`urun ${skorRengi(o.skor)}`}>
      <button className="urun-bas" onClick={() => setAcik(!acik)}>
        <span className="urun-ad">{o.ad}</span>
        <span className="urun-skor">{o.skor.toFixed(0)}</span>
      </button>
      <p className="urun-alt">
        {o.uygunluk}
        {o.cok_yillik ? " · çok yıllık" : ""}
      </p>
      {acik && (
        <div className="urun-detay">
          <p className="bilimsel">{o.bilimsel_ad}</p>
          <p>{o.sezon}</p>
          {/* Su acigi icin BURADA ayrica satir yazilmaz. Arka uc su_acigi_mm > 0
              olan her durumda uyarilar listesine zaten daha bilgilendirici bir
              cumle koyuyor (kac mm eksik ve dekara kac ton su ettigi). Ikisini
              birden basmak ayni uyariyi iki kez gostermek olurdu; olcup
              gordum, oyle oluyordu. */}
          {o.uyarilar && o.uyarilar.length > 0 && (
            <ul className="eksik">
              {o.uyarilar.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          )}
          {o.notlar && <p className="alt">{o.notlar}</p>}
        </div>
      )}
    </li>
  );
}

export default function OneriListesi({ katman }: { katman: Katman<OneriKumesi> }) {
  return (
    <KatmanKabugu
      baslik="Ürün önerileri"
      katman={katman}
      bekleyen="Ürünler puanlanıyor..."
    >
      {(o) => <Icerik o={o} />}
    </KatmanKabugu>
  );
}

function Icerik({ o }: { o: OneriKumesi }) {
  const gruplar = useMemo(() => {
    const g = new Map<string, Oneri[]>();
    for (const x of o.oneriler) {
      const l = g.get(x.grup) ?? [];
      l.push(x);
      g.set(x.grup, l);
    }
    return [...g.entries()];
  }, [o.oneriler]);

  return (
    <div className="kart">
      <div className="kart-bas">
        <h2>Ürün önerileri</h2>
        <span className="rozet">
          {o.toplam_uygun} ürün uygun · {o.sure_s.toFixed(1)} sn
        </span>
      </div>

      {!o.toprak_var && (
        /* Toprak gelmediyse puan SADECE iklime dayanir. Bunu yazmazsak
           kullanici eksik girdiyle uretilmis bir sirlamayi tam sanardi. */
        <p className="uyari">
          Toprak verisi kullanılamadı. Bu puanlar yalnızca iklime dayanıyor,
          pH ve toprak dokusu hesaba girmedi.
        </p>
      )}

      {gruplar.length === 0 ? (
        <p className="bekleyen">Bu koşullarda öne çıkan ürün bulunamadı.</p>
      ) : (
        gruplar.map(([grup, liste]) => (
          <div key={grup} className="grup">
            <h3>{grup}</h3>
            <ul className="urunler">
              {liste.map((x) => (
                <UrunKarti key={x.urun} o={x} />
              ))}
            </ul>
          </div>
        ))
      )}
    </div>
  );
}
