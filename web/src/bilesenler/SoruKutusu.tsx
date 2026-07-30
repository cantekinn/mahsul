/**
 * Serbest metin sorusu: "ne yazarsam yazayim dogru cevaba gideyim".
 *
 * NEDEN VAR
 * Uc sekme, alti hesap ve 116 urun var. Sekme cubugu bunlari gezmenin dogru
 * yolu ama ciftcinin kafasindaki cumle "domatese kac litre su vermeliyim",
 * "Sulama sekmesi" degil. Bu kutu o cumleyi alip hangi uzmanin cevaplayacagini
 * bulur (GET /sor) ve cevabi dogrudan yazar.
 *
 * YONLENDIRME ILE CEVAP AYRI SEYLER
 * Sunucu iki tur yanit dondurebiliyor:
 *   yonlendirme=false -> uzman gercekten hesapladi, cevap metni burada.
 *   yonlendirme=true  -> cevap baska sekmede uretiliyor (urun onerisi zaten
 *                        haritada hesaplaniyor; teshis fotograf istiyor) ya da
 *                        henuz nokta secilmemis. Bu durumda dugme cikar ve
 *                        kullaniciyi oraya goturur.
 * Iki durumu ayni gostermek, "cevap verildi" sanip beklemeye yol acardi.
 *
 * NEDEN SAG ALT KOSEDE, SEKME CUBUGUNUN ALTINDA DEGIL
 * Once sekmelerle icerigin arasinda, her zaman acik duruyordu. Orada iki sey
 * yanlisti: (1) ucu de kendi ekranini hak eden uc sekmenin ustunden dikey
 * alan yiyordu, (2) her acilista "once buraya yaz" diye kendini one koyuyordu
 * ama bu kutu bir baslangic noktasi degil, akla SONRADAN gelen sorunun yeri.
 * Simdi kapali duruyor, dugmeye basilinca aciliyor. Kapali haldeki maliyeti
 * bir dugme; acikken ekranin ustunu degil, kendi kosesini kapliyor.
 */
import { useEffect, useRef, useState } from "react";
import { api, ApiHatasi } from "../api/istemci";
import type { Soru } from "../api/istemci";

type Nokta = { lat: number; lon: number };

const ORNEKLER = [
  "Domatese kaç litre su vermeliyim",
  "Don riski var mı",
  "Karbon ayak izim ne kadar",
];

export default function SoruKutusu({
  nokta,
  alanM2,
  onSekme,
}: {
  nokta: Nokta | null;
  // Alan opsiyonel ama GONDERILMESI onemli: karbon envanteri onsuz
  // hesaplanamaz ve sunucu "once alanini girin" der. Kullanici alani Tarla
  // sekmesinde zaten girmis olabilir; girdiyse ayni sey ikinci kez sorulmamali.
  alanM2: number | undefined;
  onSekme: (sekme: string) => void;
}) {
  const [acik, setAcik] = useState(false);
  const [metin, setMetin] = useState("");
  const [yanit, setYanit] = useState<Soru | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [bekliyor, setBekliyor] = useState(false);
  const alan = useRef<HTMLInputElement>(null);

  // Acilinca imlec kutuya gidiyor: kullanici dugmeye zaten "yazacagim" diye
  // basti, ikinci bir tiklama istemek o niyeti bosa cikarir.
  useEffect(() => {
    if (acik) alan.current?.focus();
  }, [acik]);

  // Escape kapatir. Ekranin ustune binen her seyin klavyeyle kapanabilmesi
  // gerekiyor; fare kullanmayan biri icin tek cikis yolu bu.
  useEffect(() => {
    if (!acik) return;
    const bas = (e: KeyboardEvent) => {
      if (e.key === "Escape") setAcik(false);
    };
    window.addEventListener("keydown", bas);
    return () => window.removeEventListener("keydown", bas);
  }, [acik]);

  const gonder = async (soru: string) => {
    const s = soru.trim();
    if (s.length < 2) return;
    setBekliyor(true);
    setHata(null);
    try {
      setYanit(await api.sor(s, nokta?.lat, nokta?.lon, alanM2));
    } catch (e) {
      setYanit(null);
      setHata(e instanceof ApiHatasi ? e.message : "Sunucuya ulaşılamadı");
    } finally {
      setBekliyor(false);
    }
  };

  if (!acik) {
    return (
      <button
        type="button"
        className="soru-acici"
        onClick={() => setAcik(true)}
        aria-expanded={false}
      >
        {/* Ikon TEK BASINA birakilmadi. Bu uygulamanin kullanicisi her gun
            yazilim kullanan biri degil; kosede duran soru isaretinin ne
            yaptigini tahmin etmesini beklemek yerine yaziyi da koyuyoruz. */}
        <span aria-hidden="true">?</span>
        <span className="soru-acici-yazi">Soru sor</span>
      </button>
    );
  }

  return (
    <section className="soru-kutusu" role="dialog" aria-label="Tarla sorusu">
      <div className="soru-bas">
        <span className="soru-baslik">Tarlanızla ilgili sorun</span>
        <button
          type="button"
          className="soru-kapat"
          onClick={() => setAcik(false)}
          aria-label="Soru kutusunu kapat"
        >
          ×
        </button>
      </div>

      <form
        className="soru-satir"
        onSubmit={(e) => {
          e.preventDefault();
          void gonder(metin);
        }}
      >
        <input
          ref={alan}
          type="search"
          className="alan"
          placeholder="Tarlanızla ilgili bir şey sorun"
          aria-label="Tarlanızla ilgili soru"
          value={metin}
          onChange={(e) => setMetin(e.target.value)}
        />
        <button type="submit" className="dugme birincil" disabled={bekliyor}>
          {bekliyor ? "Bakılıyor..." : "Sor"}
        </button>
      </form>

      {/* Ornekler yalnizca HENUZ SORULMAMISKEN gorunur: cevap geldikten sonra
          ekranda durmalari, cevabin kendisiyle yarisan bir ikinci odak
          yaratirdi. */}
      {!yanit && !hata && (
        <div className="soru-ornekler">
          {ORNEKLER.map((o) => (
            <button
              key={o}
              type="button"
              className="soru-ornek"
              onClick={() => {
                setMetin(o);
                void gonder(o);
              }}
            >
              {o}
            </button>
          ))}
        </div>
      )}

      {hata && <p className="soru-hata">{hata}</p>}

      {yanit && (
        <div className="soru-yanit">
          <div className="soru-yanit-bas">
            <span className="rozet">{yanit.niyet_tr}</span>
            <button
              type="button"
              className="soru-yanit-kapat"
              onClick={() => setYanit(null)}
              aria-label="Cevabı kapat"
            >
              Kapat
            </button>
          </div>
          {/* Uzmanlarin cevabi satir satir kuruluyor (madde listeleri var);
              pre-wrap olmadan hepsi tek paragrafa yapisirdi. */}
          <p className="soru-cevap">{yanit.cevap}</p>
          {yanit.yonlendirme && (
            <button
              type="button"
              className="dugme"
              onClick={() => {
                onSekme(yanit.sekme);
                // Panel de kapaniyor: kullaniciyi bir sekmeye gonderip
                // gonderdigimiz seyin ustune bir kutu birakmak, tarif
                // edilen yeri gormesini engellerdi.
                setAcik(false);
              }}
            >
              {yanit.niyet_tr} sekmesine git
            </button>
          )}
        </div>
      )}
    </section>
  );
}
