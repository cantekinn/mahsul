"""Teshis agent'i (Sprint 2): yaprak fotografindan hastalik teshisi + tedavi.

Akis:
  state.image_path (yaprak foto) -> models.disease.predict (EfficientNetV2)
  -> Grad-CAM isi haritasi (aciklanabilirlik) -> teshis etiketi
  -> treatments.yaml eslesmesi (advisor) ile tedavi onerisi.

Model henuz egitilmemisse (torch/agirlik yok) durumu dogrustan bildirir;
sistem cokmeden calismaya devam eder (memory: dürüst degradasyon).
"""
from __future__ import annotations

from agents.advisor_agent import match_disease
from agents.state import AgentState
from models import disease


def diagnosis_node(state: AgentState) -> AgentState:
    image_path = state.get("image_path")
    if not image_path:
        # Foto yok ama kullanici belirti/hastalik adi yazmis olabilir:
        # metinden tedavi eslemesi dene (foto zorunlu degil).
        query = state.get("query", "")
        hit = match_disease(query) if query else None
        if hit:
            key, rec = hit
            return {"result": {
                "agent": "diagnosis",
                "message": (
                    f"Belirtiye en yakin eslesme: {rec['ad']}\n"
                    f"Doğal: {rec['dogal']}\n"
                    f"Kimyasal: {rec['kimyasal']}\n"
                    f"Korunma: {rec['korunma']}"
                ),
                "data": {"tedavi": rec, "hastalik": key},
            }}
        return {"result": {
            "agent": "diagnosis",
            "message": "Teşhis için yaprak/gövde fotoğrafı yükleyin veya hastalık adını/belirtisini yazın.",
            "data": {},
        }}

    if not disease.is_available():
        return {"result": {
            "agent": "diagnosis",
            "message": (
                "Hastalık teşhis modeli henüz hazır değil "
                f"({disease.status()}). Model eğitilince (models/disease/train.py) "
                "fotoğraftan otomatik teşhis yapılacak. Bu arada hastalık adını/belirtisini "
                "yazarsanız tedavi önerisi verebilirim."
            ),
            "data": {"model_durumu": disease.status()},
        }}

    try:
        pred = disease.predict(image_path, topk=3)
    except Exception as exc:
        return {"result": {
            "agent": "diagnosis",
            "message": f"Teşhis yapılamadı ({exc}).",
            "data": {},
        }}

    etiket = pred["etiket"]
    guven = pred["guven"]
    seviye = pred.get("seviye", "kesin")

    # Tanimsiz: model bu yapragi bildigi 17 urunden biri olarak tanimadi.
    # Teshis DAYATMA, yaniltici isi haritasi URETME.
    if seviye == "tanimsiz":
        return {"result": {
            "agent": "diagnosis",
            "message": (
                "Bu yaprak eğittiğim ürünlerden birine benzemiyor; büyük olasılıkla "
                "kapsam dışı bir bitki ya da net olmayan bir fotoğraf.\n"
                "Bu yüzden hastalık teşhisi ve ısı haritası vermiyorum (yanlış olurdu). "
                "Yaprağı yakından ve net çekip tekrar deneyin."
            ),
            "data": {"teshis": pred, "tedavi": None, "gradcam": None},
        }}

    # Grad-CAM (aciklanabilirlik) - basarisiz olursa teshis yine doner
    gradcam_path = None
    try:
        out = image_path.rsplit(".", 1)[0] + "_gradcam.png"
        gradcam_path = disease.gradcam(image_path, out)
    except Exception:
        pass

    # En dusuk kademe: model gercekten emin degil (dagilim disi/net olmayan foto).
    # Teshis dayatma; kullaniciyi net foto/belirti girmeye yonlendir.
    if seviye == "belirsiz":
        olasi = ", ".join(
            f"{disease.label_display(t['etiket'])} %{t['guven'] * 100:.0f}"
            for t in pred["topk"]
        )
        lines = [
            f"Kesin teşhis çıkaramadım (en yüksek güven %{guven * 100:.0f}). "
            "Fotoğraftaki bulgu düşük güvenle eşleşti.",
            f"En olası ihtimaller: {olasi}.",
            "Daha iyi sonuç için: yaprağı yakından ve net çekin, birden fazla "
            "yaprak deneyin, ya da belirtiyi yazın (örn: yaprakta kahverengi leke).",
            "Not: model 17 ürün için eğitildi (domates, biber, patates, narenciye, "
            "zeytin, muz, elma, üzüm ve dahası); kapsam dışı bir bitkiyse doğru teşhis veremez.",
        ]
        if gradcam_path:
            lines.append(f"Isı haritası (Grad-CAM): {gradcam_path}")
        return {"result": {
            "agent": "diagnosis",
            "message": "\n".join(lines),
            "data": {"teshis": pred, "tedavi": None, "gradcam": gradcam_path},
        }}

    # etiketten hastalik anahtarini treatments.yaml'a esle
    tedavi = None
    hit = match_disease(etiket.replace("_", " "))
    if hit:
        tedavi = hit[1]

    # Orta kademe (olasi): dogru sinif genelde ilk sirada ama guven dusuk;
    # teshisi + tedaviyi ver ama "kesin degil" diye isaretle, alternatifi goster.
    urun = pred.get("urun")
    urun_ad = disease.CROP_TR.get(urun, urun.capitalize()) if urun else None

    if seviye == "olasi":
        lines = []
        if urun_ad:
            lines.append(f"Tespit edilen ürün: {urun_ad} (güven %{pred.get('urun_guven', 0) * 100:.0f}).")
        lines.append(f"En olası teşhis: {disease.label_display(etiket)} "
                     f"(güven %{guven * 100:.0f}, kesin değil).")
        if len(pred["topk"]) > 1:
            alt = pred["topk"][1]
            lines.append(f"İkinci ihtimal: {disease.label_display(alt['etiket'])} "
                         f"%{alt['guven'] * 100:.0f}.")
        if "saglikli" in etiket:
            lines.append("Bitki büyük olasılıkla sağlıklı görünüyor.")
        elif tedavi:
            lines.append(f"Bu teşhis doğruysa önerilen tedavi ({tedavi['ad']}):")
            lines.append(f"  Doğal: {tedavi['dogal']}")
            lines.append(f"  Kimyasal: {tedavi['kimyasal']}")
        lines.append("Emin olmak için yaprağı yakından/net bir daha çekebilirsin.")
        if gradcam_path:
            lines.append(f"Isı haritası (Grad-CAM): {gradcam_path}")
        return {"result": {
            "agent": "diagnosis",
            "message": "\n".join(lines),
            "data": {"teshis": pred, "tedavi": tedavi, "gradcam": gradcam_path},
        }}

    lines = []
    if urun_ad:
        lines.append(f"Tespit edilen ürün: {urun_ad} (güven %{pred.get('urun_guven', 0) * 100:.0f}).")
    lines.append(f"Teşhis: {disease.label_display(etiket)} (güven {guven:.0%})")
    if "saglikli" in etiket:
        lines.append("Bitki sağlıklı görünüyor; belirgin hastalık bulgusu yok.")
    elif tedavi:
        lines.append(f"Önerilen tedavi ({tedavi['ad']}):")
        lines.append(f"  Doğal: {tedavi['dogal']}")
        lines.append(f"  Kimyasal: {tedavi['kimyasal']}")
    if gradcam_path:
        lines.append(f"Isı haritası (Grad-CAM): {gradcam_path}")

    return {"result": {
        "agent": "diagnosis",
        "message": "\n".join(lines),
        "data": {"teshis": pred, "tedavi": tedavi, "gradcam": gradcam_path},
    }}
