import json
import re
from itertools import combinations

import pandas as pd

from common import normalize
from split import formes_du_test

JEUX = ["fewshot", "tune", "final"]
CATEGORIES = {"Critical Error", "Deprecation Warning", "Error", "HTTP Status",
              "Resource Usage", "Security Alert", "System Notification",
              "Unclassified", "User Action", "Workflow Error"}


def charger():
    jeux = {}
    for nom in JEUX:
        d = pd.read_csv(f"data/llm_eval/{nom}.csv")
        d["forme"] = d["log_message"].map(normalize)
        jeux[nom] = d
    return jeux


def test_fichiers_valides():
    for nom, d in charger().items():
        assert len(d) > 0, nom
        assert d["target_label"].isin(CATEGORIES).all(), nom
        assert not d.duplicated(["log_message", "target_label"]).any(), nom


def test_taille_jeu_final():
    assert len(charger()["final"]) >= 100


def test_aucune_forme_commune_entre_jeux():
    jeux = charger()
    for a, b in combinations(JEUX, 2):
        assert not (set(jeux[a]["forme"]) & set(jeux[b]["forme"])), (a, b)


def test_aucune_forme_du_jeu_de_test():
    test = formes_du_test()
    for nom, d in charger().items():
        assert not (set(d["forme"]) & test), nom


def test_aucune_forme_couverte_par_regex():
    regles = [re.compile(r["pattern"])
              for r in json.load(open("config/regex_rules.json", encoding="utf-8"))]
    for nom, d in charger().items():
        touche = d["log_message"].map(lambda m: any(p.search(m) for p in regles))
        assert not touche.any(), (nom, d.loc[touche, "log_message"].head(3).tolist())