"""favicon.svg'den PWA ikonlarini (PNG) uretir.

NEDEN BU SCRIPT VAR: PWA kurulumu icin PNG sart. iOS Safari apple-touch-icon
olarak SVG kabul etmiyor, Android da manifest ikonunu PNG isterken en tutarli
davraniyor. Ortamda SVG rasterlayici yok (cairosvg kurulu degil, node
tarafinda sharp/resvg yok), o yuzden ikonu ELLE ikinci kez cizmek yerine
favicon.svg'nin kendi yol verisi okunup PIL ile taraniyor. Boylece marka tek
dosyada kaliyor: favicon.svg degisince bu script yeniden calistirilir.

Desteklenen SVG alt kumesi BILEREK dar: <rect rx>, "M/C/V/Z" iceren <path>
ve duz cizgi stroke. Genel amacli bir SVG motoru degil, sadece bu ikonu
cizecek kadari. Ikon karmasiklasirsa gercek bir rasterlayici kurulmali.

Kullanim:  py -m scripts.ikon_uret
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw

KOK = Path(__file__).resolve().parent.parent
SVG = KOK / "web" / "public" / "favicon.svg"
HEDEF = KOK / "web" / "public"

# Kenar yumusatma: hedef boyutun 4 katinda cizip kucultuyoruz. PIL'in poligon
# cizimi antialias yapmaz, tek care buyuk cizip LANCZOS ile indirmek.
KAT = 4
GORUNUM = 64.0  # favicon.svg viewBox boyu


def _bezier(p0, p1, p2, p3, adim=48):
    """Kubik bezier'i noktalara acar. PIL bezier bilmiyor, poligon istiyor."""
    cikti = []
    for i in range(adim + 1):
        t = i / adim
        u = 1 - t
        cikti.append((
            u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
            u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
        ))
    return cikti


def _yolu_coz(d: str) -> list[tuple[float, float]]:
    """M/C/V/Z komutlarini nokta dizisine cevirir (mutlak koordinat)."""
    parcalar = re.findall(r"([MCVZmcvz])([^MCVZmcvz]*)", d)
    noktalar: list[tuple[float, float]] = []
    su = (0.0, 0.0)
    for komut, ham in parcalar:
        sayilar = [float(s) for s in re.findall(r"-?\d+\.?\d*", ham)]
        if komut in "Mm":
            su = (sayilar[0], sayilar[1])
            noktalar.append(su)
        elif komut in "Cc":
            for i in range(0, len(sayilar), 6):
                p1 = (sayilar[i], sayilar[i + 1])
                p2 = (sayilar[i + 2], sayilar[i + 3])
                p3 = (sayilar[i + 4], sayilar[i + 5])
                noktalar.extend(_bezier(su, p1, p2, p3)[1:])
                su = p3
        elif komut in "Vv":
            su = (su[0], sayilar[0])
            noktalar.append(su)
    return noktalar


def _svg_oku() -> dict:
    metin = SVG.read_text(encoding="utf-8")
    rect = re.search(r"<rect[^>]*rx=\"([\d.]+)\"[^>]*fill=\"(#[0-9a-fA-F]{6})\"", metin)
    yollar = []
    for m in re.finditer(r"<path([^>]*)/>", metin):
        oz = m.group(1)
        d = re.search(r'd="([^"]+)"', oz)
        dolgu = re.search(r'fill="(#[0-9a-fA-F]{6})"', oz)
        cizgi = re.search(r'stroke="(#[0-9a-fA-F]{6})"', oz)
        kalinlik = re.search(r'stroke-width="([\d.]+)"', oz)
        yollar.append({
            "d": d.group(1),
            "dolgu": dolgu.group(1) if dolgu else None,
            "cizgi": cizgi.group(1) if cizgi else None,
            "kalinlik": float(kalinlik.group(1)) if kalinlik else 0.0,
        })
    return {"rx": float(rect.group(1)), "zemin": rect.group(2), "yollar": yollar}


def _ciz(boy: int, ic_oran: float, sema: dict) -> Image.Image:
    """ic_oran<1 => maskable: Android ikonu kirpar, guvenli alan icteki %80."""
    b = boy * KAT
    img = Image.new("RGBA", (b, b), (0, 0, 0, 0))
    ciz = ImageDraw.Draw(img)

    ic = b * ic_oran
    kayma = (b - ic) / 2
    olcek = ic / GORUNUM

    def d(nokta):
        return (kayma + nokta[0] * olcek, kayma + nokta[1] * olcek)

    if ic_oran < 1:
        # Kirpilan kenarlarda bosluk kalmasin diye tam kare zemin.
        ciz.rectangle([0, 0, b, b], fill=sema["zemin"])
    else:
        ciz.rounded_rectangle([kayma, kayma, kayma + ic, kayma + ic],
                              radius=sema["rx"] * olcek, fill=sema["zemin"])

    for y in sema["yollar"]:
        noktalar = [d(n) for n in _yolu_coz(y["d"])]
        if y["dolgu"]:
            ciz.polygon(noktalar, fill=y["dolgu"])
        elif y["cizgi"]:
            ciz.line(noktalar, fill=y["cizgi"], width=int(y["kalinlik"] * olcek), joint="curve")
            # linecap="round" karsiligi: PIL'de yok, uc noktalara daire konuyor.
            r = y["kalinlik"] * olcek / 2
            for n in (noktalar[0], noktalar[-1]):
                ciz.ellipse([n[0] - r, n[1] - r, n[0] + r, n[1] + r], fill=y["cizgi"])

    return img.resize((boy, boy), Image.LANCZOS)


def main() -> None:
    sema = _svg_oku()
    uretilecek = [
        ("icon-192.png", 192, 1.0),
        ("icon-512.png", 512, 1.0),
        ("icon-maskable-512.png", 512, 0.78),
        ("apple-touch-icon.png", 180, 1.0),
    ]
    for ad, boy, oran in uretilecek:
        yol = HEDEF / ad
        _ciz(boy, oran, sema).save(yol)
        print(f"  {ad:26} {boy}x{boy}  {yol.stat().st_size / 1024:.1f} KB")
    print(f"\n{len(uretilecek)} ikon uretildi -> {HEDEF}")


if __name__ == "__main__":
    main()
