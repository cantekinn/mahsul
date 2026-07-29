import { Kart, KatmanKabugu, sayi } from "./Durum";
import type { Katman } from "./Durum";
import type { Toprak } from "../api/istemci";

export default function ToprakKarti({ katman }: { katman: Katman<Toprak> }) {
  return (
    <KatmanKabugu
      baslik="Toprak"
      katman={katman}
      bekleyen="Toprak verisi alınıyor (SoilGrids)..."
    >
      {(t) => (
        <Kart
          baslik="Toprak"
          etiket={<span className="rozet">{t.sure_s.toFixed(1)} sn</span>}
        >
          {/* UC DURUM, UC AYRI EKRAN. Bunlari birlestirmek projedeki en
              pahali hataydi:
                kesin + veri var  -> deger goster
                kesin + veri yok  -> gercekten yok (deniz, kayalik, kutup)
                kesin degil       -> BILINMIYOR, "yok" DEGIL */}
          {!t.kesin ? (
            <p className="hata">
              Toprak verisi sorgulanamadı ({t.durum}). Bu noktada toprak
              olmadığı anlamına gelmez, bilinmiyor demektir.
            </p>
          ) : !t.toprak ? (
            <p className="bekleyen">
              SoilGrids bu noktada değer tutmuyor. Deniz, kayalık veya kalıcı
              buz olabilir.
            </p>
          ) : (
            <>
              <dl className="satirlar">
                <div>
                  <dt>pH</dt>
                  <dd>{sayi(t.toprak.ph, "", 1)}</dd>
                </div>
                <div>
                  <dt>Doku sınıfı</dt>
                  <dd>{t.doku_sinifi?.replace(/_/g, " ") ?? "bilinmiyor"}</dd>
                </div>
                <div>
                  <dt>Kil / Kum / Silt</dt>
                  <dd>
                    {sayi(t.toprak.clay, "", 0)} / {sayi(t.toprak.sand, "", 0)} /{" "}
                    {sayi(t.toprak.silt, " %", 0)}
                  </dd>
                </div>
                <div>
                  <dt>Organik karbon</dt>
                  <dd>{sayi(t.toprak.organic_carbon, " g/kg", 1)}</dd>
                </div>
                <div>
                  <dt>Azot</dt>
                  <dd>{sayi(t.toprak.nitrogen, " g/kg", 2)}</dd>
                </div>
              </dl>
              {t.kaynak_mesafe_km !== null &&
                t.kaynak_mesafe_km !== undefined &&
                t.kaynak_mesafe_km > 0 && (
                  /* Deger baska bir pikselden geldiyse SOYLENIR. Sessizce
                     komsunun toprağını bu noktanınmış gibi göstermek
                     yanıltıcı olurdu. Şehir merkezlerinde SoilGrids piksel
                     bırakmadığı için bu sık görülür. */
                  <p className="uyari">
                    Bu değerler noktanın kendisinden değil, {t.kaynak_mesafe_km}{" "}
                    km ötedeki en yakın ölçümlü noktadan alındı.
                  </p>
                )}
            </>
          )}
        </Kart>
      )}
    </KatmanKabugu>
  );
}
