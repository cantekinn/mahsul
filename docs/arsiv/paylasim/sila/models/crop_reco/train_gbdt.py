"""LightGBM urun oneri modeli egitimi (Sprint 1 - Sila, opsiyonel ikinci gorus).

Girdi: Kaggle "Crop Recommendation Dataset" CSV (N,P,K,temperature,humidity,ph,
rainfall,label). Veri seti Hindistan urunlerini kapsar; bu model bolgesel bir
"iklim-toprak parmak izi" ogrenicisi olarak kural tabanli motoru destekler.

Kullanim:
    1) Kaggle'dan Crop_recommendation.csv indir -> data/Crop_recommendation.csv
    2) py -m models.crop_reco.train_gbdt

CSV yoksa egitim atlanir ve kural tabanli motor (recommender.py) birincil kalir.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
_CSV = _ROOT / "data" / "Crop_recommendation.csv"
_MODEL = Path(__file__).resolve().parent / "gbdt_model.txt"
_LABELS = Path(__file__).resolve().parent / "gbdt_labels.txt"

_FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


def train() -> None:
    if not _CSV.exists():
        print(f"[atlandi] Veri seti yok: {_CSV}")
        print("Kaggle 'Crop Recommendation Dataset' indirip bu yola koyun.")
        print("Kural tabanli motor (recommender.py) birincil oneri kaynagi olarak kullanilir.")
        return

    import lightgbm as lgb
    import pandas as pd
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split

    df = pd.read_csv(_CSV)
    labels = sorted(df["label"].unique())
    label_to_id = {name: i for i, name in enumerate(labels)}
    y = df["label"].map(label_to_id)
    X = df[_FEATURES]

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = lgb.LGBMClassifier(
        objective="multiclass",
        num_class=len(labels),
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=31,
        random_state=42,
    )
    model.fit(X_tr, y_tr)
    acc = accuracy_score(y_te, model.predict(X_te))
    print(f"[ok] Dogruluk (test): {acc:.4f}  |  sinif sayisi: {len(labels)}")

    model.booster_.save_model(str(_MODEL))
    _LABELS.write_text("\n".join(labels), encoding="utf-8")
    print(f"[ok] Model kaydedildi: {_MODEL}")
    print(f"[ok] Etiketler kaydedildi: {_LABELS}")


if __name__ == "__main__":
    train()
