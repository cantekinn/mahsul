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

/* Yilin aylari, sunucudaki AYLAR dizisiyle AYNI yazimda. Serit bu diziye gore
   cizilir, gelen listeye gore degil: gelen liste "Mart, Nisan, Ağustos" gibi
   deliklidir ve deligin kendisi bilgidir (arpa iki ayri pencerede ekilir). */
const YILIN_AYLARI = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

/**
 * Ekim penceresi seridi.
 *
 * aria-hidden: altindaki "Ekim: Mart, Nisan..." satiri ayni bilgiyi TAM
 * yaziyor. Serit onun yerine gecmez, YANINDA durur; isi pencerenin BICIMINI
 * (kac ay, bitisik mi, ikiye mi bolunmus) tek bakista gostermek. Ekran
 * okuyucuya ayni listeyi iki kez okutmanin faydasi yok.
 */
function AySeridi({ aylar, suAnkiAy }: { aylar: string[]; suAnkiAy: string }) {
  const kume = new Set(aylar);
  return (
    <div className="ay-serit" aria-hidden="true">
      {YILIN_AYLARI.map((ay) => (
        <span
          key={ay}
          className={`ay-hucre${kume.has(ay) ? " uygun" : ""}${ay === suAnkiAy ? " simdi" : ""}`}
          title={ay}
        >
          {ay.slice(0, 3)}
        </span>
      ))}
    </div>
  );
}

/**
 * Puanin faktor kirilimi.
 *
 * Sunucu her faktorun uyumunu (0-1) zaten yaniti icinde donuyordu ama arayuz
 * bunu hic gostermiyordu: ciftci 84 puani goruyor, NEDEN 84 oldugunu
 * goremiyordu. Puan agirlikli GEOMETRIK ortalama oldugu icin en zayif faktor
 * sonucu orantisiz cekiyor; kirilimi gostermek "neyi duzeltirsem puan artar"
 * sorusunun cevabini veriyor (ornek: pH zayifsa kirecleme, yagis zayifsa
 * sulama).
 *
 * RENK OLCEGI SKORDAN ODUNC ALINDI, yeni bir olcek uretilmedi: uyum da skor da
 * ayni ekseni olcuyor ("ne kadar iyi"), yonu de ayni. Risk olcegi ayri
 * duruyor cunku onun yonu ters.
 *
 * AGIRLIKLAR GOSTERILMIYOR: sunucu yanitinda yoklar. Buraya elle 1.0/0.9/0.6/
 * 0.4 yazmak, sunucudaki tablo degisince sessizce yalan soyleyen bir arayuz
 * birakirdi. Bu yuzden "en dusuk uyum" deniyor, "siralamayi belirleyen faktor"
 * denmiyor: ikincisi agirligi bilmeden soylenemez.
 */
type Faktor = { faktor: string; deger: number | string; birim: string; uyum: number };

function SkorKirilimi({ o }: { o: Oneri }) {
  // Sunucu bu alani list[dict] olarak yaziyor, dolayisiyla uretilen OpenAPI
  // tipi icerigi bilmiyor. Daraltma TEK YERDE burada yapiliyor; uretilen
  // tipler.ts'i elle duzeltmek semayi yalanlamak olurdu.
  const faktorler = (o.faktorler ?? []) as unknown as Faktor[];
  if (faktorler.length === 0) return null;
  const enDusuk = Math.min(...faktorler.map((f) => f.uyum));

  return (
    <div className="kirilim">
      {faktorler.map((f) => {
        const yuzde = Math.round(f.uyum * 100);
        // Esitlikte hicbiri isaretlenmez: dordu de 1.00 iken birine "en zayif"
        // demek uydurma olur.
        const zayif =
          f.uyum === enDusuk && faktorler.filter((x) => x.uyum === enDusuk).length === 1;
        return (
          <div className="kirilim-satir" key={f.faktor}>
            <div className="kirilim-bas">
              <span className="kirilim-ad">{f.faktor}</span>
              <span className="kirilim-deger">
                {f.deger}
                {f.birim ? ` ${f.birim}` : ""}
                <span className="kirilim-uyum"> · %{yuzde}</span>
              </span>
            </div>
            <div className="kirilim-yol">
              <span
                className={`kirilim-dolu ${skorRengi(yuzde)}`}
                style={{ width: `${yuzde}%` }}
              />
            </div>
            {zayif && yuzde < 95 && (
              <p className="kirilim-not">en düşük uyum bu faktörde</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function UrunKarti({ o, suAnkiAy }: { o: Oneri; suAnkiAy: string }) {
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
        <>
          <AySeridi aylar={aylar} suAnkiAy={suAnkiAy} />
          <p className="urun-aylar">Ekim: {aylar.join(", ")}</p>
        </>
      )}
      {acik && (
        <div className="urun-detay">
          <SkorKirilimi o={o} />
          <p className="bilimsel">{o.bilimsel_ad}</p>
          <p>{o.sezon}</p>
          {o.uygunluk_gaez != null && (
            /* GAEZ 0-100 arasi bir bolgesel uygunluk gostergesi. FAO+IIASA'nin
               iklim, toprak ve su butcesini birlestirdigi bir global gridden
               geliyor. Puanin ana ceperi budur (0.7 agirlik); ciftci ayni
               anda hem birlesik puana hem kaynak sinyaline bakabilsin diye
               ayrica gosteriyoruz. */
            <p className="urun-gaez" title="FAO GAEZ v4 Suitability Index (0-100)">
              FAO GAEZ bölgesel uygunluk: {o.uygunluk_gaez.toFixed(0)}/100
            </p>
          )}
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

function Gruplu({ liste, suAnkiAy }: { liste: Oneri[]; suAnkiAy: string }) {
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
              <UrunKarti key={x.urun} o={x} suAnkiAy={suAnkiAy} />
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
  suAnkiAy,
}: {
  baslik: string;
  aciklama: string;
  liste: Oneri[];
  baslangicta_acik: boolean;
  suAnkiAy: string;
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
      {acik && <Gruplu liste={liste} suAnkiAy={suAnkiAy} />}
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

/**
 * Filtre secenekleri.
 *
 * NEDEN SADECE UC TANE: liste 29 urun ve zaten uc bolume ayrilmis durumda.
 * Buraya her alan icin bir denetim koymak (sicaklik araligi, doku, sezon...)
 * aramayi kolaylastirmaz, kararsizlastirir. Uc soru sordugumuz kadariyla
 * secildi ve ucu de ciftcinin gercekten sordugu sorular:
 *   grup   -> "tahil disinda ne var"
 *   susuz  -> "sulama tesisatim yok, sulamadan ne olur"
 *   asgari -> "vaktimi sadece iyi seceneklere ayirayim"
 * Filtre SIRALAMAYI DEGISTIRMEZ, sadece eler: sira puanindir, kullanicinin
 * secimi puani degistiremez.
 */
type Filtre = { grup: string; susuz: boolean; asgari: number };

const FILTRE_BOS: Filtre = { grup: "", susuz: false, asgari: 0 };

function FiltreCubugu({
  deger,
  degistir,
  gruplar,
  gosterilen,
  toplam,
}: {
  deger: Filtre;
  degistir: (f: Filtre) => void;
  gruplar: string[];
  gosterilen: number;
  toplam: number;
}) {
  const acik = deger.grup !== "" || deger.susuz || deger.asgari > 0;
  return (
    <div className="filtre">
      <select
        className="filtre-secim"
        value={deger.grup}
        onChange={(e) => degistir({ ...deger, grup: e.target.value })}
        aria-label="Ürün grubu"
      >
        <option value="">Tüm gruplar</option>
        {gruplar.map((g) => (
          <option key={g} value={g}>
            {g}
          </option>
        ))}
      </select>

      <select
        className="filtre-secim"
        value={String(deger.asgari)}
        onChange={(e) => degistir({ ...deger, asgari: Number(e.target.value) })}
        aria-label="En düşük puan"
      >
        {/* Esikler kart kenarligi renkleriyle AYNI basamaklar (skorRengi).
            Baska sayilar secilseydi "70 ustu" filtresi sari kenarlikli bir
            urunu de gecirir, kullanici renkle listeyi celiskili bulurdu. */}
        <option value="0">Her puan</option>
        <option value="70">70 ve üstü</option>
        <option value="85">85 ve üstü</option>
      </select>

      <label className="filtre-kutu">
        <input
          type="checkbox"
          checked={deger.susuz}
          onChange={(e) => degistir({ ...deger, susuz: e.target.checked })}
        />
        {/* "Sulama gerektirmeyen" DEGIL "yağışla yetinen": su_acigi_mm sifir
            olmasi yagisin optimum aralığın altına düşmediği anlamına gelir,
            hiç sulanmayacağı anlamına değil. */}
        <span>Yağışla yetinenler</span>
      </label>

      {acik && (
        <>
          <span className="filtre-sayi">
            {toplam} üründen {gosterilen} tanesi
          </span>
          <button className="dugme yalin" onClick={() => degistir(FILTRE_BOS)}>
            Filtreyi kaldır
          </button>
        </>
      )}
    </div>
  );
}

function Icerik({ o }: { o: OneriKumesi }) {
  const [filtre, setFiltre] = useState<Filtre>(FILTRE_BOS);

  const gruplar = useMemo(
    () => [...new Set(o.oneriler.map((x) => x.grup))].filter(Boolean).sort(),
    [o.oneriler],
  );

  const suzulmus = useMemo(
    () =>
      o.oneriler.filter(
        (x) =>
          (filtre.grup === "" || x.grup === filtre.grup) &&
          (!filtre.susuz || x.su_acigi_mm === 0) &&
          x.skor >= filtre.asgari,
      ),
    [o.oneriler, filtre],
  );

  const { simdi, sonra, cokYillik } = useMemo(() => {
    const simdi: Oneri[] = [];
    const sonra: Oneri[] = [];
    const cokYillik: Oneri[] = [];
    for (const x of suzulmus) {
      if (x.cok_yillik) cokYillik.push(x);
      else if (ekimAylari(x).includes(o.su_anki_ay)) simdi.push(x);
      else sonra.push(x);
    }
    return { simdi, sonra, cokYillik };
  }, [suzulmus, o.su_anki_ay]);

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
          <FiltreCubugu
            deger={filtre}
            degistir={setFiltre}
            gruplar={gruplar}
            gosterilen={suzulmus.length}
            toplam={o.oneriler.length}
          />
          {/* "Filtreye uyan yok" ile "burada urun yetismez" AYRI cumleler.
              Ikisi de bos liste uretir ama biri kullanicinin secimi, digeri
              toprak ve iklimin sonucu. Ayni metni yazmak, filtreyi acik unutan
              kullaniciya yerinin verimsiz oldugunu soylerdi. */}
          {suzulmus.length === 0 && (
            <p className="bekleyen">
              Seçtiğiniz filtreye uyan ürün yok. Ürünler duruyor, filtreyi
              genişletince yeniden görünürler.
            </p>
          )}
          <Bolum
            baslik={`Şimdi ekilebilir · ${o.su_anki_ay}`}
            aciklama={`${o.su_anki_ay} ayında ekilirse ürünün gelişme dönemi sıcaklık bakımından uygun geçer.`}
            liste={simdi}
            baslangicta_acik={true}
            suAnkiAy={o.su_anki_ay}
          />
          <Bolum
            baslik="Mevsiminde ekilebilir"
            aciklama={`Bu ürünler burada yetişir ama ${o.su_anki_ay} ayı doğru zaman değil. Her ürünün altında uygun ekim ayları yazıyor.`}
            liste={sonra}
            baslangicta_acik={false}
            suAnkiAy={o.su_anki_ay}
          />
          <Bolum
            baslik="Çok yıllık · fidan"
            aciklama="Ağaç, asma ve çok yıllık türler. Bunlar ekilmez, fidan dikilir; dikim zamanı EcoCrop'ta bulunmadığı için ay verilmiyor."
            liste={cokYillik}
            baslangicta_acik={false}
            suAnkiAy={o.su_anki_ay}
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
