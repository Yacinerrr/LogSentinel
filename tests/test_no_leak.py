import pandas as pd

from split import formes_du_test, train_sans_test

def test_test_csv_valide():
    test = pd.read_csv("data/test.csv")
    assert len(test) > 0
    assert test["target_label"].notna().all()
    assert not test.duplicated().any()


def test_aucune_forme_commune_train_test():
    train = train_sans_test()
    assert not (formes_du_test() & set(train["groupe"]))


def test_aucune_ligne_commune_train_test():
    train = train_sans_test()
    test = pd.read_csv("data/test.csv")
    assert not (set(test["log_message"]) & set(train["log_message"]))


def test_scripts_entrainement_utilisent_train_sans_test():
    for p in ["ml/baseline_tfidf.py", "ml/bert_classifier.py"]:
        assert "train_sans_test" in open(p, encoding="utf-8").read(), p