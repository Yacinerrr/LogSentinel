# LogSentinel: Task Split (2 people)

**Dev A = ML & Intelligence** · **Dev B = Platform & Security/Ops**
Pick whoever is more comfortable with ML as A. Estimated load is balanced: **~67 h each + ~10 h shared** over 6 weeks (~12 h/week each). Hours are rough estimates, so adjust after week 1.

## 1. How we avoid blocking each other

**File ownership.** Only the owner edits these files directly. The other person opens a PR.

| Dev A owns | Dev B owns | Shared (PR + review by both) |
|---|---|---|
| `app/classifiers/*` | `app/api/*` | `app/schemas.py` |
| `config/regex_rules.json` | `app/db.py`, `app/text.py` | `docs/*` |
| `ml/*` | `dashboard/*` | `tests/*` (each owns tests for own code) |
| `models/*` | `Dockerfile`, `docker-compose.yml`, `.github/*`, `Makefile` | `README.md` |

**Handoff points (the only moments one person waits on the other).**

| # | When | A gives B | B gives A |
|---|---|---|---|
| H1 | End wk 1 | Frozen label taxonomy + CSV schema (`source, log_message, target_label`) | CI green + issue board + Docker running |
| H2 | Wk 2 | Model artifact format: `models/bert_clf.joblib` + `bert_clf_metrics.json` | Model loading path / registry skeleton |
| H3 | Wk 3 | `Prediction` fields frozen (label, tier, confidence, latency) | OpenAPI contract frozen (dashboard depends on it) |
| H4 | Wk 4 | Retrain script that consumes `/feedback/export` | Feedback export format stable + volume of reviewed data |

**Working rules**
- Small PRs (under ~300 lines), **always reviewed by the other person**, `main` stays green.
- Branch names: `ml/<task>`, `platform/<task>`.
- 2 syncs a week, 20 minutes: Monday (plan) and Thursday (blockers + demo what works).
- **Cross-training hour each week:** each person explains their half to the other. The review quality depends on this, and the final report/demo needs both.
- GitHub labels: `area:ml`, `area:platform`, `shared`, plus `blocked`.

---

## 2. Tasks

Legend: **Dep** = depends on. **Done when** = objective acceptance criterion.

### Phase 0: Foundations (week 1)

| ID | Owner | Task | Hrs | Dep | Done when |
|---|---|---|---|---|---|
| A0.1 | A | Define taxonomy: each label with definition + 3 examples + edge cases | 3 | none | `docs/TAXONOMY.md` merged, both agree |
| A0.2 | A | Collect data: Loghub samples + `make data` synthetic; map to taxonomy | 6 | A0.1 | `data/` has ≥ 2k labeled rows, 8+ labels |
| A0.3 | A | Regex rules v1 from real samples | 4 | A0.2 | Regex resolves ≥ 30% of the dataset at ≥ 99% precision |
| B0.1 | B | Repo hygiene: branch protection, PR template, issue board, labels | 2 | none | Board exists with all tasks below |
| B0.2 | B | `docker compose up` works from a clean clone; CI green | 3 | none | Fresh clone → API + dashboard reachable |
| S0.1 | Both | Cross-training hour + agree handoff points | 1 | none | Calendar invites for the syncs |

### Phase 1: Core (weeks 2-3)

| ID | Owner | Task | Hrs | Dep | Done when |
|---|---|---|---|---|---|
| A1.1 | A | TF-IDF + LogReg baseline | 4 | A0.2 | Macro-F1 recorded in `docs/RESULTS.md` |
| A1.2 | A | BERT-embedding classifier + threshold tuning (precision/coverage curve) | 8 | A1.1 | Beats baseline; threshold chosen with a plot |
| A1.3 | A | **Freeze held-out test set** (never trained on) | 3 | A0.2 | `data/test.csv` committed, documented |
| A1.4 | A | R1 prompt engineering; test on ≥ 100 hard samples; measure format-failure rate | 8 | A0.2 | ≥ 95% parseable replies, accuracy logged |
| A1.5 | A | `ml.evaluate` upgraded: per-tier accuracy, confusion matrix, latency, error dump | 4 | A1.2, A1.4 | One command prints the full report |
| B1.1 | B | API-key auth (header) + per-key rate limit + request size limits | 7 | none | Unauthorized → 401, tested |
| B1.2 | B | Alembic migrations (replace `create_all`) | 4 | none | `alembic upgrade head` on empty DB works |
| B1.3 | B | Structured JSON logging + request IDs | 3 | none | Each request traceable in logs |
| B1.4 | B | **PII/secret masking before the LLM tier** (emails, tokens, passwords, IPs optional) | 5 | A1.4 | Test proves a secret never reaches the LLM call |
| B1.5 | B | Dashboard polish: filters, per-label table, CSV download | 6 | H3 | Usable by someone who didn't build it |
| B1.6 | B | Large-CSV handling (chunked processing, progress) | 3 | none | 50k-row CSV processes without timeout |

### Phase 2: Intelligence & ops (weeks 4-5)

| ID | Owner | Task | Hrs | Dep | Done when |
|---|---|---|---|---|---|
| A2.1 | A | Retrain-from-feedback script + **promotion gate** (new model must beat old on frozen test set) | 8 | H4 | Script exits non-zero if the new model is worse |
| A2.2 | A | Few-shot examples auto-selected from reviewed logs into the R1 prompt | 5 | A1.4 | Measured accuracy change documented |
| A2.3 | A | Novelty detection: distance to nearest known cluster flags new log types | 8 | A1.2 | Flagged logs appear in the review queue |
| A2.4 | A | *(Stretch)* Fine-tune a small BERT vs. frozen embeddings, compare | 10 | A1.5 | Comparison table in RESULTS.md |
| B2.1 | B | Model registry + versioning + `POST /admin/reload-model` (no restart) | 6 | H2 | Swap model while API is serving |
| B2.2 | B | Drift panel: label distribution over time | 6 | none | Chart in dashboard |
| B2.3 | B | Cost panel: LLM calls, cache hit-rate, estimated spend | 4 | none | Numbers match DB |
| B2.4 | B | Streaming ingestion: tail a log file / syslog UDP into the pipeline | 8 | H3 | Live lines show up in dashboard within seconds |

### Phase 3: Hardening & ship (week 6)

| ID | Owner | Task | Hrs | Dep | Done when |
|---|---|---|---|---|---|
| A3.1 | A | Final evaluation + error analysis (worst 20 cases with hypotheses) | 6 | all A | `docs/RESULTS.md` final |
| B3.1 | B | Load test (locust) on regex+BERT path; document bottlenecks | 5 | B2.* | Throughput number reported |
| B3.2 | B | Architecture diagram, deployment guide, `.env` docs | 4 | none | New person can deploy from README |
| S3.1 | Both | Demo script + final report/slides; each presents own half | 6 | all | Dry run completed |
| S3.2 | Both | Cross-review: each person fixes one bug in the other's half | 3 | none | Proves you both understand the whole |

---

## 3. Workload check

| | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Total |
|---|---|---|---|---|---|
| **Dev A** | 13 | 27 | 21 (+10 stretch) | 6 | **67** |
| **Dev B** | 5 | 28 | 24 | 9 | **66** |
| Shared | 1 | none | none | 9 | **10** |

Dev B has little to do in week 1 while A builds the dataset. B should use the spare time to start **B1.1-B1.3** early and to learn the ML side (read `app/classifiers/` and `ml/train.py`), so cross-training is real.

## 4. If someone falls behind
- **Cut first:** A2.4 (fine-tuning), B2.4 (streaming), B2.3 (cost panel).
- **Never cut:** A1.3 (frozen test set), A2.1's promotion gate, B1.4 (PII masking), B1.1 (auth), tests.
- If A is late, B can take A0.3 (regex rules) since it needs no ML knowledge.
- If B is late, A can take B1.3 and B2.2.
