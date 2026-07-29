/**
 * Urun onerileri.
 *
 * IKI KADEMELI AYRIM VAR, sirasi onemli:
 *
 * 1) ZAMAN. Ciftcinin ilk sorusu "bu ay ne ekebilirim". Once bugun ekilebilen
 *    urunler gosterilir, gerisi katlanmis durur ve istenirse acilir. Arka uc
 *    her urun icin ekim_aylari listesini dondurdugu icin bu ayrim tahmin degil,
 *    hesap sonucudur.
 * 2) GRUP. Her bolumun icinde tahil/baklagil/meyve ayri ayri listelenir.
 *    NEDEN: duz siralamada ilk siralara ayni aileden urunler doluyor (olculdu:
 *    Antalya'da ust siralar bastan asaga sebze). Ciftciye gercek secenek sunmak
 *    icin cesitlilik gerekir.
 *
 * COK YILLIKLAR AYRI BOLUMDE, cunku onlar "ekilmez". Agac/asma icin fidan
 *    dikimi soz konusudur ve dikim zamani EcoCrop'ta olmayan bir bilgidir;
 *    uydurmak yerine bolumu ayirip zaman iddiasinda bulunmuyoruz.
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

/**
 * Merkezligi cumleye cevirir.
 *
 * NEDEN GEREKLI: puan doygun. Bursa'da 10 urun birden tam 100 aliyor ve bu bir
 * hata degil; EcoCrop optimum araligin ICINI esit derecede uygun sayar, dort
 * faktorun dordunde de aralik icine dusen her urun 100 alir. Merkezlik bu
 * beraberligi bozmadan aciklar: olculen degerler araligin ortasinda mi
 * kenarinda mi. Puana KATILMAZ (gerekcesi global_reco._merkezlik icinde).
 *
 * "Kenarinda VEYA disinda" diyoruz, "kenarinda" demiyoruz: merkezlik hesabinda
 * aralik disinda kalan faktor 0 sayilir, dolayisiyla dusuk deger iki anlama da
 * gelebilir. Tekini secip yazmak olcumun soylemedigi bir sey soylemek olurdu.
 */
function merkezlikCumlesi(m: number): string {
  if (m >= 0.66) return "ölçümler en iyi aralığın tam ortasında";
  if (m >= 0.33) return "ölçümler en iyi aralığın içinde, ortasında değil";
  return "ölçümler en iyi aralığın kenarında veya dışında";
}

/**
 * Ekim aylarini her zaman bir dizi olarak verir.
 *
 * Alan sunucuda varsayilanli oldugu icin OpenAPI semasinda ZORUNLU degil,
 * dolayisiyla uretilen tipte "string[] | undefined" goruluyor. Sunucu her
 * durumda bir liste donuyor (cok yillikta bos liste) ama tipi elle "zorunlu"ya
 * cevirmek semayi yalanlamak olurdu. Eksikligi burada, tek yerde, sunucunun
 * kendi varsayilaniyla ayni sekilde karsiliyoruz.
 */
function ekimAylari(o: Oneri): string[] {
  return o.ekim_aylari ?? [];
}

function UrunKarti({ o }: { o: Oneri }) {
  const [acik, setAcik] = useState(false);
  const aylar = ekimAylari(o);
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
      <p className="urun-merkez" title={`Merkezlik ${o.merkezlik.toFixed(2)} (0 = kenar, 1 = tam orta). Puana dahil değildir.`}>
        {merkezlikCumlesi(o.merkezlik)}
      </p>
      {aylar.length > 0 && (
        <p className="urun-aylar">Ekim: {aylar.join(", ")}</p>
      )}
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

function Gruplu({ liste }: { liste: Oneri[] }) {
  const gruplar = useMemo(() => {
    const g = new Map<string, Oneri[]>();
    for (const x of liste) {
      const l = g.get(x.grup) ?? [];
      l.push(x);
      g.set(x.grup, l);
    }
    return [...g.entries()];
  }, [liste]);

  return (
    <>
      {gruplar.map(([grup, l]) => (
        <div key={grup} className="grup">
          <h3>{grup}</h3>
          <ul className="urunler">
            {l.map((x) => (
              <UrunKarti key={x.urun} o={x} />
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}

function Bolum({
  baslik,
  aciklama,
  liste,
  baslangicta_acik,
}: {
  baslik: string;
  aciklama: string;
  liste: Oneri[];
  baslangicta_acik: boolean;
}) {
  const [acik, setAcik] = useState(baslangicta_acik);
  // Bos bolum hic cizilmez. Bos bir baslik "burada hicbir sey yetismez"
  // izlenimi verirdi; oysa dogrusu "bu urunler baska bolumde".
  if (liste.length === 0) return null;
  return (
    <section className="oneri-bolum">
      <button className="bolum-bas" onClick={() => setAcik(!acik)} aria-expanded={acik}>
        <span className="bolum-ad">{baslik}</span>
        <span className="bolum-sayi">{liste.length}</span>
        <span className="bolum-ok">{acik ? "−" : "+"}</span>
      </button>
      <p className="bolum-alt">{aciklama}</p>
      {acik && <Gruplu liste={liste} />}
    </section>
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
  const { simdi, sonra, cokYillik } = useMemo(() => {
    const simdi: Oneri[] = [];
    const sonra: Oneri[] = [];
    const cokYillik: Oneri[] = [];
    for (const x of o.oneriler) {
      if (x.cok_yillik) cokYillik.push(x);
      else if (ekimAylari(x).includes(o.su_anki_ay)) simdi.push(x);
      else sonra.push(x);
    }
    return { simdi, sonra, cokYillik };
  }, [o.oneriler, o.su_anki_ay]);

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

      {o.oneriler.length === 0 ? (
        <p className="bekleyen">Bu koşullarda öne çıkan ürün bulunamadı.</p>
      ) : (
        <>
          <Bolum
            baslik={`Şimdi ekilebilir · ${o.su_anki_ay}`}
            aciklama={`${o.su_anki_ay} ayında ekilirse ürünün gelişme dönemi sıcaklık bakımından uygun geçer.`}
            liste={simdi}
            baslangicta_acik={true}
          />
          <Bolum
            baslik="Mevsiminde ekilebilir"
            aciklama={`Bu ürünler burada yetişir ama ${o.su_anki_ay} ayı doğru zaman değil. Her ürünün altında uygun ekim ayları yazıyor.`}
            liste={sonra}
            baslangicta_acik={false}
          />
          <Bolum
            baslik="Çok yıllık · fidan"
            aciklama="Ağaç, asma ve çok yıllık türler. Bunlar ekilmez, fidan dikilir; dikim zamanı EcoCrop'ta bulunmadığı için ay verilmiyor."
            liste={cokYillik}
            baslangicta_acik={false}
          />
          {/* Bu uyari kaldirilmamalidir. Model bugdayi Bursa'da Temmuz ekimi
              icin 98 puanla uygun buluyor; uc aylik pencere gercekten yeterince
              sicak ama Bursa bugdayi Ekim'de ekilir. Fark EcoCrop'ta
              vernalizasyon ve gun uzunlugu alanlarinin bulunmamasindan
              geliyor. Sinirlamayi gizlemek, ciftciye yanlis takvim vermek
              olurdu. */}
          <p className="alt">
            Ekim ayları yalnızca sıcaklık uygunluğundan hesaplanır. Bu bir ekim
            takvimi değildir: soğuklama ihtiyacı, gün uzunluğu, hastalık baskısı
            ve yerel çeşit farkları bu veride yoktur. Yerel tarım müdürlüğünün
            takvimiyle birlikte değerlendirin.
          </p>
        </>
      )}
    </div>
  );
}
