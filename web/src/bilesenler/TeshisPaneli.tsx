/**
 * Hastalik teshis paneli: dosya sec / kamera cek -> analiz et -> sonuc karti.
 *
 * TASARIM KARARLARI:
 * - Kamera ve dosya secici TEK input: `accept="image/*" capture="environment"`.
 *   Mobilde arka kamera acilir; masaustunde capture yok sayilir ve normal
 *   dosya secici cikar. Iki ayri dugme kullanmadik cunku iOS Safari'da
 *   "capture" olmayan dugme kameraya girmiyor, olan dugme galeriye girmiyor;
 *   yani iki dugme iki OS'ta farkli davranir. Tek input her yerde ise yariyor.
 * - Onizleme URL.createObjectURL ile: base64'e cevirmek 5 MB dosyayi tarayicida
 *   ~7 MB string'e cevirir, gereksiz bellek. blob URL sifir kopya.
 * - Seviye renkleri semantik: kesin=yesil, olasi=sari, belirsiz=turuncu,
 *   tanimsiz=gri. Kullanici "yesil = guvenli" beklentisiyle karistirmasin diye
 *   "yesil = model kesin" oldugunu rozette ACIKCA yaziyoruz.
 * - Tedavi bilgisi accordeon degil dogrudan acik: 4 alan (belirti, dogal,
 *   kimyasal, korunma) hem az yer tutar hem de tikla-ac adimini ortadan
 *   kaldirir. Ciftci tarlada iken hizli okumali.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { ApiHatasi } from "../api/istemci";
import { teshisEt, type Teshis } from "../api/teshis";
import { kucult } from "../gorsel";
import { Kart } from "./Durum";

type Durum =
  | { tur: "bos" }
  | { tur: "hazirlaniyor" }
  | { tur: "secildi"; dosya: File; onizlemeUrl: string; kazanc: string | null }
  | { tur: "yukleniyor"; dosya: File; onizlemeUrl: string; kazanc: string | null }
  | { tur: "sonuc"; dosya: File; onizlemeUrl: string; kazanc: string | null; teshis: Teshis }
  | { tur: "hata"; dosya: File; onizlemeUrl: string; kazanc: string | null; mesaj: string };

const MAX_MB = 6;

/** "3.8 MB -> 0.3 MB" gibi bir ozet; kucultme olmadiysa null. */
function kazancMetni(oncesi: number, sonrasi: number): string | null {
  if (sonrasi >= oncesi * 0.95) return null;
  const mb = (b: number) => (b / 1024 / 1024).toFixed(1);
  return `${mb(oncesi)} MB fotoğraf ${mb(sonrasi)} MB'a küçültüldü (model 224 piksel kullanıyor, ayrıntı kaybı yok)`;
}

function seviyeRenk(seviye: string): "kesin" | "olasi" | "belirsiz" | "tanimsiz" {
  if (seviye === "kesin" || seviye === "olasi" || seviye === "belirsiz" || seviye === "tanimsiz") {
    return seviye;
  }
  return "belirsiz";
}

function seviyeYazi(seviye: string): string {
  switch (seviye) {
    case "kesin":
      return "Kesin";
    case "olasi":
      return "Olası";
    case "belirsiz":
      return "Belirsiz";
    case "tanimsiz":
      return "Tanımsız";
    default:
      return seviye;
  }
}

export default function TeshisPaneli() {
  const [durum, setDurum] = useState<Durum>({ tur: "bos" });
  const dosyaGirdisi = useRef<HTMLInputElement>(null);

  // Onizleme URL'ini component unmount olurken serbest birak. Aksi halde
  // blob URL'leri bellekte kalir ve /teshis sekmesinden cikip donen kullanici
  // gorunmeyen kopyalari birakir.
  useEffect(() => {
    return () => {
      if (durum.tur !== "bos" && durum.tur !== "hazirlaniyor") {
        URL.revokeObjectURL(durum.onizlemeUrl);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const dosyaSec = useCallback(async (secilen: File) => {
    // ONCE KUCULT, SONRA BOYUT KONTROLU. Sirasi onemli: telefon kamerasinin
    // 4 MB'lik ciktisi kucultmeden once 6 MB tavaninin altinda olsa bile
    // kirsal baglantida yavas yuklenir. Kucultme ayrica EXIF donusunu de
    // duzeltir (bkz gorsel.ts).
    setDurum((eski) => {
      if (eski.tur !== "bos" && eski.tur !== "hazirlaniyor") {
        URL.revokeObjectURL(eski.onizlemeUrl);
      }
      return { tur: "hazirlaniyor" };
    });

    const yeni = await kucult(secilen);
    const kazanc = kazancMetni(secilen.size, yeni.size);
    const onizlemeUrl = URL.createObjectURL(yeni);

    // Kucultmeye ragmen tavani asiyorsa (cok buyuk panorama vb.) reddet.
    if (yeni.size > MAX_MB * 1024 * 1024) {
      setDurum({
        tur: "hata",
        dosya: yeni,
        onizlemeUrl,
        kazanc,
        mesaj: `Dosya çok büyük: ${(yeni.size / 1024 / 1024).toFixed(1)} MB (üst sınır ${MAX_MB} MB)`,
      });
      return;
    }
    setDurum({ tur: "secildi", dosya: yeni, onizlemeUrl, kazanc });
  }, []);

  const dosyaDegisti = (e: React.ChangeEvent<HTMLInputElement>) => {
    const d = e.target.files?.[0];
    if (d) void dosyaSec(d);
  };

  const analizEt = async () => {
    if (durum.tur !== "secildi" && durum.tur !== "hata" && durum.tur !== "sonuc") return;
    const { dosya, onizlemeUrl, kazanc } = durum;
    setDurum({ tur: "yukleniyor", dosya, onizlemeUrl, kazanc });
    try {
      const t = await teshisEt(dosya);
      setDurum({ tur: "sonuc", dosya, onizlemeUrl, kazanc, teshis: t });
    } catch (e) {
      setDurum({
        tur: "hata",
        dosya,
        onizlemeUrl,
        kazanc,
        mesaj: e instanceof ApiHatasi ? e.message : "Sunucuya ulaşılamadı",
      });
    }
  };

  const temizle = () => {
    if (durum.tur !== "bos" && durum.tur !== "hazirlaniyor") {
      URL.revokeObjectURL(durum.onizlemeUrl);
    }
    setDurum({ tur: "bos" });
    if (dosyaGirdisi.current) dosyaGirdisi.current.value = "";
  };

  return (
    <div className="teshis-panel">
      <Kart baslik="Hastalık teşhisi">
        <p className="teshis-tanit">
          Yaprak fotoğrafı çekin veya seçin. Model 45 hastalığı 16 üründe
          tanıyor (domates, patates, biber, elma, üzüm, mısır, çilek, muz,
          zeytin ve daha fazlası). Tedavi önerileri hem doğal hem kimyasal
          seçenek içerir.
        </p>

        <div className="teshis-yukleme">
          {/* accept ve capture birlikte: mobilde arka kamera, masaustunde
              dosya secici. iOS Safari'da "capture" bir on tercih; kullanici
              yine de galeriden secebilir. */}
          <input
            ref={dosyaGirdisi}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={dosyaDegisti}
            className="teshis-input"
            id="teshis-dosya"
          />
          <label htmlFor="teshis-dosya" className="dugme teshis-sec-dugme">
            {durum.tur === "bos" ? "Fotoğraf seç / çek" : "Başka fotoğraf"}
          </label>
          {durum.tur !== "bos" && durum.tur !== "hazirlaniyor" && (
            <button className="dugme yalin" onClick={temizle} type="button">
              Temizle
            </button>
          )}
        </div>

        {durum.tur === "hazirlaniyor" && (
          <p className="bekleyen">Fotoğraf hazırlanıyor...</p>
        )}

        {durum.tur !== "bos" && durum.tur !== "hazirlaniyor" && (
          <>
            <div className="teshis-onizleme">
              <img src={durum.onizlemeUrl} alt="Seçilen yaprak" />
              <div className="teshis-onizleme-alt">
                <span className="dosya-ad">{durum.dosya.name}</span>
                <span className="dosya-boyut">
                  {(durum.dosya.size / 1024).toFixed(0)} KB
                </span>
              </div>
            </div>
            {/* Kucultme sessizce yapilmaz, kullaniciya SOYLENIR. Ciftci
                fotografinin degistirildigini bilmeli ve ayrinti kaybi olmadigini
                gorebilmeli. */}
            {durum.kazanc && <p className="teshis-kazanc">{durum.kazanc}</p>}
          </>
        )}

        {(durum.tur === "secildi" || durum.tur === "hata") && (
          <button
            className="dugme birincil teshis-analiz-dugme"
            onClick={analizEt}
            type="button"
          >
            Analiz et
          </button>
        )}

        {durum.tur === "yukleniyor" && (
          <p className="bekleyen">Model çalışıyor, birkaç saniye sürer...</p>
        )}

        {durum.tur === "hata" && <p className="hata">{durum.mesaj}</p>}
      </Kart>

      {durum.tur === "sonuc" && <SonucKarti teshis={durum.teshis} />}
    </div>
  );
}

function SonucKarti({ teshis }: { teshis: Teshis }) {
  const renk = seviyeRenk(teshis.seviye);
  const yuzde = Math.round(teshis.guven * 100);

  return (
    <Kart
      baslik={teshis.etiket_tr}
      etiket={
        <span className={`teshis-rozet ${renk}`}>{seviyeYazi(teshis.seviye)}</span>
      }
    >
      <div className="teshis-guven-satiri">
        <div className="teshis-guven-cubugu" aria-label={`Güven: %${yuzde}`}>
          <div
            className={`teshis-guven-doldu ${renk}`}
            style={{ width: `${yuzde}%` }}
          />
        </div>
        <span className="teshis-guven-yazi">%{yuzde} güven</span>
      </div>

      {teshis.urun_tr && (
        <p className="teshis-urun">
          Ürün: <strong>{teshis.urun_tr}</strong>
        </p>
      )}

      {teshis.uyari && <p className="teshis-uyari">{teshis.uyari}</p>}

      {teshis.tedavi && (
        <div className="teshis-tedavi">
          <h3>{teshis.tedavi.ad}</h3>
          {teshis.tedavi.belirti && (
            <div className="tedavi-bolum">
              <h4>Belirti</h4>
              <p>{teshis.tedavi.belirti}</p>
            </div>
          )}
          {teshis.tedavi.dogal && (
            <div className="tedavi-bolum">
              <h4>Doğal / kültürel önlem</h4>
              <p>{teshis.tedavi.dogal}</p>
            </div>
          )}
          {teshis.tedavi.kimyasal && (
            <div className="tedavi-bolum">
              <h4>Kimyasal (son çare)</h4>
              <p>{teshis.tedavi.kimyasal}</p>
            </div>
          )}
          {teshis.tedavi.korunma && (
            <div className="tedavi-bolum">
              <h4>Sonraki sezon için korunma</h4>
              <p>{teshis.tedavi.korunma}</p>
            </div>
          )}
        </div>
      )}

      {!teshis.tedavi && teshis.etiket.endsWith("_saglikli") && (
        <p className="teshis-saglikli">
          Yaprak sağlıklı görünüyor. Tedavi gerekmez.
        </p>
      )}

      {teshis.topk.length > 1 && (
        <div className="teshis-alt-tahminler">
          <h4>Alternatif olasılıklar</h4>
          <ol>
            {teshis.topk.slice(1).map((m) => (
              <li key={m.etiket}>
                <span>{m.etiket_tr}</span>
                <span className="alt-guven">%{Math.round(m.guven * 100)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </Kart>
  );
}
