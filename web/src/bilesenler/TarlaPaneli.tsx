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
 *
 * URUN LISTESI SECILI TARLADAN GELIR. Once burada 6 urunluk sabit bir dizi
 * vardi; kullanici Bursa'da bir tarla secip cavdar onerisi aldiktan sonra bu
 * sekmede cavdari bulamiyordu. Artik liste iki bolume ayrilir: once o noktaya
 * ONERILEN urunler (puanlariyla), sonra kalan tum urunler. Oneri henuz
 * gelmediyse liste yine dolu kalir, sadece siralamasi genel olur.
 *
 * KAPSAM DISI URUN GIZLENMEZ. Uc hesabin siniri ayni degil (iklim 116 urun,
 * sulama 84, zararli 5). Urunu listeden cikarmak kullaniciya "bu urun yok"
 * dedirtirdi; oysa dogru cumle "bu hesabi bu urun icin yapamiyoruz, sebebi
 * su". O yuzden kart, istegi hic atmadan sebebi yazar.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiHatasi } from "../api/istemci";
import type { IklimRisk, Kapsam, OneriKumesi, Sulama, Zararli } from "../api/istemci";
import { Kart, KatmanKabugu } from "./Durum";
import type { Katman } from "./Durum";

type Nokta = { lat: number; lon: number };
type Yetenek = "sulama" | "iklim" | "zararli";
type UrunSecenek = { anahtar: string; ad: string; skor?: number };

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

/** Kapsam tablosu: hangi hesap hangi urunu cevaplayabiliyor.
 *
 *  Bir kez cekilir ve noktadan bagimsizdir; tablo koordinata gore degismez.
 *  Cekilemezse null kalir ve KISITLAMA UYGULANMAZ: kapsam bilgisi olmadan
 *  urunu engellemek, sunucu 422 dondurse bile daha az bilgi vermek olurdu.
 *  O durumda istek atilir ve sunucunun kendi gerekcesi hata olarak gorunur. */
function useKapsam(): Record<Yetenek, Kapsam> | null {
  const [k, ayarla] = useState<Record<Yetenek, Kapsam> | null>(null);
  useEffect(() => {
    let iptal = false;
    api
      .kapsam()
      .then((liste) => {
        if (iptal) return;
        const m = {} as Record<Yetenek, Kapsam>;
        for (const y of liste) m[y.yetenek as Yetenek] = y;
        ayarla(m);
      })
      .catch(() => {
        /* kapsam bilinmiyor: kisitlama yok, sunucu karar versin */
      });
    return () => {
      iptal = true;
    };
  }, []);
  return k;
}

/** Kapsam disi urunde istegi HIC ATMADAN sebebi yazan kart.
 *
 *  Bos bir kart veya "veri yok" yazisi degil: kullanicinin ogrenmesi gereken
 *  sey verinin gelmedigi degil, bu hesabin bu urun icin yapilamayacagi ve
 *  nedeni. */
function KapsamDisiKarti({ baslik, gerekce }: { baslik: string; gerekce: string }) {
  return (
    <Kart baslik={baslik} etiket={<span className="rozet yalin">kapsam dışı</span>}>
      <p className="tarla-kapsam">{gerekce}</p>
    </Kart>
  );
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
  oneri,
  onHaritayaGit,
}: {
  nokta: Nokta | null;
  oneri: Katman<OneriKumesi>;
  onHaritayaGit: () => void;
}) {
  const [urun, setUrun] = useState("domates");
  const [asama, setAsama] = useState("mid");
  const [dekar, setDekar] = useState("");
  const kapsam = useKapsam();

  // Secili tarlaya onerilen urunler + kalan tum urunler.
  //
  // TUM URUNLERIN KAYNAGI uc kapsam kumesinin BIRLESIMI, kesisimi degil:
  // kesisim 5 urune inerdi (zararli tablosu en dar olan), oysa iklim riski
  // 116 urun cevapliyor. Birlesimde bir urun bazi kartlarda kapsam disi
  // cikar; o kart sebebini kendisi yazar.
  const { onerilen, digerleri } = useMemo(() => {
    const onerilenler: UrunSecenek[] =
      oneri.durum === "ok"
        ? oneri.veri.oneriler.map((o) => ({ anahtar: o.urun, ad: o.ad, skor: o.skor }))
        : [];
    const secilmis = new Set(onerilenler.map((o) => o.anahtar));
    const tumu = new Map<string, string>();
    for (const y of Object.values(kapsam ?? {})) {
      for (const u of y.urunler) tumu.set(u.anahtar, u.ad);
    }
    const kalan: UrunSecenek[] = [...tumu.entries()]
      .filter(([a]) => !secilmis.has(a))
      .map(([anahtar, ad]) => ({ anahtar, ad }))
      .sort((a, b) => a.ad.localeCompare(b.ad, "tr"));
    return { onerilen: onerilenler, digerleri: kalan };
  }, [oneri, kapsam]);

  // Secili urun listede hic yoksa (kapsam gelmeden once secilen bir urun
  // sonradan listeden dusmus olabilir) secenegi yine de goster; aksi halde
  // <select> sessizce ilk secenege atlar ve kullanici baska bir urunun
  // sonucuna bakiyor olur.
  const listedeVar =
    onerilen.some((o) => o.anahtar === urun) || digerleri.some((o) => o.anahtar === urun);

  const disi = (yetenek: Yetenek): string | null => {
    const k = kapsam?.[yetenek];
    if (!k) return null;
    return k.urunler.some((u) => u.anahtar === urun) ? null : k.gerekce;
  };
  const sulamaDisi = disi("sulama");
  const iklimDisi = disi("iklim");
  const zararliDisi = disi("zararli");

  // Ciftci dekar konusur; API metrekare bekliyor. Cevrim TEK YERDE.
  const alanM2 = (() => {
    const d = Number(dekar.replace(",", "."));
    return dekar.trim() !== "" && Number.isFinite(d) && d > 0 ? d * 1000 : undefined;
  })();

  // Kapsam disi ise cagri null: istek HIC atilmaz. Atip 422 yakalamak da
  // olurdu ama o zaman kullaniciya kirmizi bir hata gorunurdu; oysa bu bir
  // hata degil, bilginin sinirlari.
  const sulamaCagri = useCallback(
    () =>
      nokta ? api.sulama(nokta.lat, nokta.lon, urun, asama, alanM2) : Promise.reject(),
    [nokta, urun, asama, alanM2],
  );
  const riskCagri = useCallback(
    () => (nokta ? api.iklimRisk(nokta.lat, nokta.lon, urun) : Promise.reject()),
    [nokta, urun],
  );
  const zararliCagri = useCallback(
    () => (nokta ? api.zararli(nokta.lat, nokta.lon, urun) : Promise.reject()),
    [nokta, urun],
  );

  // Kapsam disi ise cagri null: istek HIC atilmaz. Atip 422 yakalamak da
  // olurdu ama o zaman kullaniciya kirmizi bir hata gorunurdu; oysa bu bir
  // hata degil, bilginin sinirlari.
  const sulama = useIstek<Sulama>(nokta && !sulamaDisi ? sulamaCagri : null);
  const risk = useIstek<IklimRisk>(nokta && !iklimDisi ? riskCagri : null);
  const zararli = useIstek<Zararli>(nokta && !zararliDisi ? zararliCagri : null);

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
            {!listedeVar && <option value={urun}>{urun.replace(/_/g, " ")}</option>}
            {onerilen.length > 0 && (
              <optgroup label="Bu tarlaya önerilenler">
                {onerilen.map((u) => (
                  <option key={u.anahtar} value={u.anahtar}>
                    {u.ad} · {u.skor?.toFixed(0)} puan
                  </option>
                ))}
              </optgroup>
            )}
            {digerleri.length > 0 && (
              <optgroup label="Diğer ürünler">
                {digerleri.map((u) => (
                  <option key={u.anahtar} value={u.anahtar}>
                    {u.ad}
                  </option>
                ))}
              </optgroup>
            )}
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
        {sulamaDisi ? (
          <KapsamDisiKarti baslik="Sulama" gerekce={sulamaDisi} />
        ) : (
          <SulamaKarti katman={sulama} />
        )}
        {iklimDisi ? (
          <KapsamDisiKarti baslik="İklim riski" gerekce={iklimDisi} />
        ) : (
          <RiskKarti katman={risk} />
        )}
        {zararliDisi ? (
          <KapsamDisiKarti baslik="Zararlı takvimi" gerekce={zararliDisi} />
        ) : (
          <ZararliKarti katman={zararli} />
        )}
      </div>
    </div>
  );
}
