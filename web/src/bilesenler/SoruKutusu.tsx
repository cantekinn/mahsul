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
 */
import { useState } from "react";
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
  const [metin, setMetin] = useState("");
  const [yanit, setYanit] = useState<Soru | null>(null);
  const [hata, setHata] = useState<string | null>(null);
  const [bekliyor, setBekliyor] = useState(false);

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

  return (
    <section className="soru-kutusu">
      <form
        className="soru-satir"
        onSubmit={(e) => {
          e.preventDefault();
          void gonder(metin);
        }}
      >
        <input
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
              className="soru-kapat"
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
              onClick={() => onSekme(yanit.sekme)}
            >
              {yanit.niyet_tr} sekmesine git
            </button>
          )}
        </div>
      )}
    </section>
  );
}
