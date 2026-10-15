"""Train the BERT-embedding head. Usage: python -m ml.train data/synthetic.csv [--min-samples 100]"""
import argparse
import json
import joblib
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--min-samples", type=int, default=100)
ap.add_argument("--model-name", default="all-MiniLM-L6-v2")
ap.add_argument("--out", default="models/bert_clf.joblib")
a = ap.parse_args()

df = pd.read_csv(a.csv).dropna(subset=["log_message", "target_label"])
df = df[df["target_label"].map(df["target_label"].value_counts()) >= a.min_samples]
print("training labels:", sorted(df["target_label"].unique()))

X = SentenceTransformer(a.model_name).encode(df["log_message"].tolist(), show_progress_bar=True)
y = df["target_label"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
clf = LogisticRegression(max_iter=2000, class_weight="balanced").fit(Xtr, ytr)

report = classification_report(yte, clf.predict(Xte), output_dict=True)
print(classification_report(yte, clf.predict(Xte)))
joblib.dump(clf, a.out)
with open(a.out.replace(".joblib", "_metrics.json"), "w") as f:
    json.dump(report, f, indent=2)
print("saved", a.out)
