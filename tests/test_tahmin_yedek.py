"""Kota dolunca gomulu anlik kaydin devreye girmesi.

NEDEN BU DOSYA VAR: canli surumde Open-Meteo bir kez "Daily API request limit
exceeded" dedi ve sulama, iklim riski, karbon, sezon gunlugu kartlarinin dordu
birden bos kaldi. Yedek zinciri bunun icin yazildi ve elle bir kez denendi;
elle denenen sey, bir dahaki refactor'da sessizce bozulur.

Testler AG'A CIKMAZ: requests.get yerine sahte cevap konuluyor. Bir agin
gercekten 429 dondugu ana bagli test, kota doluyken gecmez.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from data import open_meteo


class _SahteCevap:
    """Open-Meteo'nun 429 cevabi: gerekceyi GOVDESINDE yazar, basligında degil."""

    status_code = 429
    text = '{"error":true,"reason":"Daily API request limit exceeded."}'

    def json(self) -> dict:
        return json.loads(self.text)


@pytest.fixture(autouse=True)
def _temiz_ortam(tmp_path, monkeypatch):
    """Her test kendi bos yedek klasoru ve bos surec ici onbellegiyle baslar.

    Surec ici onbellek temizlenmezse yedek yolu HIC denenmez (kod once bayat
    kayda bakiyor); o zaman test, olculmek istenen seyi olcmemis olur.
    """
    monkeypatch.setattr(open_meteo, "TAHMIN_YEDEK", tmp_path / "tahmin_yedek")
    open_meteo._TAHMIN_ONBELLEK.clear()
    yield
    open_meteo._TAHMIN_ONBELLEK.clear()


def _pencere() -> dict:
    return {
        "time": ["2026-08-01", "2026-08-02"],
        "temperature_2m_min": [21.0, 22.0],
        "temperature_2m_max": [33.0, 34.0],
        "precipitation_sum": [0.0, 1.2],
        "et0_fao_evapotranspiration": [5.4, 5.1],
    }


def test_yedek_yaziliyor_ve_tarihi_tasiyor(tmp_path):
    yol = open_meteo.yedek_yaz(36.92, 30.86, _pencere())
    kayit = json.loads(yol.read_text(encoding="utf-8"))
    assert kayit["_tarih"] == date.today().isoformat()
    assert kayit["et0_fao_evapotranspiration"] == [5.4, 5.1]


def test_kota_dolunca_yedek_okunuyor(monkeypatch):
    open_meteo.yedek_yaz(36.92, 30.86, _pencere())
    monkeypatch.setattr(open_meteo.requests, "get", lambda *a, **k: _SahteCevap())

    daily = open_meteo._tahmin_penceresi(36.92, 30.86)

    assert daily["et0_fao_evapotranspiration"] == [5.4, 5.1]
    # Tarihin tasinmasi kartlarin "canli veri" ile "gomulu kayit" ayrimini
    # yapabilmesinin TEK yolu; bu alan dusarse arayuz eski bir tahmini
    # bugunun plani gibi gosterir.
    assert daily["_tarih"] == date.today().isoformat()


def test_yedek_yoksa_hata_yukari_cikiyor(monkeypatch):
    """Yedegi olmayan noktada SESSIZ bir cevap uretilmez.

    Bos sozluk donseydi sulama plani "0 mm/gun" derdi; bu, kartin bos
    kalmasindan daha kotudur.
    """
    monkeypatch.setattr(open_meteo.requests, "get", lambda *a, **k: _SahteCevap())
    with pytest.raises(RuntimeError):
        open_meteo._tahmin_penceresi(10.0, 10.0)


def test_kayit_tarihi_uc_geticinin_hepsinde_donuyor(monkeypatch):
    """Sulama, iklim riski ve gunluk: ucu de ayni pencereden besleniyor."""
    open_meteo.yedek_yaz(36.92, 30.86, _pencere())
    monkeypatch.setattr(open_meteo.requests, "get", lambda *a, **k: _SahteCevap())
    bugun = date.today().isoformat()

    assert open_meteo.get_irrigation_inputs(36.92, 30.86)["kayit_tarihi"] == bugun
    assert open_meteo.get_forecast_series(36.92, 30.86)["kayit_tarihi"] == bugun
    assert open_meteo.get_gunluk_su_serisi(36.92, 30.86)["kayit_tarihi"] == bugun


def test_canli_cevapta_kayit_tarihi_bos(monkeypatch):
    """Canli veri geldiginde arayuzde HICBIR not cikmamali."""

    class _Ok:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"daily": _pencere()}

    monkeypatch.setattr(open_meteo.requests, "get", lambda *a, **k: _Ok())
    assert open_meteo.get_irrigation_inputs(36.92, 30.86)["kayit_tarihi"] is None
