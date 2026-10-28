"""Entraînement = labeled_logs.csv privé de toutes les formes présentes dans data/test.csv."""
import pandas as pd

from common import load, normalize


def formes_du_test(chemin_test="data/test.csv"):
    test = pd.read_csv(chemin_test)
    return set(test["log_message"].map(normalize))


def train_sans_test(chemin_labeled="data/labeled_logs.csv", chemin_test="data/test.csv"):
    df = load(chemin_labeled)
    return df[~df["groupe"].isin(formes_du_test(chemin_test))].reset_index(drop=True)