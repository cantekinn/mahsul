/**
 * Tarla takvimi: sulama, iklim riski ve zararli tek ekranda.
 *
 * Sprint 2 ajanlari buraya baglaniyor. Uc uc nokta AYRI cekiliyor, tek bir
 * "yukleniyor" bayragina baglanmiyor: ucu de Open-Meteo'ya farkli sorgu atiyor
 * (7 gunluk ET0, 16 gunluk tahmin, 1 Mart'tan bugune arsiv) ve sureleri
 * birbirinden bagimsiz. Tek bayrak olsaydi ekran en yavas olanin hizina
 * inerdi; App.tsx'teki katman mantiginin ayni gerekcesi.
 *
 * Nokta HARITA SEKMESINDEN gelir. Burada ikinci bir harita gostermiyoruz:
 * ayni secimi iki yerde tutmak, iki yerin ayrisip farkli koordinat gostermesi
 * demekti.
 */
import { useCallback, useEffect, useState } from "react";
import { api, ApiHatasi } from "../api/istemci";
import type { IklimRisk, Sulama, Zararli } from "../api/istemci";
import { Kart, KatmanKabugu } from "./Durum";
import type { Katman } from "./Durum";

type Nokta = { lat: number; lon: number };

/** API'nin desteklediginin AYNISI (core/config.py agent_crops). Buradaki liste
 *  uzarsa sunucu 422 doner, sessiz bir yanlis sonuc uretmez. */
const URUNLER = [
  { anahtar: "domates", ad: "Domates" },
  { anahtar: "biber", ad: "Biber" },
  { anahtar: "patates", ad: "Patates" },
  { anahtar: "narenciye", ad: "Narenciye" },
  { anahtar: "zeytin", ad: "Zeytin" },
  { anahtar: "muz", ad: "Muz" },
];

const ASAMALAR = [
  { anahtar: "ini", ad: "Fide / ekim" },
  { anahtar: "mid", ad: "Gelişme" },
  { anahtar: "end", ad: "Hasat" },
];

/** Bir istegi katman durumuna cevirir. App.tsx'teki useKatman ile ayni desen,
 *  ama burada bagimlilik listesi urun/asamayi da icerir. */
function useIstek<T>(cagir: (() => Promise<T>) | null): Katman<T> {
  const [k, ayarla] = useState<Katman<T>>({ durum: "bos" });
  useEffect(() => {
    if (!cagir) {
      ayarla({ durum: "bos" });
      return;
    }
    let iptal = false;
    ayarla({ durum: "yukleniyor" });
    cagir()
      .then((v) => {
        if (!iptal) ayarla({ durum: "ok", veri: v });
      })
      .catch((e: unknown) => {
        if (!iptal) {
          ayarla({
            durum: "hata",
            hata: e instanceof ApiHatasi ? e.message : "Sunucuya ulaşılamadı",
          });
        }
      });
    return () => {
      iptal = true;
    };
  }, [cagir]);
  return k;
}

function SulamaKarti({ katman }: { katman: Katman<Sulama> }) {
  return (
    <KatmanKabugu baslik="Sulama" katman={katman} bekleyen="ET0 hesaplanıyor...">
      {(v) => (
        <Kart baslik="Sulama" etiket={<span className="rozet">FAO-56</span>}>
          {v.planlar.map((p) => (
            <div key={p.urun} className="tarla-olcum">
              <div className="tarla-buyuk">
                {p.net_mm_gun.toFixed(1)}
                <span className="tarla-birim">mm/gün</span>
              </div>
              <div className="tarla-alt">
                {p.urun_tr} · {v.asama_tr} aşaması
                {p.litre_gun !== null && p.litre_gun !== undefined && (
                  <> · parselde {Math.round(p.litre_gun).toLocaleString("tr-TR")} L/gün</>
                )}
              </div>
            </div>
          ))}
          <dl className="tarla-satirlar">
            <div>
              <dt>ET0 (referans buharlaşma)</dt>
              <dd>{v.et0_mm_gun.toFixed(2)} mm/gün</dd>
            </div>
            <div>
              <dt>Beklenen yağış</dt>
              <dd>
                {v.yagis_mm_donem.toFixed(1)} mm / {v.gun} gün
              </dd>
            </div>
            {v.planlar.map((p) => (
              <div key={p.urun}>
                <dt>Kc ({p.urun_tr})</dt>
                <dd>
                  {p.kc.toFixed(2)} · ETc {p.etc_mm_gun.toFixed(1)} mm/gün
                </dd>
              </div>
            ))}
          </dl>
          <p className="tarla-uyari">{v.uyari}</p>
        </Kart>
      )}
    </KatmanKabugu>
  );
}

function RiskKarti({ katman }: { katman: Katman<IklimRisk> }) {
  return (
    <KatmanKabugu baslik="İklim riski" katman={katman} bekleyen="16 günlük tahmin alınıyor...">
      {(v) => (
        <Kart
          baslik="İklim riski"
          etiket={<span className="rozet">{v.gun} gün</span>}
        >
          {v.urunler.map((u) => (
            <div key={u.urun}>
              {u.riskler.length === 0 ? (
                // "Risk yok" DEMIYORUZ. Model yalnizca esik asimina bakiyor;
                // esik asilmamasi riskin olmadigi anlamina gelmez.
                <p className="tarla-temiz">
                  {u.urun_tr} için önümüzdeki {v.gun} günde eşik aşımı görünmüyor.
                </p>
              ) : (
                <ul className="risk-liste">
                  {u.riskler.map((r, i) => (
                    <li key={i} className={`risk risk-${r.seviye}`}>
                      <span className="risk-rozet">{r.tur_tr}</span>
                      <span className="risk-metin">{r.aciklama}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
          <p className="tarla-uyari">{v.uyari}</p>
        </Kart>
      )}
    </KatmanKabugu>
  );
}

function ZararliKarti({ katman }: { katman: Katman<Zararli> }) {
  return (
    <KatmanKabugu baslik="Zararlı takvimi" katman={katman} bekleyen="Derece-gün birikiyor...">
      {(v) => (
        <Kart
          baslik="Zararlı takvimi"
          etiket={<span className="rozet">{v.biofix} başlangıç</span>}
        >
          {v.durumlar.length === 0 ? (
            <p className="tarla-temiz">
              Bu ürün için derece-gün tablosunda tanımlı zararlı kaydı yok.
            </p>
          ) : (
            <ul className="zararli-liste">
              {v.durumlar.map((z) => (
                <li key={z.zararli}>
                  <div className="zararli-bas">
                    <strong>{z.zararli}</strong>
                    <span className="rozet">
                      {z.nesil}. nesil · {z.evre}
                    </span>
                  </div>
                  <div className="zararli-gdd">
                    {z.toplam_gdd.toFixed(0)} GDD birikti
                    {z.sonraki_evre_ad && (
                      <>
                        {" "}
                        · sonraki evre {z.sonraki_evre_ad},{" "}
                        {z.sonraki_evre_gdd?.toFixed(0)} GDD sonra
                      </>
                    )}
                  </div>
                  <p className="zararli-not">{z.aciklama}</p>
                </li>
              ))}
            </ul>
          )}
          <p className="tarla-uyari">{v.uyari}</p>
        </Kart>
      )}
    </KatmanKabugu>
  );
}

export default function TarlaPaneli({
  nokta,
  onHaritayaGit,
}: {
  nokta: Nokta | null;
  onHaritayaGit: () => void;
}) {
  const [urun, setUrun] = useState("domates");
  const [asama, setAsama] = useState("mid");
  const [dekar, setDekar] = useState("");

  // Ciftci dekar konusur; API metrekare bekliyor. Cevrim TEK YERDE.
  const alanM2 = (() => {
    const d = Number(dekar.replace(",", "."));
    return dekar.trim() !== "" && Number.isFinite(d) && d > 0 ? d * 1000 : undefined;
  })();

  const sulama = useIstek<Sulama>(
    useCallback(
      () =>
        nokta
          ? api.sulama(nokta.lat, nokta.lon, urun, asama, alanM2)
          : Promise.reject(),
      [nokta, urun, asama, alanM2],
    ),
  );
  const risk = useIstek<IklimRisk>(
    useCallback(
      () => (nokta ? api.iklimRisk(nokta.lat, nokta.lon, urun) : Promise.reject()),
      [nokta, urun],
    ),
  );
  const zararli = useIstek<Zararli>(
    useCallback(
      () => (nokta ? api.zararli(nokta.lat, nokta.lon, urun) : Promise.reject()),
      [nokta, urun],
    ),
  );

  if (!nokta) {
    return (
      <div className="kart bos-mesaj">
        <p>
          Tarla takvimi seçili noktanın hava verisiyle çalışır. Önce ürün önerisi
          sekmesinden haritada bir nokta seçin.
        </p>
        <button type="button" className="dugme birincil" onClick={onHaritayaGit}>
          Haritaya git
        </button>
      </div>
    );
  }

  return (
    <div className="tarla-panel">
      <form className="tarla-secim" onSubmit={(e) => e.preventDefault()}>
        <label>
          Ürün
          <select value={urun} onChange={(e) => setUrun(e.target.value)}>
            {URUNLER.map((u) => (
              <option key={u.anahtar} value={u.anahtar}>
                {u.ad}
              </option>
            ))}
          </select>
        </label>
        <label>
          Aşama
          <select value={asama} onChange={(e) => setAsama(e.target.value)}>
            {ASAMALAR.map((a) => (
              <option key={a.anahtar} value={a.anahtar}>
                {a.ad}
              </option>
            ))}
          </select>
        </label>
        <label>
          Alan (dekar)
          <input
            type="number"
            min="0"
            step="0.1"
            inputMode="decimal"
            placeholder="isteğe bağlı"
            value={dekar}
            onChange={(e) => setDekar(e.target.value)}
          />
        </label>
      </form>

      <div className="tarla-kartlar">
        <SulamaKarti katman={sulama} />
        <RiskKarti katman={risk} />
        <ZararliKarti katman={zararli} />
      </div>
    </div>
  );
}
