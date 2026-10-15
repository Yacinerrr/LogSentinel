# Captain Checklist (Dev B)

## Day 1: repo setup (≈ 1 h)
1. Create the GitHub repo (private until the report is done). Push `logsentinel/`.
2. Add Dev A as collaborator (Write access).
3. Edit `.github/CODEOWNERS`: replace `@dev-a` / `@dev-b` with the two real usernames (both on the one `*` line).
4. **Branch protection on `main`** (Settings → Branches → Add rule):
   - Require a pull request before merging, **1 approval**
   - Require review from Code Owners
   - Require status checks to pass → select the `test` job (it only appears in the list **after CI has run once**: push a commit first)
   - Dismiss stale approvals on new commits
   - Block force pushes
5. Run `scripts/bootstrap_github.sh` (labels + milestones + 29 issues).
6. Create a GitHub **Project** (board view): columns `Todo / In progress / In review / Done`; add all issues.
7. Secrets: **never commit `.env`**. Each person generates their own `DEEPSEEK_API_KEY`. Enable GitHub secret scanning and push protection (Settings → Code security).

## Kickoff meeting (45 min, with Dev A)
1. Confirm roles and file ownership (`docs/TASKS.md` §1). 5 min
2. **Resolve the open taxonomy items** and fill the decision log (`docs/TAXONOMY_REVIEW.md` §1). 25 min
3. Agree meeting rhythm: Monday plan (20 min), Thursday blockers + demo (20 min). 5 min
4. Cross-training hour: schedule it. 5 min
5. Who writes what in week 1 (A0.1-A0.3 vs B0.1-B0.2). 5 min

## Captain duties each week
- Monday: move issues to *In progress*, confirm the week's goals.
- Thursday: demo what works, update the board, flag slippage using the "cut first" list in `TASKS.md` §4.
- Friday: `main` must be green and deployable (`docker compose up`).
- Keep `docs/RESULTS.md` updated with the latest numbers.

## Local dev quick reference
```bash
cp .env.example .env     # set DEEPSEEK_API_KEY and API_KEYS
make install && make test
make api                 # uses auth: send header  X-API-Key: <one of API_KEYS>
curl -H "X-API-Key: change-me-dev-key" localhost:8000/stats
```
