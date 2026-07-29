import { Kart, KatmanKabugu, sayi } from "./Durum";
import type { Katman } from "./Durum";
import type { Konum } from "../api/istemci";

export default function KonumKarti({
  katman,
  nokta,
}: {
  katman: Katman<Konum>;
  nokta: { lat: number; lon: number };
}) {
  return (
    <KatmanKabugu baslik="Konum" katman={katman} bekleyen="Konum alınıyor...">
      {(k) => (
        <Kart
          baslik="Konum"
          etiket={<span className="rozet">{k.sure_s.toFixed(1)} sn</span>}
        >
          <p className="yer">{k.yer_adi ?? "Adı bilinmeyen nokta"}</p>
          <p className="alt">
            {k.ulke ?? "ülke bilinmiyor"} · {nokta.lat.toFixed(4)},{" "}
            {nokta.lon.toFixed(4)}
          </p>
          <dl className="satirlar">
            <div>
              <dt>Yükselti</dt>
              <dd>{sayi(k.yukselti_m, " m", 0)}</dd>
            </div>
            <div>
              <dt>Yıllık yağış</dt>
              <dd>{sayi(k.iklim?.rainfall, " mm", 0)}</dd>
            </div>
            <div>
              <dt>Yıllık ortalama sıcaklık</dt>
              <dd>{sayi(k.iklim?.temperature, " C")}</dd>
            </div>
          </dl>
          {!k.karada && (
            <p className="uyari">Bu nokta karada görünmüyor.</p>
          )}
          {k.eksik && k.eksik.length > 0 && (
            /* Eksik katmanlar SAKLANMAZ. Kullanici hangi bilginin
               alinamadigini bilmeli, yoksa eksik veriyle uretilmis bir
               oneriyi tam sanir. */
            <ul className="eksik">
              {k.eksik.map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          )}
        </Kart>
      )}
    </KatmanKabugu>
  );
}
