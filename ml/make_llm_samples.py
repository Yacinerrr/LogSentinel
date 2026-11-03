
import json
import re

import numpy as np
import pandas as pd
import os

from bert_classifier import collect_predictions, get_embeddings
from split import train_sans_test
from common import SEED

REGLES = "config/regex_rules.json"
MODELE = "BAAI/bge-small-en-v1.5"
SEUIL = 0.82   # seuil retenu en A1.2
SORTIE = "data/llm_eval"
PLAFOND_LIGNES = 2   # lignes gardées au maximum par forme
COLONNES = ["source", "log_message", "target_label", "groupe", "bert_pred", "bert_conf"]
# catégorie : (final, réglage, exemples du prompt), en nombre de lignes
QUOTAS = {
    "System Notification": (20, 8, 1), "Error": (12, 6, 1),
    "Security Alert": (16, 6, 1), "HTTP Status": (10, 4, 1),
    "Resource Usage": (6, 2, 1), "User Action": (12, 4, 1),
    "Critical Error": (8, 4, 1), "Workflow Error": (8, 4, 1),
    "Unclassified": (10, 4, 1), "Deprecation Warning": (6, 2, 1),
}


def formes_couvertes_par_regex(df):
    """Formes reconnues par au moins une règle Regex (fichier lu, jamais modifié)."""
    regles = [re.compile(r["pattern"]) for r in json.load(open(REGLES, encoding="utf-8"))]
    touche = df["log_message"].map(lambda m: any(p.search(m) for p in regles))
    return set(df.loc[touche, "groupe"])


def construire_vivier():
    """Logs hors jeu de test et hors formes déjà résolues par Regex."""
    df = train_sans_test()
    exclues = formes_couvertes_par_regex(df)
    vivier = df[~df["groupe"].isin(exclues)].reset_index(drop=True)
    print(f"après test : {len(df)} lignes | formes Regex retirées : {len(exclues)} "
          f"| vivier : {len(vivier)} lignes")
    return vivier


def ajouter_bert(vivier):
    """Ajoute la prédiction de BERT, sa confiance (hors entraînement) et l'indicateur 'difficile'."""
    X = get_embeddings(vivier["log_message"].tolist(), MODELE)
    pred, conf = collect_predictions(vivier, X)
    v = vivier.copy()
    v["bert_pred"] = pred
    v["bert_conf"] = conf
    v["difficile"] = (conf < SEUIL) | (pred != v["target_label"].values)
    return v


def retirer_formes_ambigues(v):
    """Une forme à deux étiquettes différentes ne peut pas servir à mesurer une accuracy."""
    n = v.groupby("groupe")["target_label"].nunique()
    ambigues = set(n[n > 1].index)
    print("formes à étiquettes contradictoires retirées :", len(ambigues))
    return v[~v["groupe"].isin(ambigues)].reset_index(drop=True)


def lignes_par_forme(v):
    """Pour chaque forme : au plus PLAFOND_LIGNES lignes distinctes, tirées au hasard."""
    uniques = v.drop_duplicates(["log_message", "target_label"])
    garde = uniques.sample(frac=1, random_state=SEED).groupby("groupe").head(PLAFOND_LIGNES)
    return {f: list(idx) for f, idx in garde.groupby("groupe").groups.items()}


def afficher_comptes(v):
    """Formes et lignes difficiles, par catégorie et par origine."""
    v = v.assign(origine=np.where(v["source"] == "synthetic", "synthétique", "réel"))
    cles = ["target_label", "origine"]
    formes = v.groupby(cles)["groupe"].nunique().rename("formes")
    dur = v[v["difficile"]]
    formes_dur = dur.groupby(cles)["groupe"].nunique().rename("formes_difficiles")
    lignes_dur = dur.groupby(cles).size().rename("lignes_difficiles")
    tableau = pd.concat([formes, formes_dur, lignes_dur], axis=1).fillna(0).astype(int)
    print(tableau.to_string())
    print("\nTotal difficile :", int(v["difficile"].sum()), "lignes /", len(v))


def formes_de(v, cat):
    """Formes d'une catégorie : confiance moyenne, 'BERT a toujours raison' et 'difficile'."""
    g = v[v["target_label"] == cat].assign(ok=lambda d: d["bert_pred"] == d["target_label"])
    return g.groupby("groupe").agg(conf=("bert_conf", "mean"), ok=("ok", "all"),
                                   dur=("difficile", "any"))


def prendre(formes, quota, par_forme, deja):
    """Prend des formes dans l'ordre jusqu'à atteindre le quota de lignes."""
    idx = []
    for f in formes:
        if len(idx) >= quota:
            break
        if f in deja:
            continue
        idx += par_forme[f][: quota - len(idx)]
        deja.add(f)
    return idx


def tirer(v):
    """Répartit les formes entre exemples, réglage et final, sans recoupement."""
    rng = np.random.RandomState(SEED)
    par_forme = lignes_par_forme(v)
    deja = set()
    jeux = {"fewshot": [], "tune": [], "final": []}
    for cat, (_, _, n_ex) in QUOTAS.items():
        f = formes_de(v, cat)
        clairs = f[f["ok"]] if f["ok"].any() else f
        jeux["fewshot"] += prendre(list(clairs.sort_values("conf", ascending=False).index),
                                   n_ex, par_forme, deja)
    for cat, (n_final, n_tune, _) in QUOTAS.items():
        f = formes_de(v, cat)
        f = f[~f.index.isin(deja)]
        sous = list(f[f["dur"]].index)
        rng.shuffle(sous)
        ordre = sous + list(f[~f["dur"]].sort_values("conf").index)
        for nom, n in (("final", n_final), ("tune", n_tune)):
            avant = len(jeux[nom])
            jeux[nom] += prendre(ordre, n, par_forme, deja)
            if len(jeux[nom]) - avant < n:
                print(f"  manque de formes : {cat} / {nom} : {len(jeux[nom]) - avant} lignes sur {n}")
    return {nom: v.loc[idx, COLONNES] for nom, idx in jeux.items()}


def ecrire(jeux):
    os.makedirs(SORTIE, exist_ok=True)
    for nom, d in jeux.items():
        d = d.sample(frac=1, random_state=SEED).reset_index(drop=True)
        d.to_csv(f"{SORTIE}/{nom}.csv", index=False, encoding="utf-8")
        print(f"\n{nom} : {len(d)} lignes, {d['groupe'].nunique()} formes, "
              f"{int((d['source'] == 'synthetic').sum())} synthétiques")
        print(d.groupby("target_label").agg(
            lignes=("log_message", "size"),
            sous_seuil=("bert_conf", lambda c: int((c < SEUIL).sum()))).to_string())


if __name__ == "__main__":
    v = retirer_formes_ambigues(ajouter_bert(construire_vivier()))
    afficher_comptes(v)
    ecrire(tirer(v))