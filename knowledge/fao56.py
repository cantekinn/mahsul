"""FAO-56 sulama fizigi (Sprint 2).

Bu modul MAKINE OGRENMESI DEGIL, saf fizik/agronomi denklemleridir.
Referans: Allen et al. (1998), FAO Irrigation and Drainage Paper 56.

Ana zincir:
    ET0  (referans terleme, Penman-Monteith)  [mm/gun]
    ETc  = ET0 * Kc   (urune ozel bitki su tuketimi)
    net_sulama = ETc - etkili_yagis

Tum fonksiyonlar bagimsiz ve test edilebilir; dis servise ihtiyac yoktur.
ET0 hesabinin girdileri (radyasyon/ruzgar) yoksa Open-Meteo dogrudan
FAO-56 ET0 (et0_fao_evapotranspiration) saglar; bu modul o degeri de kullanabilir.
"""
from __future__ import annotations

import math

# Guclu sabitler (FAO-56)
_SOLAR_CONSTANT = 0.0820          # Gsc, MJ m^-2 dk^-1
_STEFAN_BOLTZMANN = 4.903e-9      # sigma, MJ K^-4 m^-2 gun^-1
_ALBEDO = 0.23                    # referans cim yansimasi


def saturation_vapor_pressure(t_c: float) -> float:
    """Doygun buhar basinci es(T) [kPa]. FAO-56 Eq.11."""
    return 0.6108 * math.exp(17.27 * t_c / (t_c + 237.3))


def slope_svp(t_c: float) -> float:
    """Doygun buhar basinci egrisinin egimi Delta [kPa/C]. FAO-56 Eq.13."""
    es = saturation_vapor_pressure(t_c)
    return 4098 * es / (t_c + 237.3) ** 2


def atmospheric_pressure(elevation_m: float) -> float:
    """Atmosfer basinci P [kPa]. FAO-56 Eq.7."""
    return 101.3 * ((293 - 0.0065 * elevation_m) / 293) ** 5.26


def psychrometric_constant(elevation_m: float) -> float:
    """Psikrometrik sabit gamma [kPa/C]. FAO-56 Eq.8."""
    return 0.000665 * atmospheric_pressure(elevation_m)


def extraterrestrial_radiation(latitude_deg: float, day_of_year: int) -> float:
    """Atmosfer disi radyasyon Ra [MJ m^-2 gun^-1]. FAO-56 Eq.21.

    Yalnizca enlem ve gunun sirasindan (astronomi) hesaplanir.
    """
    phi = math.radians(latitude_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * day_of_year / 365)          # Eq.23
    delta = 0.409 * math.sin(2 * math.pi * day_of_year / 365 - 1.39)    # Eq.24
    x = -math.tan(phi) * math.tan(delta)
    x = max(-1.0, min(1.0, x))                                          # kutup guvenligi
    omega_s = math.acos(x)                                             # Eq.25
    ra = (24 * 60 / math.pi) * _SOLAR_CONSTANT * dr * (
        omega_s * math.sin(phi) * math.sin(delta)
        + math.cos(phi) * math.cos(delta) * math.sin(omega_s)
    )
    return ra


def clear_sky_radiation(ra: float, elevation_m: float) -> float:
    """Acik gokyuzu radyasyonu Rso [MJ m^-2 gun^-1]. FAO-56 Eq.37."""
    return (0.75 + 2e-5 * elevation_m) * ra


def net_radiation(
    rs: float, ra: float, t_min: float, t_max: float, ea: float, elevation_m: float
) -> float:
    """Net radyasyon Rn [MJ m^-2 gun^-1]. FAO-56 Eq.38-40.

    rs: gelen kisa dalga radyasyon (olculen/tahmin, MJ m^-2 gun^-1)
    ea: gercek buhar basinci [kPa]
    """
    rns = (1 - _ALBEDO) * rs                                            # net kisa dalga
    rso = clear_sky_radiation(ra, elevation_m)
    tmax_k = t_max + 273.16
    tmin_k = t_min + 273.16
    cloud = 1.35 * min(rs / rso, 1.0) - 0.35 if rso > 0 else 0.05
    rnl = (
        _STEFAN_BOLTZMANN
        * ((tmax_k ** 4 + tmin_k ** 4) / 2)
        * (0.34 - 0.14 * math.sqrt(max(ea, 0)))
        * cloud
    )                                                                  # net uzun dalga
    return rns - rnl


def penman_monteith_et0(
    t_min: float,
    t_max: float,
    rh_mean: float,
    wind_2m: float,
    rs: float,
    latitude_deg: float,
    elevation_m: float,
    day_of_year: int,
) -> float:
    """Referans terleme ET0 [mm/gun]. FAO-56 Eq.6 (Penman-Monteith).

    Girdiler:
      t_min/t_max  : gunluk min/maks hava sicakligi [C]
      rh_mean      : ortalama bagil nem [%]
      wind_2m      : 2 m yukseklikte ruzgar hizi [m/s]
      rs           : gelen gunes radyasyonu [MJ m^-2 gun^-1]
      latitude_deg : enlem (kuzey +)
      elevation_m  : rakim [m]
      day_of_year  : 1..365
    """
    t_mean = (t_min + t_max) / 2
    delta = slope_svp(t_mean)
    gamma = psychrometric_constant(elevation_m)

    es = (saturation_vapor_pressure(t_max) + saturation_vapor_pressure(t_min)) / 2
    ea = es * rh_mean / 100.0

    ra = extraterrestrial_radiation(latitude_deg, day_of_year)
    rn = net_radiation(rs, ra, t_min, t_max, ea, elevation_m)
    g = 0.0  # gunluk toprak isi akisi ~ 0

    num = 0.408 * delta * (rn - g) + gamma * (900 / (t_mean + 273)) * wind_2m * (es - ea)
    den = delta + gamma * (1 + 0.34 * wind_2m)
    return max(0.0, num / den)


def effective_rainfall(rainfall_mm: float) -> float:
    """Etkili yagis [mm] (USDA-SCS aylik yontemi, FAO-56).

    Yagisin bitki koku tarafindan kullanilabilen kismi; yuzey akisi ve
    derin sizma cikarilir. rainfall_mm: aylik toplam yagis.
    """
    p = max(0.0, rainfall_mm)
    if p <= 250:
        return p * (125 - 0.2 * p) / 125
    return 125 + 0.1 * p


# Kisa donem (haftalik) tahmin icin etkili yagis orani. USDA-SCS aylik yontemi
# haftalik pencereye uygun degil (aya olceklemek yagisli haftayi asiri buyutur);
# gunluk sulama plani icin ortalama gunluk yagisin ~%80'i etkili kabul edilir.
_RAIN_EFFECTIVE_FRAC = 0.80


def effective_rainfall_daily(rainfall_mm_daily: float) -> float:
    """Kisa donem tahminden gunluk etkili yagis [mm/gun]."""
    return _RAIN_EFFECTIVE_FRAC * max(0.0, rainfall_mm_daily)


# FAO-56 tek bitki katsayisi Kc (ini / mid / end asamalari)
KC_TABLE: dict[str, dict[str, float]] = {
    "domates":   {"ini": 0.60, "mid": 1.15, "end": 0.80},
    "biber":     {"ini": 0.60, "mid": 1.05, "end": 0.90},
    "patates":   {"ini": 0.50, "mid": 1.15, "end": 0.75},
    "narenciye": {"ini": 0.70, "mid": 0.65, "end": 0.70},  # yer ortusu yok
    "zeytin":    {"ini": 0.65, "mid": 0.70, "end": 0.70},
    "muz":       {"ini": 0.50, "mid": 1.10, "end": 1.00},
}


def crop_coefficient(crop: str, stage: str = "mid") -> float:
    """Urun ve asama icin Kc. Bilinmiyorsa 1.0 (referans cim)."""
    return KC_TABLE.get(crop, {}).get(stage, 1.0)


def crop_water_need(et0: float, crop: str, stage: str = "mid") -> float:
    """Bitki su tuketimi ETc = ET0 * Kc [mm/gun]."""
    return et0 * crop_coefficient(crop, stage)


def net_irrigation(
    et0: float,
    crop: str,
    stage: str = "mid",
    rainfall_mm_daily: float = 0.0,
) -> float:
    """Net sulama ihtiyaci [mm/gun].

    ETc - gunluk_etkili_yagis; negatifse 0 (yagis yeterli).
    rainfall_mm_daily: tahmin doneminin ortalama gunluk yagisi.
    """
    etc = crop_water_need(et0, crop, stage)
    pe_daily = effective_rainfall_daily(rainfall_mm_daily)
    return max(0.0, etc - pe_daily)


def irrigation_plan(
    et0: float,
    crop: str,
    stage: str = "mid",
    rainfall_mm_daily: float = 0.0,
    area_m2: float | None = None,
) -> dict:
    """Bir urun icin gunluk sulama plani.

    Donen alanlar:
      etc_mm_gun     : bitki su tuketimi (mm/gun)
      net_mm_gun     : net sulama (etkili yagis dusulmus, mm/gun)
      litre_gun      : parsel alani verilirse toplam litre/gun (1 mm/m2 = 1 L)
      kc, stage      : kullanilan katsayi ve asama
    rainfall_mm_daily: tahmin doneminin ortalama gunluk yagisi.
    """
    etc = crop_water_need(et0, crop, stage)
    net = net_irrigation(et0, crop, stage, rainfall_mm_daily)
    plan = {
        "urun": crop,
        "stage": stage,
        "kc": round(crop_coefficient(crop, stage), 2),
        "et0_mm_gun": round(et0, 2),
        "etc_mm_gun": round(etc, 2),
        "net_mm_gun": round(net, 2),
    }
    if area_m2:
        plan["litre_gun"] = round(net * area_m2, 1)     # 1 mm x 1 m2 = 1 litre
    return plan
