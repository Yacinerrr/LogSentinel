# LogSentinel: Project Plan (team of 2, ~6 weeks)

**Goal:** a production-style hybrid log classifier (Regex → BERT → DeepSeek R1) with an API,
review dashboard, feedback loop, and measurable evaluation.

## Roles
| | **Dev A: ML & Intelligence** | **Dev B: Platform & Ops** |
|---|---|---|
| Owns | `ml/`, `app/classifiers/`, `config/regex_rules.json` | `app/api/`, `app/db.py`, `dashboard/`, Docker, CI |
| Contract | `Classifier.predict(source, message) -> Prediction \| None` (`app/classifiers/base.py`) | `/classify`, `/classify/batch`, `/classify/csv`, `/logs`, `/feedback`, `/stats` |

Rule: A and B only talk through those two contracts, so neither blocks the other.

## Phases
**Phase 0, Foundations (week 1, together):** repo, branching (`main` protected, PRs reviewed by the other), agree on label taxonomy, find or build the dataset (`make data` gives a synthetic one), get CI green.

**Phase 1, Core (weeks 2-3)**
- A: real/richer dataset, train BERT (`make train`), tune threshold, expand regex rules, prompt-tune R1, report per-tier accuracy (`make eval`).
- B: API hardening (auth via API key header, request limits, structured logging), DB migrations (Alembic), dashboard polish, Docker compose end-to-end.

**Phase 2, Intelligence (weeks 4-5)**
- A: active learning loop: pull `/feedback/export`, retrain, compare against the previous model, only promote if better. Add few-shot examples to the R1 prompt from reviewed logs. Optional: fine-tune a small BERT instead of frozen embeddings; anomaly/novelty detection (embedding distance from known clusters) to flag brand-new log types.
- B: model versioning + hot reload endpoint, drift panel (label distribution over time), streaming ingestion (file tail / syslog / Kafka-lite via a queue), cost panel (LLM calls × price).

**Phase 3, Hardening & ship (week 6)**
- Load test (target: >200 logs/s on regex+BERT path), error budgets for LLM timeouts, README + architecture diagram, demo script, final report.

## Task board
- [ ] Label taxonomy agreed (A+B)
- [ ] Dataset v1 (A)  
- [ ] BERT trained, metrics saved (A)
- [ ] Regex coverage ≥ 40% of logs (A)
- [ ] R1 prompt + cache hit-rate measured (A)
- [ ] API key auth + rate limit (B)
- [ ] Alembic migrations (B)
- [ ] Dashboard: overview, review queue (B)
- [ ] Retrain-from-feedback script + promotion gate (A)
- [ ] Model versioning / reload (B)
- [ ] Streaming ingestion (B)
- [ ] Drift + novelty detection (A+B)
- [ ] Load test + docs + demo (A+B)

## Metrics that prove it works
1. Overall macro-F1 on a held-out set, and accuracy per tier.
2. % of logs resolved by regex / BERT / LLM (goal: LLM < 10%).
3. Avg latency per tier; LLM cache hit-rate.
4. Reviewed accuracy from the live feedback loop.

## Risks
- **Little real data:** use synthetic first, collect public logs (Loghub), then correct via the review queue.
- **R1 slow/expensive:** cache + threshold tuning + batch concurrency (`MAX_WORKERS`).
- **Label noise:** the review queue is the fix; agree taxonomy early.
