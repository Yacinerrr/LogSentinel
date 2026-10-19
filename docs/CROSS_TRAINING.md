# Shared tasks (S-tasks): how to do them

Shared tasks are done **together**. They keep both of you able to explain and fix the whole project.

---

## S0.1: Kickoff + first cross-training hour (week 1, ~1 h)

**Done when:** both sync meetings are in both calendars, the taxonomy decision log is filled, and each of you can explain the other half in 2 minutes.

### Agenda (60 min)
| Min | What | Output |
|---|---|---|
| 0-5 | Show the board. Confirm who is Dev A / Dev B. | Assignees match the labels |
| 5-30 | **Taxonomy decisions** from `docs/TAXONOMY_REVIEW.md` §1: go through every "à valider" row, decide, write each in the Decision log | Decision log in `TAXONOMY.md` (PR) |
| 30-40 | **Dev B explains the platform** (10 min): request → auth → pipeline → DB → dashboard. Open `app/api/main.py` live. | Dev A can say what `/classify` does |
| 40-50 | **Dev A explains the ML side** (10 min): regex → BERT → LLM, why a threshold, why a frozen test set. Open `app/classifiers/pipeline.py` live. | Dev B can say why a log goes to the LLM |
| 50-55 | Confirm the 4 handoff points H1-H4 (`docs/TASKS.md` §1) and their dates | Dates written on the issues |
| 55-60 | Create the recurring invites: **Monday 20 min** (plan), **Thursday 20 min** (demo + blockers) | Calendar invites |

### After the meeting
- Close issue S0.1 with a comment listing the decisions and the meeting times.

---

## Weekly cross-training hour (every week, 30-45 min, rotate the teacher)

Each week one person teaches one concept from their half **using the real code**. The learner asks questions and must be able to repeat it back.

| Week | Teacher | Topic | Learner proves it by |
|---|---|---|---|
| 1 | A | How a log travels through the 3 tiers | Drawing the flow from memory |
| 2 | B | Auth, rate limiting, and why the CSV output is sanitized | Explaining what a 401 vs 429 means here |
| 3 | A | Precision/recall/F1, the confusion matrix, why the test set is frozen | Reading `ml.evaluate` output and naming the weakest label |
| 4 | B | Migrations and the DB: how to add a column safely | Adding a harmless column in a throwaway branch |
| 5 | A | Feedback loop: export → retrain → promotion gate | Explaining when a new model is rejected |
| 6 | B | Docker, deployment, logs/requests tracing | Starting the stack from a clean clone, unaided |

---

## S3.2: Cross-review bug fix (week 6, ~3 h)

**Goal:** each of you fixes a real bug in the *other* person's half. This proves the project is not "two separate projects".

How:
1. Each person makes a list of 3 small, real issues in their **own** half (a missing test, a confusing function, a rough error message). Create them as issues labeled `good-first-fix`.
2. Swap: Dev A picks one from B's list, Dev B picks one from A's list.
3. Fix it with the normal workflow: branch → PR → the **owner** of that code reviews.
4. In the PR description write what you learned.

**Done when:** two merged PRs, each author fixing the other's area.

---

## S3.1: Demo script + final report (week 6, ~6 h)

Start the outline early (week 4). Skeleton:

**Demo (10 min)**
1. Problem in one sentence + one messy log example (1 min)
2. Architecture diagram: 3 tiers (2 min)
3. Live: classify a regex-resolved log, a BERT-resolved log, an LLM-resolved log; show `tier` and latency (3 min)
4. Dashboard: stats, LLM share, review queue; correct a label (2 min)
5. Retrain from feedback; show the promotion gate result (1 min)
6. Results table + what we'd do next (1 min)

**Report outline:** problem · taxonomy · data · architecture · per-tier results · error analysis (worst 20) · security decisions · team workflow · limits · future work.

**Rule:** each person presents **their own half** and answers one question about the other half.

**Done when:** a full dry run was done once, with a timer.
