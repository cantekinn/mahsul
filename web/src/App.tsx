/**
 * Uygulama kabugu ve KATMAN YUKLEME SIRASI.
 *
 * Arka uctaki uc noktalari hizlarina gore bolmustuk (konum 0.4-9 s, toprak
 * 3-6 s, parsel 25 s'ye kadar). O bolmenin tek anlami burada ortaya cikar:
 * her katman KENDI durumunu tasir ve geldigi anda ekrana yazilir. Hepsini
 * tek "yukleniyor" bayragina baglasaydik ekran en yavas katmanin hizina
 * inerdi ve arka uctaki ayrim bosa giderdi.
 */
import { useCallback, useEffect, useState } from "react";
import Harita from "./bilesenler/Harita";
import KonumKarti from "./bilesenler/KonumKarti";
import ToprakKarti from "./bilesenler/ToprakKarti";
import ParselKarti from "./bilesenler/ParselKarti";
import OneriListesi from "./bilesenler/OneriListesi";
import Kisayollar from "./bilesenler/Kisayollar";
import TeshisPaneli from "./bilesenler/TeshisPaneli";
import { api, ApiHatasi } from "./api/istemci";
import type { Konum, OneriKumesi, Parseller, Toprak } from "./api/istemci";
import type { Katman } from "./bilesenler/Durum";
import "./stil.css";

type Nokta = { lat: number; lon: number };
type Gorunum = "harita" | "teshis";

/** Adresteki ?g=teshis varsa teshis sekmesi acilir. */
function adrestenGorunum(): Gorunum {
  const p = new URLSearchParams(window.location.search);
  return p.get("g") === "teshis" ? "teshis" : "harita";
}

/** Bir uc noktayi cagirip sonucunu katman durumuna cevirir. */
function useKatman<T>(
  cagir: (lat: number, lon: number) => Promise<T>,
  nokta: Nokta | null,
): Katman<T> {
  const [k, ayarla] = useState<Katman<T>>({ durum: "bos" });
  useEffect(() => {
    if (!nokta) {
      ayarla({ durum: "bos" });
      return;
    }
    // Kullanici hizli hizli nokta degistirirse ONCEKI istegin gec gelen
    // cevabi yenisinin uzerine yazmamali. Bayrak bunu engeller.
    let iptal = false;
    ayarla({ durum: "yukleniyor" });
    cagir(nokta.lat, nokta.lon)
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
  }, [nokta, cagir]);
  return k;
}

/** Adresteki ?lat=&lon= varsa acilista o noktayi secer. */
function adrestenNokta(): Nokta | null {
  const p = new URLSearchParams(window.location.search);
  const lat = Number(p.get("lat"));
  const lon = Number(p.get("lon"));
  if (!p.has("lat") || !p.has("lon") || Number.isNaN(lat) || Number.isNaN(lon)) {
    return null;
  }
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  return { lat, lon };
}

export default function App() {
  // Nokta adreste tutulur: boylece bir sonuc PAYLASILABILIR ve sayfa
  // yenilenince kaybolmaz. Sunum sirasinda ayni noktayi tekrar bulmak icin
  // haritada gezinmek gerekmez.
  const [nokta, setNokta] = useState<Nokta | null>(adrestenNokta);
  const [gorunum, setGorunum] = useState<Gorunum>(adrestenGorunum);
  const [rastgeleYukleniyor, setRastgeleYukleniyor] = useState(false);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (nokta) {
      url.searchParams.set("lat", String(nokta.lat));
      url.searchParams.set("lon", String(nokta.lon));
    } else {
      url.searchParams.delete("lat");
      url.searchParams.delete("lon");
    }
    if (gorunum === "teshis") {
      url.searchParams.set("g", "teshis");
    } else {
      url.searchParams.delete("g");
    }
    window.history.replaceState(null, "", url);
  }, [nokta, gorunum]);

  const konum = useKatman<Konum>(
    useCallback((lat: number, lon: number) => api.konum(lat, lon), []),
    nokta,
  );
  const toprak = useKatman<Toprak>(
    useCallback((lat: number, lon: number) => api.toprak(lat, lon), []),
    nokta,
  );
  const parseller = useKatman<Parseller>(
    useCallback((lat: number, lon: number) => api.parseller(lat, lon), []),
    nokta,
  );
  const oneri = useKatman<OneriKumesi>(
    useCallback((lat: number, lon: number) => api.oneri(lat, lon), []),
    nokta,
  );

  const rastgeleSec = async () => {
    setRastgeleYukleniyor(true);
    try {
      const r = await api.rastgele();
      setNokta({ lat: r.lat, lon: r.lon });
    } finally {
      setRastgeleYukleniyor(false);
    }
  };

  return (
    <div className="kabuk">
      <header className="baslik">
        <div>
          <h1>Tarım Asistanı</h1>
          <p className="alt">
            {gorunum === "harita"
              ? "Dünyanın herhangi bir noktasında ne yetişir. Haritaya tıklayın veya rastgele bir tarım noktası seçin."
              : "Yaprak fotoğrafından hastalık teşhisi. 45 hastalık, 16 ürün."}
          </p>
        </div>
        {gorunum === "harita" && (
          <button className="dugme" onClick={rastgeleSec} disabled={rastgeleYukleniyor}>
            {rastgeleYukleniyor ? "Nokta aranıyor..." : "Rastgele nokta"}
          </button>
        )}
      </header>

      {/* Sekme cubugu: iki gorunum arasindaki tek anahtar. URL'ye yaziliyor,
          paylasilabilir ve yenilemeye dayanikli. */}
      <nav className="sekme-cubugu" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={gorunum === "harita"}
          className={`sekme ${gorunum === "harita" ? "aktif" : ""}`}
          onClick={() => setGorunum("harita")}
        >
          Ürün önerisi
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={gorunum === "teshis"}
          className={`sekme ${gorunum === "teshis" ? "aktif" : ""}`}
          onClick={() => setGorunum("teshis")}
        >
          Hastalık teşhisi
        </button>
      </nav>

      {gorunum === "harita" ? (
        <>
          <Kisayollar onSec={(lat, lon) => setNokta({ lat, lon })} secili={nokta} />

          <main className="govde">
            <section className="harita-alan">
              <Harita
                nokta={nokta}
                parseller={parseller.durum === "ok" ? parseller.veri.parseller : []}
                onSec={(lat, lon) => setNokta({ lat, lon })}
              />
            </section>

            <aside className="yan">
              {!nokta ? (
                <div className="kart bos-mesaj">
                  Başlamak için haritadan bir nokta seçin.
                </div>
              ) : (
                <>
                  <KonumKarti katman={konum} nokta={nokta} />
                  <ToprakKarti katman={toprak} />
                  <ParselKarti katman={parseller} />
                </>
              )}
            </aside>
          </main>

          {nokta && (
            <section className="oneri-alan">
              <OneriListesi katman={oneri} />
            </section>
          )}
        </>
      ) : (
        <main className="govde teshis-govde">
          <TeshisPaneli />
        </main>
      )}
    </div>
  );
}
