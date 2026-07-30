"""MEGSIS (TKGM) parsel istemcisi (Sprint 1 - Ozlem).

Amac: ciftci il/ilce/mahalle/ada/parsel girince tarlasini tanimlamak.
MEGSIS parsel geometrisini (GeoJSON poligon) alir; bundan:
  - merkez koordinat (lat/lon)  -> SoilGrids + Open-Meteo sorgusu icin
  - alan (m2)                   -> toplam su/gubre hesabi icin
uretir.

Onemli: TKGM MEGSIS canli servisi resmi erisim/izin gerektirir ve kurumsal
kullanim sartlarina tabidir. Bu yuzden istemci iki katmanli:
  1) parcel_from_geojson(...)  -> geometriden Parcel uretir (tam testli cekirdek,
     dis bagimlilik yok; elde/servisten gelen GeoJSON'a uygulanir).
  2) get_parcel(...)           -> MEGSIS servisine istek atar; erisim yoksa
     MegsisError firlatir, cagiran taraf koordinat girisine duser.
"""
from __future__ import annotations

import math

import requests

from core.config import settings
from core.schemas import Parcel


class MegsisError(RuntimeError):
    """MEGSIS servisine ulasilamadi ya da parsel bulunamadi."""


def _extract_ring(geojson: dict) -> list[list[float]]:
    """GeoJSON'dan ilk poligonun dis halkasini [ [lon,lat], ... ] olarak ceker."""
    geom = geojson
    if geojson.get("type") == "FeatureCollection":
        geom = geojson["features"][0]["geometry"]
    elif geojson.get("type") == "Feature":
        geom = geojson["geometry"]

    coords = geom["coordinates"]
    if geom["type"] == "Polygon":
        return coords[0]
    if geom["type"] == "MultiPolygon":
        return coords[0][0]
    raise MegsisError(f"Desteklenmeyen geometri tipi: {geom['type']}")


def _centroid_and_area(ring: list[list[float]]) -> tuple[float, float, float]:
    """Lon/lat halkasindan (merkez_lat, merkez_lon, alan_m2) hesaplar.

    Halka merkezinde ekdikdortgen (equirectangular) izdusumuyle metreye cevirip
    shoelace uygular. Parsel olceginde (< birkac km) hata ihmal edilebilir.
    """
    lat0 = sum(p[1] for p in ring) / len(ring)
    lon0 = sum(p[0] for p in ring) / len(ring)
    m_per_deg_lat = 110_540.0
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(lat0))

    xy = [((p[0] - lon0) * m_per_deg_lon, (p[1] - lat0) * m_per_deg_lat) for p in ring]

    # Shoelace: alan + poligon merkezi (projekte koordinatta)
    area2 = 0.0
    cx = 0.0
    cy = 0.0
    for (x1, y1), (x2, y2) in zip(xy, xy[1:] + xy[:1]):
        cross = x1 * y2 - x2 * y1
        area2 += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross

    area = abs(area2) / 2.0
    if area2 != 0:
        cx /= 3 * area2
        cy /= 3 * area2

    center_lon = lon0 + cx / m_per_deg_lon
    center_lat = lat0 + cy / m_per_deg_lat
    return center_lat, center_lon, area


def parcel_from_geojson(
    geojson: dict,
    il: str,
    ilce: str,
    mahalle: str,
    ada: str,
    parsel: str,
) -> Parcel:
    """GeoJSON parsel geometrisinden Parcel (merkez + alan) uretir."""
    ring = _extract_ring(geojson)
    lat, lon, area = _centroid_and_area(ring)
    return Parcel(
        il=il,
        ilce=ilce,
        mahalle=mahalle,
        ada=ada,
        parsel=parsel,
        lat=round(lat, 6),
        lon=round(lon, 6),
        alan_m2=round(area, 1),
    )


def get_parcel(
    il: str,
    ilce: str,
    mahalle: str,
    ada: str,
    parsel: str,
    *,
    mahalle_id: str | int,
    timeout: int = 30,
) -> Parcel:
    """MEGSIS'ten parsel geometrisini cekip Parcel dondurur.

    mahalle_id: MEGSIS mahalle kodu (idari yapi sorgusundan gelir).
    Servise ulasilamazsa/parsel yoksa MegsisError firlatir.
    """
    url = f"{settings.megsis_url}/api/parsel/{mahalle_id}/{ada}/{parsel}"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        geojson = resp.json()
    except requests.RequestException as exc:
        raise MegsisError(
            "MEGSIS servisine ulasilamadi (TKGM resmi erisim gerektirir). "
            "Koordinat girisiyle devam edin."
        ) from exc

    if not geojson or "type" not in geojson:
        raise MegsisError("Parsel bulunamadi ya da beklenmeyen yanit.")

    return parcel_from_geojson(geojson, il, ilce, mahalle, ada, parsel)
