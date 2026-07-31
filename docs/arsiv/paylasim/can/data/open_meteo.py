"""Open-Meteo istemcisi: koordinattan iklim ozeti (ucretsiz, anahtarsiz).

Urun onerisi modeli sicaklik/nem/yagis ister. Bunlari son 1 yillik
gecmis veriden (archive API) ozetleyerek temsili deger uretiriz:
- temperature: yillik ortalama sicaklik (C)
- humidity: yillik ortalama bagil nem (%)
- rainfall: yillik toplam yagis (mm)
"""
from __future__ import annotations

from datetime import date, timedelta

import requests

from core.schemas import ClimateData

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_climate(lat: float, lon: float, timeout: int = 20) -> ClimateData:
    """Verilen koordinat icin son ~1 yilin iklim ozetini dondurur."""
    end = date.today() - timedelta(days=7)   # arsiv verisi ~1 hafta gecikmeli
    start = end - timedelta(days=365)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,precipitation_sum",
        "hourly": "relative_humidity_2m",
        "timezone": "auto",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    daily = data.get("daily", {})
    temps = [t for t in daily.get("temperature_2m_mean", []) if t is not None]
    rains = [r for r in daily.get("precipitation_sum", []) if r is not None]
    hums = [h for h in data.get("hourly", {}).get("relative_humidity_2m", []) if h is not None]

    return ClimateData(
        temperature=round(sum(temps) / len(temps), 1) if temps else None,
        humidity=round(sum(hums) / len(hums), 1) if hums else None,
        rainfall=round(sum(rains), 1) if rains else None,
    )
