/**
 * Harita: nokta secimi ve parsel sinirlari.
 *
 * Karo kaynagi OpenStreetMap. Anahtar istemez, ucretsizdir ve projenin
 * "sifir maliyet" kuralina uyar. Ucretli bir karo saglayicisi (Mapbox,
 * Google) daha guzel gorunurdu ama uygulamayi para gerektirir hale getirirdi.
 */
import { useEffect } from "react";
import {
  MapContainer,
  Marker,
  Polygon,
  TileLayer,
  Tooltip,
  useMap,
  useMapEvents,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Parsel } from "../api/istemci";

// Leaflet'in varsayilan isaretci gorseli paketleyiciyle gelmez, bu yuzden
// isaretci gorunmez olur. Kendi isaretcimizi ciziyoruz (ek dosya da gerekmez).
const ISARETCI = L.divIcon({
  className: "",
  html: '<div class="isaretci"></div>',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

function Tiklama({ onSec }: { onSec: (lat: number, lon: number) => void }) {
  useMapEvents({
    click: (e) => onSec(+e.latlng.lat.toFixed(5), +e.latlng.lng.toFixed(5)),
  });
  return null;
}

function Ucur({ nokta }: { nokta: { lat: number; lon: number } | null }) {
  const harita = useMap();
  useEffect(() => {
    if (!nokta) return;
    // Rastgele nokta dunyanin obur ucunda olabilir; kullanici nereye
    // gittigini gormeli. Yakinlastirma seviyesi parsel siniri secilecek
    // kadar yakin (14), ama cevreyi de gosterecek kadar genis.
    harita.flyTo([nokta.lat, nokta.lon], Math.max(harita.getZoom(), 14), {
      duration: 1.2,
    });
  }, [nokta, harita]);
  return null;
}

export default function Harita({
  nokta,
  parseller,
  onSec,
}: {
  nokta: { lat: number; lon: number } | null;
  parseller: Parsel[];
  onSec: (lat: number, lon: number) => void;
}) {
  return (
    <MapContainer center={[36.92, 30.83]} zoom={5} className="harita">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> katkicilari'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        maxZoom={19}
      />
      <Tiklama onSec={onSec} />
      <Ucur nokta={nokta} />
      {nokta && <Marker position={[nokta.lat, nokta.lon]} icon={ISARETCI} />}
      {parseller.map((p) =>
        p.sinir && p.sinir.length > 2 ? (
          <Polygon
            key={p.osm_id}
            positions={p.sinir as [number, number][]}
            pathOptions={{ color: "#2f7a3e", weight: 2, fillOpacity: 0.18 }}
          >
            <Tooltip sticky>
              {p.ad ? `${p.ad} - ` : ""}
              {p.tur_tr}
              {p.alan_dekar ? ` (${p.alan_dekar} dekar)` : ""}
            </Tooltip>
          </Polygon>
        ) : null,
      )}
    </MapContainer>
  );
}
