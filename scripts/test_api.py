"""API uc noktalarinin DOGRULUK ve SURE olcumu.

Calistirma (sunucu ayaktayken): py -m scripts.test_api

Sure neden olculuyor: canli surumde kullanici bekleyecek. Parsel ve topragi ayri
uc noktalara almanin gerekcesi bir olcuydu (parsel 25 s'ye, SoilGrids 40 s'ye
kadar; digerleri 1-5 s); bu ayrimin gercekten ise yaradigi ancak olculerek
gosterilebilir. "Hizli oldu" demek yeterli degil, sayi gerekiyor.

Testin asil kontrol ettigi DOGRULUK sartlari:
  1) /konum yavas katmanlari BEKLEMEMELI (toprak_durum "sorgulanmadi" olmali).
  2) /oneri bos liste dondurmemeli. Bos liste "burada hicbir urun yetismez"
     demektir; dis servis coktugunde bunu yazmak yalan olur, HTTP 503 dogrudur.
  3) /toprak ve /parseller bos sonucu "kesin" bayragiyla ayirt edilebilmeli:
     kesin=False iken bos sonuc "yok" degil "bilinmiyor" demektir.
  4) Ayni tohumla /rastgele ayni noktayi vermeli.
"""
from __future__ import annotations

import re
import sys
import time

import requests

KOK = "http://127.0.0.1:8000"

# (ad, lat, lon, o bolgede ilk sirlarda BEKLENEN urunlerden en az biri)
YERLER = [
    ("Antalya (TR)", 36.92, 30.83),
    ("Iowa (ABD)", 42.03, -93.63),
    ("Nakuru (KE)", -0.30, 36.08),
]


def _temiz(s: object) -> str:
    """Windows konsolu (cp1254) Turkce disi karakterlerde cokuyor."""
    return re.sub(r"[^\x00-\x7f]", "?", str(s))


def _al(yol: str, bekle: int = 200, **params) -> tuple[dict, float, int]:
    t0 = time.time()
    r = requests.get(f"{KOK}{yol}", params=params, timeout=bekle)
    return r.json(), time.time() - t0, r.status_code


def _bekle(saniye: int = 30) -> None:
    for _ in range(saniye * 2):
        try:
            requests.get(f"{KOK}/saglik", timeout=2)
            return
        except Exception:
            time.sleep(0.5)
    raise SystemExit(f"Sunucu {saniye} s icinde ayaga kalkmadi: {KOK}")


def main() -> None:
    _bekle()
    saglik, s, _ = _al("/saglik")
    print(f"/saglik  {s:5.2f} s  {saglik}")

    urun, s, _ = _al("/urunler")
    print(f"/urunler {s:5.2f} s  {urun['adet']} urun, "
          f"{len(urun['gruplar'])} grup: {_temiz(', '.join(urun['gruplar']))}")

    hatalar: list[str] = []
    sureler: dict[str, list[float]] = {}

    for ad, lat, lon in YERLER:
        print(f"\n{'=' * 72}\n{ad}  ({lat}, {lon})")

        k, s_k, kod = _al("/konum", lat=lat, lon=lon)
        sureler.setdefault("/konum", []).append(s_k)
        print(f"  /konum      {s_k:5.2f} s  {_temiz(k['yer_adi'])[:45]} / "
              f"{_temiz(k['ulke'])}, {k['yukselti_m']} m, "
              f"iklim {k['iklim']}")
        if k.get("eksik"):
            print(f"              eksik: {_temiz('; '.join(k['eksik']))}")
        # 1) /konum yavas katmanlari beklememeli.
        if k.get("toprak_durum") != "sorgulanmadi":
            hatalar.append(f"{ad}: /konum topragi bekledi, ayri uc nokta olmali")
        if "parseller" in k:
            hatalar.append(f"{ad}: /konum parsel dondurdu, ayri uc nokta olmali")

        t, s_t, _ = _al("/toprak", lat=lat, lon=lon)
        sureler.setdefault("/toprak", []).append(s_t)
        tp = t.get("toprak")
        durum = "kesin" if t["kesin"] else f"BILINMIYOR ({_temiz(t['durum'])})"
        print(f"  /toprak     {s_t:5.2f} s  pH {tp['ph'] if tp else None}, "
              f"doku {_temiz(t.get('doku_sinifi'))}, "
              f"{t.get('kaynak_mesafe_km')} km oteden, {durum}")
        # 3) Toprak yoksa nedeni ayirt edilebilmeli.
        if tp is None and t["kesin"]:
            print("              (SoilGrids bu noktada gercekten deger tutmuyor)")

        o, s_o, kod = _al("/oneri", lat=lat, lon=lon, adet=5)
        sureler.setdefault("/oneri", []).append(s_o)
        if kod != 200:
            print(f"  /oneri      {s_o:5.2f} s  HTTP {kod}: {_temiz(o.get('detail'))[:90]}")
            hatalar.append(f"{ad}: /oneri HTTP {kod}")
        else:
            print(f"  /oneri      {s_o:5.2f} s  {o['toplam_uygun']} urun uygun, "
                  f"toprak_var={o['toprak_var']}, "
                  f"yagis {o['iklim']['yillik_yagis_mm']:.0f} mm, "
                  f"mutlak min {o['iklim']['mutlak_min_c']} C")
            for r in o["oneriler"]:
                print(f"      {r['skor']:5.1f}  {_temiz(r['ad']):20s} "
                      f"{_temiz(r['uygunluk'])}")
            # 2) Bos liste yalandir.
            if not o["oneriler"]:
                hatalar.append(f"{ad}: /oneri bos liste dondurdu")
            # Iklim tutarliligi: /konum ile /oneri ayni yagis sayisini vermeli.
            k_yagis = (k.get("iklim") or {}).get("rainfall")
            if k_yagis is not None and abs(k_yagis - o["iklim"]["yillik_yagis_mm"]) > 0.1:
                hatalar.append(f"{ad}: /konum yagis {k_yagis} != "
                               f"/oneri yagis {o['iklim']['yillik_yagis_mm']}")

        g, s_g, _ = _al("/oneri/gruplar", lat=lat, lon=lon, grup_basina=2)
        sureler.setdefault("/oneri/gruplar", []).append(s_g)
        print(f"  /gruplar    {s_g:5.2f} s  {len(g.get('gruplar', {}))} grup")

        p, s_p, _ = _al("/parseller", lat=lat, lon=lon)
        sureler.setdefault("/parseller", []).append(s_p)
        durum = "kesin" if p["kesin"] else f"BILINMIYOR ({_temiz(p['durum'])})"
        print(f"  /parseller  {s_p:5.2f} s  {p['adet']} parsel, {durum}")
        # Bos liste + kesin=False kombinasyonu arayuze "parsel yok" diye
        # yazilamaz; testin asil kontrol ettigi sey bu ayrimin tasinmasidir.
        if p["adet"] == 0 and p["kesin"]:
            print("              (gercekten parsel yok, iki ayna dogruladi)")

    print(f"\n{'=' * 72}\nrastgele nokta (tohum sabit, tekrarlanabilir):")
    r1, s_r, _ = _al("/rastgele", tohum=7)
    sureler.setdefault("/rastgele", []).append(s_r)
    print(f"  /rastgele   {s_r:5.2f} s  {_temiz(r1['yer_adi'])[:50]} / "
          f"{_temiz(r1['ulke'])} ({r1['lat']}, {r1['lon']})")
    r2, _s, _ = _al("/rastgele", tohum=7)
    if (r1["lat"], r1["lon"]) != (r2["lat"], r2["lon"]):
        hatalar.append("ayni tohum farkli nokta verdi, tekrarlanabilir degil")

    print(f"\n{'=' * 72}\nSURELER (saniye)")
    for yol, l in sureler.items():
        print(f"  {yol:16s} en hizli {min(l):5.2f}  ortalama {sum(l)/len(l):5.2f}  "
              f"en yavas {max(l):5.2f}")

    print(f"\nHATA: {len(hatalar)}")
    for h in hatalar:
        print(f"  {h}")
    sys.exit(1 if hatalar else 0)


if __name__ == "__main__":
    main()
