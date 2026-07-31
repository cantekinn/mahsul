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
import TarlaPaneli from "./bilesenler/TarlaPaneli";
import SoruKutusu from "./bilesenler/SoruKutusu";
import ParselSecici, { useTkgmParselleri } from "./bilesenler/ParselSecici";
import { api, ApiHatasi } from "./api/istemci";
import type { Konum, OneriKumesi, Parseller, Toprak } from "./api/istemci";
import type { Katman } from "./bilesenler/Durum";
import "./stil.css";

type Nokta = { lat: number; lon: number };
type Gorunum = "harita" | "teshis" | "tarla";

const SEKMELER: { anahtar: Gorunum; ad: string; alt: string }[] = [
  {
    anahtar: "harita",
    ad: "Ürün önerisi",
    alt: "Dünyanın herhangi bir noktasında ne yetişir. Haritaya tıklayın veya rastgele bir tarım noktası seçin.",
  },
  {
    anahtar: "tarla",
    ad: "Tarla takvimi",
    alt: "Seçili nokta için sulama, iklim riski ve zararlı takvimi.",
  },
  {
    anahtar: "teshis",
    ad: "Hastalık teşhisi",
    alt: "Yaprak fotoğrafından hastalık teşhisi. 45 hastalık, 16 ürün.",
  },
];

/** Marka isareti: filiz.
 *
 *  Cizim public/favicon.svg ile AYNI yollardan olusuyor, yeni bir sekil
 *  uydurulmadi. Sekme ikonu, ana ekran ikonu ve baslik ayni isareti
 *  gosterdiginde kullanici uygulamayi tek bir seyle taniyor.
 *
 *  Satir ici SVG: tek bir sekil icin ayri bir ag istegi ya da ikon
 *  kutuphanesi eklemenin karsiligi yok. <img src="/favicon.svg"> de olurdu
 *  ama o zaman isaret sayfayla ayni anda gelmez, baslik bir kare bos durur. */
function MarkaIsareti() {
  return (
    <svg
      className="marka-isaret"
      viewBox="0 0 64 64"
      width="40"
      height="40"
      aria-hidden="true"
      focusable="false"
    >
      <rect width="64" height="64" rx="14" fill="var(--yesil)" />
      <path
        d="M32 53 V32"
        stroke="#ffffff"
        strokeWidth="5"
        strokeLinecap="round"
        fill="none"
      />
      <path d="M31 37 C 31 24 22 15 11 14 C 10 27 18 36 31 37 Z" fill="#ffffff" />
      <path d="M33 44 C 33 33 41 25 53 24 C 54 36 45 44 33 44 Z" fill="#a8d5a2" />
    </svg>
  );
}

/** Adresteki ?g= degeri sekmeyi acar. Taninmayan deger haritaya duser. */
function adrestenGorunum(): Gorunum {
  const g = new URLSearchParams(window.location.search).get("g");
  return SEKMELER.some((s) => s.anahtar === g) ? (g as Gorunum) : "harita";
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
  // Parsel alani BURADA duruyor, Tarla panelinde degil. Iki yerde birden
  // gerekiyor: karbon karti (Tarla sekmesi) ve soru kutusu (her sekme).
  // Panelin icinde kalsaydi kullanici alani girdikten sonra "karbon ayak izim
  // ne kadar" diye sordugunda sunucu yine "once alanini girin" derdi; yani
  // kullanici bilgiyi vermis olmasina ragmen ayni sey tekrar istenirdi.
  const [dekar, setDekar] = useState("");
  // Tapu parselleri de BURADA: secici artik iki sekmede birden duruyor ve
  // listeyi her sekmenin ayri cekmesi, ayni dosyayi sekme degistikce yeniden
  // indirmek olurdu.
  const tkgm = useTkgmParselleri();

  /** Parsel secimi noktayi VE alani birden kurar.
   *
   *  Ikisini birden yazmasi onemli: alan elle istenseydi ciftcinin tapudaki
   *  degeri hatirlamasi gerekirdi, oysa deger zaten sorgu sonucunda var ve
   *  karbon karti onsuz calismiyor. */
  const parselSec = (lat: number, lon: number, d: number) => {
    setNokta({ lat, lon });
    setDekar(String(d));
  };

  // Ciftci dekar konusur, API metrekare bekler. Cevrim TEK YERDE, burada.
  const alanM2 = (() => {
    const d = Number(dekar.replace(",", "."));
    return dekar.trim() !== "" && Number.isFinite(d) && d > 0 ? d * 1000 : undefined;
  })();

  useEffect(() => {
    const url = new URL(window.location.href);
    if (nokta) {
      url.searchParams.set("lat", String(nokta.lat));
      url.searchParams.set("lon", String(nokta.lon));
    } else {
      url.searchParams.delete("lat");
      url.searchParams.delete("lon");
    }
    if (gorunum === "harita") {
      url.searchParams.delete("g");
    } else {
      url.searchParams.set("g", gorunum);
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
        <div className="marka">
          <MarkaIsareti />
          <h1>Tarım Asistanı</h1>
        </div>
        {gorunum === "harita" && (
          <button className="dugme" onClick={rastgeleSec} disabled={rastgeleYukleniyor}>
            {rastgeleYukleniyor ? "Nokta aranıyor..." : "Rastgele nokta"}
          </button>
        )}
      </header>

      {/* Sekme cubugu YAPISKAN, marka satiri DEGIL.
          Oneri listesi acikken sayfa 3400 px'i geciyordu; sekme degistirmek
          icin her seferinde en basa donmek gerekiyordu, yani ana gezinme
          sayfanin yalnizca ilk ekraninda vardi. Marka satirini da yapisik
          tutmak seridi telefonda 142 px'e cikariyordu (ekranin altida biri);
          marka kimligi surekli gorunmek zorunda degil, gezinme zorunda.
          Serit simdi 70 px. */}
      <div className="ust-serit">
        <nav className="sekme-cubugu" role="tablist">
          {SEKMELER.map((s) => (
            <button
              key={s.anahtar}
              type="button"
              role="tab"
              aria-selected={gorunum === s.anahtar}
              className={`sekme ${gorunum === s.anahtar ? "aktif" : ""}`}
              onClick={() => setGorunum(s.anahtar)}
            >
              {s.ad}
            </button>
          ))}
        </nav>
      </div>

      {/* Sekme aciklamasi SERIDIN DISINDA: iki satirlik bir cumle yapisik
          seritte duraydi, serit her ekranda 40 px daha uzun olurdu ve
          telefonda goruntunun besde birini kaplardi. Aciklama zaten bir kez
          okunup gecilen bir metin, sekme adi ise surekli lazim. */}
      <p className="gorunum-alt">{SEKMELER.find((s) => s.anahtar === gorunum)?.alt}</p>

      {/* Soru kutusu SEKMELERIN ALTINDA ve her sekmede duruyor: kullanicinin
          sorusu hangi sekmede aklina gelirse gelsin ayni yerde sorulabilsin.
          Sunucu niyeti bulup ya cevabi yazar ya da dogru sekmeye gonderir. */}
      <SoruKutusu
        nokta={nokta}
        alanM2={alanM2}
        onSekme={(s) => setGorunum(s as Gorunum)}
      />

      {gorunum === "harita" && (
        <>
          <Kisayollar onSec={(lat, lon) => setNokta({ lat, lon })} secili={nokta} />

          {/* Parsel secici KISAYOLLARIN YANINDA: ikisi de "noktayi nasil
              secerim" sorusunun cevabi. Haritada gozle tarla aramak yerine
              tapu kaydini secen kullanici, dort katmanin dordunu de (konum,
              toprak, parsel, oneri) hicbir sey daha yapmadan alir.

              tarla-secim sinifi BILEREK yeniden kullaniliyor: bu, oradaki
              kutunun aynisi. Ayni gorunum icin ikinci bir kural kumesi
              yazmak, ilerde birini guncelleyip digerini unutmak demekti. */}
          {tkgm.length > 0 && (
            <form
              className="tarla-secim parsel-satir"
              onSubmit={(e) => e.preventDefault()}
            >
              <ParselSecici liste={tkgm} onSec={parselSec} sinif="parsel-alan" />
              <span className="parsel-alt">
                Tapu kaydını seçtiğinizde nokta ve alan birlikte kurulur.
              </span>
            </form>
          )}

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
      )}

      {gorunum === "tarla" && (
        <main className="govde tarla-govde">
          {/* Oneri katmani harita sekmesi icin zaten cekiliyor; ayni sonucu
              burada urun listesini siralamak icin kullaniyoruz. Ikinci bir
              istek atmak ayni noktanin iki farkli oneri listesini
              uretebilirdi. */}
          <TarlaPaneli
            nokta={nokta}
            oneri={oneri}
            dekar={dekar}
            alanM2={alanM2}
            tkgm={tkgm}
            onDekar={setDekar}
            onHaritayaGit={() => setGorunum("harita")}
            onNoktaSec={(lat, lon) => setNokta({ lat, lon })}
          />
        </main>
      )}

      {gorunum === "teshis" && (
        <main className="govde teshis-govde">
          {/* Nokta VERILIR ama zorunlu degildir: teshis fotograftan cikar,
              konum bilmeyi gerektirmez. Nokta yalnizca sezon gunlugu icin
              lazim (hangi tarlanin gunlugu). Nokta secilmemisse teshis yine
              calisir, sadece gunluk yazma ve tekrar uyarisi kapali kalir. */}
          <TeshisPaneli nokta={nokta} />
        </main>
      )}

      {/* Alt bilgi HER SEKMEDE duruyor ve tek isi var: ekrandaki sayilarin
          NEREDEN geldigini yazmak. Uygulama "toprakta %2.1 organik madde var"
          diyor; bunun bir uydu urununden mi yoksa bir tahminden mi geldigi
          kullanicinin bilmesi gereken bir sey. Kaynaklar sayfanin icine
          dagitilmis olsaydi (her kartin altina bir satir) kart basina bir
          satir daha eklenir ve okunan bilgiyi seyreltirdi. */}
      <footer className="alt-bilgi">
        <p>
          <strong>Veri kaynakları:</strong> iklim ve buharlaşma Open-Meteo,
          toprak ISRIC SoilGrids, yer adı ve harita OpenStreetMap, ürün
          uygunluğu FAO GAEZ v4, sulama katsayıları FAO-56, sera gazı IPCC 2019
          Tier 1, tapu parselleri TKGM.
        </p>
        <p>
          Bu araç ölçülen veriyi hesaplayıp gösterir; ziraat mühendisi ya da
          laboratuvar analizinin yerine geçmez.
        </p>
        <p className="alt-bilgi-imza">
          Google YZTA 2026 &middot; 14. Grup &middot; Yapay Zeka
        </p>
      </footer>
    </div>
  );
}
