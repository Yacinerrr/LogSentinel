"""A1.3 : construit data/test.csv (jeu de test figé, jamais utilisé pour entraîner)."""
import json
import os
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from common import load, normalize, SEED

REGLES = "config/regex_rules.json"
FRACTION = 0.20   # part des formes mises de côté, par catégorie
MIN_FORMES = 5    # en dessous, la catégorie n'a pas de test réel
PLAFOND = 20      # lignes gardées au maximum par forme
LLM_FICHIERS = ["data/logsentinel_synthetic_logs.csv",
                "data/logsentinel_synthetic_logs_2.csv"]  
SEUIL_PROCHE = 0.70
NON_TRANCHEES = ("unrecognized parameter", "invalid timestamp", "unknown execution mode")


def formes_couvertes_par_regex(reel):
    """Formes réelles reconnues par au moins une règle Regex (fichier lu, jamais modifié)."""
    regles = [re.compile(r["pattern"]) for r in json.load(open(REGLES, encoding="utf-8"))]
    touche = reel["log_message"].map(lambda m: any(p.search(m) for p in regles))
    return set(reel.loc[touche, "groupe"])

def tirer_test(reel, exclues):
    """Choisit des formes entières par catégorie ; renvoie (lignes de test, formes de test)."""
    rng = np.random.RandomState(SEED)
    formes_test = []
    for cat, g in reel[~reel["groupe"].isin(exclues)].groupby("target_label"):
        formes = sorted(g["groupe"].unique())
        if len(formes) < MIN_FORMES:
            continue
        n = max(1, round(FRACTION * len(formes)))
        formes_test += list(rng.choice(formes, size=n, replace=False))
    en_test = reel[reel["groupe"].isin(formes_test)]
    lignes = (en_test.drop_duplicates(["log_message", "target_label"]).sample(frac=1, random_state=SEED).groupby("groupe").head(PLAFOND))
              
    return lignes, set(formes_test)


def lignes_llm(train):
    """Lignes du LLM gardées : on retire les copies de nos données et les cas non tranchés."""
    t = pd.concat([pd.read_csv(p) for p in LLM_FICHIERS if os.path.exists(p)], ignore_index=True)
    t["groupe"] = t["log_message"].map(normalize)
    tr = train.drop_duplicates("groupe")
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit(tr["groupe"])
    sim = cosine_similarity(vec.transform(t["groupe"]), vec.transform(tr["groupe"]))
    t["sim"] = sim.max(axis=1)
    flou = t["log_message"].str.contains("|".join(NON_TRANCHEES), case=False)
    retire = (t["sim"] >= SEUIL_PROCHE) | flou
    print("lignes du LLM :", len(t), "| trop proches :", (t["sim"] >= SEUIL_PROCHE).sum(),
          "| non tranchées :", flou.sum(), "| gardées :", (~retire).sum())
    gardees = t[~retire].copy()
    gardees["source"] = "synthetic"
    return gardees[["source", "log_message", "target_label"]]


def main():
    df = load("data/labeled_logs.csv")
    reel = df[df["source"] != "synthetic"]
    couvertes = formes_couvertes_par_regex(reel)
    test_reel, formes = tirer_test(reel, couvertes)
    test = pd.concat([test_reel[["source", "log_message", "target_label"]], lignes_llm(df)],
                     ignore_index=True).drop_duplicates().reset_index(drop=True)
    test.to_csv("data/test.csv", index=False, encoding="utf-8", lineterminator="\n")
    print("data/test.csv :", len(test), "lignes,", len(formes), "formes réelles de test")
    print(pd.crosstab(test["target_label"], test["source"] == "synthetic",
                      colnames=["artificielle"]))
if __name__ == "__main__":
    main()