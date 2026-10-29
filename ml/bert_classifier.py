
from pathlib import Path
import hashlib

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold
import matplotlib.pyplot as plt
from split import train_sans_test




from common import load, SEED

DATA = "data/labeled_logs.csv"
CACHE_DIR = Path("models/cache_embeddings")
THRESHOLD = 0.82


def get_embeddings(texts, model_name):
    """Transforme chaque log en vecteur et met le résultat en cache."""

    # Empreinte du contenu des logs
    content = "\n".join(texts)
    dataset_hash = hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()[:16]

    cache = CACHE_DIR / f"{model_name.replace('/', '_')}_{dataset_hash}.npy"

    # Réutiliser le cache s'il existe
    if cache.exists():
        print("Cache trouvé : chargement des embeddings...")
        return np.load(cache)

    # Sinon, calculer les embeddings
    print("Cache absent : calcul des embeddings...")
    model = SentenceTransformer(model_name)

    emb = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(cache, emb)

    return emb


def make_classifier():
    return LogisticRegression(max_iter=2000, class_weight="balanced")


def eval_grouped_bert(df, X, n_splits=5):
    y = df["target_label"]
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    scores = {"toutes": [], "réelles": [], "synthétiques": []}
    for tr, te in cv.split(df["groupe"], y, groups=df["groupe"]):
        m = make_classifier().fit(X[tr], y.iloc[tr])
        test = df.iloc[te]
        pred = m.predict(X[te])
        masques = {
            "toutes": test["source"].notna(),
            "réelles": test["source"] != "synthetic",
            "synthétiques": test["source"] == "synthetic",
        }
        for nom, masque in masques.items():
            yt = test["target_label"][masque]
            if len(yt) == 0:
                continue
            scores[nom].append(f1_score(yt, pred[masque.values], labels=sorted(set(yt)),
                                        average="macro", zero_division=0))
    return {nom: (np.mean(v), np.std(v)) for nom, v in scores.items()}


def collect_predictions(df, X, n_splits=5):
    y = df["target_label"]
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=SEED)
    pred = np.empty(len(df), dtype=object)
    conf = np.zeros(len(df))
    for tr, te in cv.split(df["groupe"], y, groups=df["groupe"]):
        m = make_classifier().fit(X[tr], y.iloc[tr])
        proba = m.predict_proba(X[te])
        pred[te] = m.classes_[proba.argmax(axis=1)]
        conf[te] = proba.max(axis=1)
    return pred, conf


def precision_coverage(y_true, pred, conf, thresholds):
    rows = []
    for t in thresholds:
        acceptes = conf >= t
        couverture = acceptes.mean()
        precision = (pred[acceptes] == y_true[acceptes]).mean() if acceptes.any() else np.nan
        rows.append((t, couverture, precision))
    return rows





def plot_curve(rows, path, chosen=None):
    t = [r[0] for r in rows]
    cov = [r[1] for r in rows]
    prec = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(cov, prec, marker="o")
    for ti, ci, pi in zip(t, cov, prec):
        if round(ti * 100) % 10 == 0:
            ax.annotate(f"{ti:.1f}", (ci, pi), textcoords="offset points", xytext=(5, 5))

    if chosen is not None:
        r = min(rows, key=lambda r: abs(r[0] - chosen))
        ax.scatter([r[1]], [r[2]], s=140, color="red", zorder=5,
                   label=f"seuil retenu = {chosen:.2f}")
        ax.legend()
    ax.set_xlabel("Couverture (part des logs traités par BERT)")
    ax.set_ylabel("Précision (sur les logs acceptés)")
    ax.set_title("bge-small : précision vs couverture (logs réels)")
    ax.grid(True)
    fig.savefig(path, dpi=150, bbox_inches="tight")





if __name__ == "__main__":
    df = train_sans_test(DATA)
    X = get_embeddings(df["log_message"].tolist(), "BAAI/bge-small-en-v1.5")
    pred, conf = collect_predictions(df, X)

    # courbe calculée sur les logs réels uniquement
    reel = (df["source"] != "synthetic").values
    y_true = df["target_label"].values[reel]
    thresholds = np.arange(0.30, 1.00, 0.01)
    rows = precision_coverage(y_true, pred[reel], conf[reel], thresholds)

    print("seuil  couverture  précision")
    for t, c, p in rows:
        if round(t * 100) % 5 != 0:
            continue
        print(f"{t:.2f}   {c:6.1%}      {p:6.1%}")

    # chiffres du seuil retenu (à recopier dans docs/RESULTS.md)
    t, c, p = min(rows, key=lambda r: abs(r[0] - THRESHOLD))
    print(f"\nSeuil retenu {THRESHOLD:.2f} : couverture {c:.1%}, précision {p:.1%}")
        # précision à plusieurs niveaux de couverture visés
    print("\ncouverture visée   seuil   couverture   précision")
    for cible_cov in (0.50, 0.60, 0.65, 0.70, 0.80):
        ok = [r for r in rows if r[1] >= cible_cov]
        if not ok:
            print(f"{cible_cov:.0%}               inatteignable")
            continue
        t, c, p = max(ok, key=lambda r: r[0])
        print(f"{cible_cov:.0%}               {t:.2f}    {c:6.1%}      {p:6.1%}")


    

    plot_curve(rows, "docs/precision_coverage.png", chosen=THRESHOLD)
    print("Graphique sauvegardé dans docs/precision_coverage.png")