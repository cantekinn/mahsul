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
import type {
  IklimRisk,
  Kapsam,
  Karbon,
  OneriKumesi,
  Sulama,
  TkgmParsel,
  Zararli,
} from "../api/istemci";
import { Kart, KatmanKabugu } from "./Durum";
import type { Katman } from "./Durum";
import ParselSecici from "./ParselSecici";

type Nokta = { lat: number; lon: number };
type Yetenek = "sulama" | "iklim" | "zararli";
type UrunSecenek = { anahtar: string; ad: string; skor?: number };

const ASAMALAR = [
  { anahtar: "ini", ad: "Fide / ekim" },
  { anahtar: "mid", ad: "Gelişme" },
  { anahtar: "end", ad: "Hasat" },
];

const SULAMA_YONTEMLERI = [
  { anahtar: "damla", ad: "Damla" },
  { anahtar: "yagmurlama", ad: "Yağmurlama" },
  { anahtar: "salma", ad: "Salma" },
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

/** Kullanicinin kendi tarlalari. TARAYICIDA tutulur.
 *
 *  NEDEN SUNUCUDA DEGIL: uygulama ucretsiz barindirma katmaninda calisiyor ve
 *  oradaki dosya sistemi KALICI DEGIL (kalici disk ucretli). Sunucuya yazilan
 *  bir tarla listesi her yayinda ve her uyku sonrasi silinirdi; kullanici
 *  acisindan bu "kaydettim ama kayboldu" yani bir HATA gibi gorunur. Tarayici
 *  deposu silinmez ve kimin hangi tarlaya sahip oldugu bilgisi hic sunucuya
 *  gitmez.
 *
 *  KABUL EDILEN SINIR: kayitlar baska cihazda gorunmez. Bu, sessizce
 *  kaybolan bir listeden iyidir; degistirmek icin hesap sistemi gerekir. */
type Tarla = {
  ad: string;
  lat: number;
  lon: number;
  urun: string;
  asama: string;
  dekar: string;
  yontem: string;
};

const TARLA_ANAHTAR = "tarim.tarlalar";

function useTarlalarim() {
  const [liste, ayarla] = useState<Tarla[]>(() => {
    try {
      const ham = localStorage.getItem(TARLA_ANAHTAR);
      const v: unknown = ham ? JSON.parse(ham) : [];
      return Array.isArray(v) ? (v as Tarla[]) : [];
    } catch {
      // Bozuk ya da erisilemez depo acilisi ENGELLEMEMELI: kayitli tarla
      // yardimci bir ozellik, uygulamanin calisma sarti degil.
      return [];
    }
  });

  const yaz = (yeni: Tarla[]) => {
    ayarla(yeni);
    try {
      localStorage.setItem(TARLA_ANAHTAR, JSON.stringify(yeni));
    } catch {
      /* kota dolu ya da depo kapali: liste yalnizca bu oturumda yasar */
    }
  };

  return {
    liste,
    // Ayni ad UZERINE YAZAR: kullanici "Aksu tarlasi"ni tekrar kaydettiginde
    // beklentisi guncelleme, ayni adla ikinci bir kayit degil.
    kaydet: (t: Tarla) => yaz([...liste.filter((x) => x.ad !== t.ad), t]),
    sil: (ad: string) => yaz(liste.filter((x) => x.ad !== ad)),
  };
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

/** Karbon ayak izi karti.
 *
 *  ALAN ZORUNLU, ve bu bilerek boyle: envanterin her kalemi dekar basina
 *  girdiyle carpiliyor, alan olmadan uretilecek tek sey "dekar basina" sayisi
 *  olurdu ve o da ciftcinin tarlasi hakkinda hicbir sey soylemez. Alan
 *  girilmemisse istek atilmaz, ne istendigi yazilir.
 *
 *  KALEM CUBUKLARI toplama gore oransal. Rakam listesi de olurdu ama karbon
 *  hesabinda tek karar sorusu "en buyuk kalem hangisi"; onu bir bakista
 *  gosteren sey uzunluk.
 */
function KarbonKarti({
  katman,
  alanVar,
}: {
  katman: Katman<Karbon>;
  alanVar: boolean;
}) {
  if (!alanVar) {
    return (
      <Kart baslik="Karbon ayak izi" etiket={<span className="rozet yalin">alan gerekli</span>}>
        <p className="tarla-kapsam">
          Sera gazı envanteri parselin alanıyla hesaplanır. Yukarıdaki
          &quot;Alan (dekar)&quot; kutusunu doldurun.
        </p>
      </Kart>
    );
  }
  return (
    <KatmanKabugu baslik="Karbon ayak izi" katman={katman} bekleyen="Envanter çıkarılıyor...">
      {(v) => {
        const enBuyuk = Math.max(...v.kalemler.map((k) => k.kg_co2e), 1);
        return (
          <Kart
            baslik="Karbon ayak izi"
            etiket={
              <span className={`rozet ${v.gosterge ? "yalin" : ""}`}>
                {v.gosterge ? "gösterge" : "IPCC 2019"}
              </span>
            }
          >
            <div className="tarla-olcum">
              <div className="tarla-buyuk">
                {v.dekar_basina_kg_co2e.toLocaleString("tr-TR")}
                <span className="tarla-birim">kg CO2e/dekar</span>
              </div>
              <div className="tarla-alt">
                {v.urun_tr} · {v.dekar} dekar · {v.sezon_gun} günlük sezon · toplam{" "}
                {Math.round(v.toplam_kg_co2e).toLocaleString("tr-TR")} kg CO2e
              </div>
            </div>

            <ul className="karbon-kalemler">
              {v.kalemler.map((k) => (
                <li key={k.ad}>
                  <div className="karbon-kalem-bas">
                    <span>{k.ad}</span>
                    <strong>{Math.round(k.kg_co2e).toLocaleString("tr-TR")}</strong>
                  </div>
                  {/* Genislik yuzde olarak satir ici veriliyor: deger calisma
                      aninda hesaplaniyor, CSS sinifiyla anlatilamaz. */}
                  <div className="karbon-cubuk">
                    <span style={{ width: `${(k.kg_co2e / enBuyuk) * 100}%` }} />
                  </div>
                  <div className="karbon-kaynak">{k.kaynak}</div>
                </li>
              ))}
            </ul>

            {v.azaltim.length > 0 && (
              <>
                <h4 className="karbon-baslik">Azaltım karşılıkları</h4>
                <ul className="karbon-azaltim">
                  {v.azaltim.map((a) => (
                    <li key={a.baslik}>
                      <div className="karbon-kalem-bas">
                        <span>{a.baslik}</span>
                        {/* Eksi isareti bilincli: bu sayi salima EKLENMIYOR,
                            salimdan dusuyor. */}
                        <strong className="karbon-kazanc">
                          -{Math.round(a.kazanc_kg_co2e).toLocaleString("tr-TR")}
                        </strong>
                      </div>
                      <p className="karbon-kaynak">{a.aciklama}</p>
                    </li>
                  ))}
                </ul>
              </>
            )}

            <details className="karbon-detay">
              <summary>Hesabın sınırları</summary>
              <p className="tarla-uyari">{v.su_senaryosu}</p>
              <p className="tarla-uyari">Kapsam dışı: {v.kapsam_disi.join("; ")}.</p>
            </details>
            <p className="tarla-uyari">{v.aciklama}</p>
          </Kart>
        );
      }}
    </KatmanKabugu>
  );
}

export default function TarlaPaneli({
  nokta,
  oneri,
  dekar,
  alanM2,
  tkgm,
  onDekar,
  onHaritayaGit,
  onNoktaSec,
}: {
  nokta: Nokta | null;
  oneri: Katman<OneriKumesi>;
  // Alan App.tsx'te duruyor, burada degil: soru kutusu her sekmede acik ve o
  // da ayni degeri kullaniyor. Iki ayri kopya tutsaydik kullanicinin girdigi
  // alan, sorduğu soruya ulasmazdi.
  dekar: string;
  alanM2: number | undefined;
  // Parsel listesi de App.tsx'te: ayni secici artik harita sekmesinde de var
  // ve iki ayri cagri, ayni dosyayi iki kez indirmek demekti.
  tkgm: TkgmParsel[];
  onDekar: (v: string) => void;
  onHaritayaGit: () => void;
  onNoktaSec: (lat: number, lon: number) => void;
}) {
  const [urun, setUrun] = useState("domates");
  const [asama, setAsama] = useState("mid");
  // Sulama yontemi SADECE karbon hesabini etkiler (pompalanan su hacmi
  // uygulama verimine bolunuyor). /sulama net bitki su ihtiyacini verir,
  // yontemden bagimsizdir; bu yuzden secim degisince o kart yeniden
  // cekilmez.
  const [yontem, setYontem] = useState("damla");
  const kapsam = useKapsam();
  const tarlalarim = useTarlalarim();

  /** Kayitli tarla TUM secimi geri kurar, sadece noktayi degil.
   *
   *  Tarla kimligi "koordinat" degil "koordinat + ne ektigim + ne kadar alan +
   *  nasil suladigim". Yalniz nokta geri gelseydi kullanici her acilista ayni
   *  dort kutuyu tekrar doldururdu ve kaydin anlami kalmazdi. */
  const tarlaYukle = (t: Tarla) => {
    onNoktaSec(t.lat, t.lon);
    setUrun(t.urun);
    setAsama(t.asama);
    onDekar(t.dekar);
    setYontem(t.yontem);
  };

  const tarlaKaydet = () => {
    if (!nokta) return;
    const ad = window.prompt(
      "Tarlaya bir ad verin",
      `Tarla ${tarlalarim.liste.length + 1}`,
    );
    if (!ad?.trim()) return;
    tarlalarim.kaydet({ ad: ad.trim(), ...nokta, urun, asama, dekar, yontem });
  };

  const parselSec = (lat: number, lon: number, dekar: number) => {
    onNoktaSec(lat, lon);
    onDekar(String(dekar));
  };

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
  // Karbon sulama kapsamina bagli: envanterin pompa kalemi FAO-56 planindan
  // turuyor, Kc yoksa o kalem uydurulamaz. Bu yuzden ayri bir "karbon
  // kapsami" yok, sulama kapsami kullaniliyor.
  const karbonCagri = useCallback(
    () =>
      nokta && alanM2
        ? api.karbon(nokta.lat, nokta.lon, urun, alanM2, { sulama_yontemi: yontem })
        : Promise.reject(),
    [nokta, urun, alanM2, yontem],
  );

  // Kapsam disi ise cagri null: istek HIC atilmaz. Atip 422 yakalamak da
  // olurdu ama o zaman kullaniciya kirmizi bir hata gorunurdu; oysa bu bir
  // hata degil, bilginin sinirlari.
  const sulama = useIstek<Sulama>(nokta && !sulamaDisi ? sulamaCagri : null);
  const risk = useIstek<IklimRisk>(nokta && !iklimDisi ? riskCagri : null);
  const zararli = useIstek<Zararli>(nokta && !zararliDisi ? zararliCagri : null);
  const karbon = useIstek<Karbon>(nokta && !sulamaDisi && alanM2 ? karbonCagri : null);

  // Secici iki yerde de ayni: nokta yokken baslangic yolu, nokta varken
  // parsel degistirme yolu. Tek tanim, iki kullanim.
  const parselSecici = tkgm.length > 0 && (
    <ParselSecici liste={tkgm} onSec={parselSec} />
  );

  // Serit iki yerde de ayni. Nokta yokken kayitli tarlalar TEK BASINA
  // gorunur (kaydetme dugmesi olmadan): kaydedecek bir secim henuz yok.
  const tarlaSeridi = (tarlalarim.liste.length > 0 || nokta) && (
    <div className="tarlalarim">
      {tarlalarim.liste.map((t) => (
        <span key={t.ad} className="tarlam">
          <button type="button" className="tarlam-ad" onClick={() => tarlaYukle(t)}>
            {t.ad}
          </button>
          <button
            type="button"
            className="tarlam-sil"
            onClick={() => tarlalarim.sil(t.ad)}
            aria-label={`${t.ad} kaydını sil`}
          >
            ×
          </button>
        </span>
      ))}
      {nokta && (
        <button type="button" className="dugme yalin" onClick={tarlaKaydet}>
          Bu tarlayı kaydet
        </button>
      )}
    </div>
  );

  if (!nokta) {
    return (
      <div className="kart bos-mesaj">
        <p>
          Tarla takvimi seçili noktanın hava verisiyle çalışır. Haritadan bir
          nokta seçin ya da kayıtlı bir tapu parseli seçin.
        </p>
        {tarlaSeridi}
        {parselSecici && <form className="tarla-secim">{parselSecici}</form>}
        <button type="button" className="dugme birincil" onClick={onHaritayaGit}>
          Haritaya git
        </button>
      </div>
    );
  }

  return (
    <div className="tarla-panel">
      {tarlaSeridi}
      <form className="tarla-secim" onSubmit={(e) => e.preventDefault()}>
        {parselSecici}
        <label className="genis">
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
            placeholder="karbon için gerekli"
            value={dekar}
            onChange={(e) => onDekar(e.target.value)}
          />
        </label>
        <label>
          Sulama yöntemi
          <select value={yontem} onChange={(e) => setYontem(e.target.value)}>
            {SULAMA_YONTEMLERI.map((y) => (
              <option key={y.anahtar} value={y.anahtar}>
                {y.ad}
              </option>
            ))}
          </select>
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
        {sulamaDisi ? (
          <KapsamDisiKarti baslik="Karbon ayak izi" gerekce={sulamaDisi} />
        ) : (
          <KarbonKarti katman={karbon} alanVar={Boolean(alanM2)} />
        )}
      </div>
    </div>
  );
}
