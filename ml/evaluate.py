"""End-to-end evaluation of the full pipeline. Usage: python -m ml.evaluate data/test.csv"""
import sys
import pandas as pd
from sklearn.metrics import classification_report
from app.config import get_settings
from app.db import Database
from app.classifiers.pipeline import build_pipeline

s = get_settings()
pipe = build_pipeline(s, Database("sqlite:///data/eval.db"))
df = pd.read_csv(sys.argv[1])
preds = [pipe.classify(r.source, r.log_message) for r in df.itertuples()]
df["pred"] = [p.label for p in preds]
df["tier"] = [p.tier for p in preds]
df["latency_ms"] = [p.latency_ms for p in preds]

print("== overall ==")
print(classification_report(df["target_label"], df["pred"], zero_division=0))
print("== per tier ==")
for tier, g in df.groupby("tier"):
    print(f"{tier:9s} n={len(g):5d} acc={(g.pred == g.target_label).mean():.3f} avg_ms={g.latency_ms.mean():.1f}")
