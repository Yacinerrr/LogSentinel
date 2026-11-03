"""See what masking does to YOUR logs, without calling any LLM. Runs fully offline.

  python scripts/preview_masking.py data/labeled_logs.csv
  python scripts/preview_masking.py data/labels/openssh.csv            # finds the message column by itself
  python scripts/preview_masking.py FILE --label-col target_label      # which labels get altered most
  python scripts/preview_masking.py FILE --kind token,card,email       # only examples of these kinds
  python scripts/preview_masking.py FILE --examples 10                 # examples per kind (default 5)

Use it to (1) find secrets the rules MISS, (2) find false positives that hurt classification.
"""
import argparse
import csv
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.masking import mask  # noqa: E402

GUESSES = ["log_message", "message", "Content", "content", "text", "log", "raw", "Message", "Text"]

ap = argparse.ArgumentParser()
ap.add_argument("csv")
ap.add_argument("--col", default=None, help="message column (auto-detected if omitted)")
ap.add_argument("--label-col", default=None)
ap.add_argument("--kind", default=None, help="comma list, e.g. token,card,email")
ap.add_argument("--examples", type=int, default=5, help="examples per kind")
ap.add_argument("--no-ips", action="store_true")
ap.add_argument("--no-usernames", action="store_true")
a = ap.parse_args()

total = changed = 0
kinds, by_label = Counter(), Counter()
shown: dict[str, list] = defaultdict(list)
wanted = set(a.kind.split(",")) if a.kind else None
seen_lines = Counter()

with open(a.csv, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames or []
    col = a.col or next((g for g in GUESSES if g in cols), None)
    if col not in cols:
        sys.exit(f"Column {col or a.col!r} not found. Columns in this file: {cols}\nUse --col <name>.")
    print(f"file: {a.csv} | message column: {col!r} | columns: {cols}")
    for row in reader:
        total += 1
        text = row[col] or ""
        seen_lines[text] += 1
        r = mask(text, ips=not a.no_ips, usernames=not a.no_usernames)
        if not r.changed:
            continue
        changed += 1
        kinds.update(r.counts)
        if a.label_col and a.label_col in row:
            by_label[row[a.label_col]] += 1
        for k in r.counts:
            if (wanted is None or k in wanted) and len(shown[k]) < a.examples:
                shown[k].append((text, r.text))

dups = sum(c - 1 for c in seen_lines.values() if c > 1)
print(f"\n{changed}/{total} lines changed ({100 * changed / max(total, 1):.1f}%)   |   exact duplicate lines: {dups}")
print("hits by kind:", dict(kinds.most_common()))
if by_label:
    print("changed lines by label:", dict(by_label.most_common()))
for k in sorted(shown, key=lambda k: -kinds[k]):
    print(f"\n=== {k}: {kinds[k]} hits, examples ===")
    for before, after in shown[k]:
        print("BEFORE:", before[:220])
        print("AFTER :", after[:220], "\n")
