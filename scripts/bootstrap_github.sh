#!/usr/bin/env bash
# Creates labels, milestones and one issue per task in docs/TASKS.md.
# Requires: gh CLI authenticated (gh auth login), run from the repo root.
# NOT idempotent for issues: run it once.
set -euo pipefail

gh label create "area:ml"       --color 1D76DB --description "Dev A" --force
gh label create "area:platform" --color 0E8A16 --description "Dev B" --force
gh label create "shared"        --color 5319E7 --force
gh label create "blocked"       --color B60205 --force
gh label create "stretch"       --color FBCA04 --force

REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
for p in "Phase 0: Foundations" "Phase 1: Core" "Phase 2: Intelligence & ops" "Phase 3: Ship"; do
  gh api "repos/$REPO/milestones" -f title="$p" >/dev/null 2>&1 || true
done

# ID|labels|phase|hours|title
while IFS='|' read -r id labels phase hrs title; do
  [ -z "$id" ] && continue
  gh issue create --title "[$id] $title" --label "$labels" --milestone "$phase" \
    --body "Task **$id** · estimate **${hrs} h**. Acceptance criteria: see docs/TASKS.md."
done << 'TASKS'
A0.1|area:ml|Phase 0: Foundations|3|Define taxonomy (decision log, kappa check)
A0.2|area:ml|Phase 0: Foundations|6|Collect data: Loghub + synthetic, map to taxonomy
A0.3|area:ml|Phase 0: Foundations|4|Regex rules v1
B0.1|area:platform|Phase 0: Foundations|2|Repo hygiene: branch protection, templates, board
B0.2|area:platform|Phase 0: Foundations|3|docker compose up from clean clone; CI green
S0.1|shared|Phase 0: Foundations|1|Cross-training hour + agree handoff points
A1.1|area:ml|Phase 1: Core|4|TF-IDF + LogReg baseline
A1.2|area:ml|Phase 1: Core|8|BERT-embedding classifier + threshold tuning
A1.3|area:ml|Phase 1: Core|3|Freeze held-out test set
A1.4|area:ml|Phase 1: Core|8|R1 prompt engineering (full taxonomy) + eval
A1.5|area:ml|Phase 1: Core|4|ml.evaluate: per-tier report, confusion matrix, error dump
B1.1|area:platform|Phase 1: Core|7|API-key auth + rate limit + size limits
B1.2|area:platform|Phase 1: Core|4|Alembic migrations
B1.3|area:platform|Phase 1: Core|3|Structured JSON logging + request IDs
B1.4|area:platform|Phase 1: Core|5|PII/secret masking before the LLM tier
B1.5|area:platform|Phase 1: Core|6|Dashboard polish
B1.6|area:platform|Phase 1: Core|3|Large-CSV handling
A2.1|area:ml|Phase 2: Intelligence & ops|8|Retrain-from-feedback + promotion gate
A2.2|area:ml|Phase 2: Intelligence & ops|5|Few-shot examples from reviewed logs into R1 prompt
A2.3|area:ml|Phase 2: Intelligence & ops|8|Novelty detection
A2.4|area:ml,stretch|Phase 2: Intelligence & ops|10|Fine-tune small BERT vs frozen embeddings
B2.1|area:platform|Phase 2: Intelligence & ops|6|Model registry + hot reload
B2.2|area:platform|Phase 2: Intelligence & ops|6|Drift panel
B2.3|area:platform|Phase 2: Intelligence & ops|4|Cost panel
B2.4|area:platform,stretch|Phase 2: Intelligence & ops|8|Streaming ingestion (file tail / syslog)
A3.1|area:ml|Phase 3: Ship|6|Final evaluation + error analysis
B3.1|area:platform|Phase 3: Ship|5|Load test (locust)
B3.2|area:platform|Phase 3: Ship|4|Architecture diagram + deployment guide
S3.1|shared|Phase 3: Ship|6|Demo script + final report
S3.2|shared|Phase 3: Ship|3|Cross-review: fix a bug in the other half
TASKS
echo "Done. Open the Projects tab and add these issues to a board."
