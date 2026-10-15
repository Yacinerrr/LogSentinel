"""A1.1 : baseline TF-IDF + LogisticRegression.
Usage: python -m ml.baseline_tfidf data/labeled_logs.csv
"""
import argparse
import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import StratifiedGroupKFold, train_test_split
from sklearn.pipeline import make_pipeline

SEED = 42


def normalize(s):
    """Masque ce qui change d'une ligne à l'autre sans changer son sens."""
    s = re.sub(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "<UUID>", s)
    s = re.sub(r"\b[0-9a-fA-F]{16,}\b", "<HEX>", s)
    s = re.sub(r"\d+(\.\d+)*", "<N>", s)
    return s


def load(path):
    df = pd.read_csv(path).dropna(subset=["log_message", "target_label"])
    df["groupe"] = df["log_message"].map(normalize)
    return df.reset_index(drop=True)


def make_model():
    return make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        LogisticRegression(max_iter=2000, class_weight="balanced"),
    )


def eval_random(df, col="groupe"):
    X, y = df[col], df["target_label"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)
    pred = make_model().fit(Xtr, ytr).predict(Xte)
    return f1_score(yte, pred, average="macro"), classification_report(yte, pred, zero_division=0)


def eval_grouped(df):
    ...  # étape 4


def top_words(model, k=8):
    ...  # étape 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    a = ap.parse_args()
    df = load(a.csv)
    print(len(df), "lignes,", df["groupe"].nunique(), "groupes")
    for col in ["log_message", "groupe"]:
        f1, rapport = eval_random(df, col)
        print(f"[80/20 au hasard] texte = {col:11s} macro-F1 = {f1:.3f}")
    print(rapport)


if __name__ == "__main__":
    main()
