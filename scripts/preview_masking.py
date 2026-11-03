"""See what masking does to YOUR logs, without calling any LLM. Runs fully offline.

  python scripts/preview_masking.py data/train.csv                 # column 'log_message'
  python scripts/preview_masking.py data/train.csv --examples 30   # show more before/after pairs
  python scripts/preview_masking.py data/train.csv --label-col target_label   # also shows which labels get altered most

Use it to (1) find secrets the rules MISS, (2) find false positives that hurt classification.
"""
import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.masking import mask  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--col", default="log_message")
ap.add_argument("--label-col", default=None)
ap.add_argument("--examples", type=int, default=15)
ap.add_argument("--no-ips", action="store_true")
ap.add_argument("--no-usernames", action="store_true")
a = ap.parse_args()

total = changed = 0
kinds, by_label, shown = Counter(), Counter(), []
with open(a.csv, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        total += 1
        r = mask(row[a.col], ips=not a.no_ips, usernames=not a.no_usernames)
        if r.changed:
            changed += 1
            kinds.update(r.counts)
            if a.label_col:
                by_label[row[a.label_col]] += 1
            if len(shown) < a.examples:
                shown.append((row[a.col], r.text))

print(f"\n{changed}/{total} lines changed ({100 * changed / max(total, 1):.1f}%)")
print("hits by kind:", dict(kinds.most_common()))
if by_label:
    print("changed lines by label:", dict(by_label.most_common()))
print("\n--- examples (before -> after) ---")
for before, after in shown:
    print("BEFORE:", before[:200])
    print("AFTER :", after[:200], "\n")
