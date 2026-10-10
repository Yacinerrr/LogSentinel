# Taxonomy Review: What to Tighten

Review of `docs/TAXONOMY.md`. The structure is strong (quick test per category, real examples, priority order, edge cases). The points below make it **consistent enough to train a model on and to use as an LLM prompt**. They are ordered by impact.

---

## 1. Close the open "à valider avec Dev B" items first

About a dozen decisions are still open, and some concern very frequent log lines, so they will change a large share of the dataset. Settle them in one 30-minute session and record them in a **Decision log** section at the end of `TAXONOMY.md` so they are never reopened silently.

Proposed defaults (accept or override each):

| # | Open question | Proposed decision | Why |
|---|---|---|---|
| 1 | `Unknown base file: ...` (OpenStack WARNING): `Error` or `System Notification`? | **System Notification** | Nothing failed or stopped. Putting it in `Error` dilutes that class with non-failures. Either choice is fine **if applied everywhere**. |
| 2 | Intermediate steps of an intrusion attempt (`check pass; user unknown`, `invalid user ... [preauth]`) | **Security Alert** | Each line is classified on its own meaning. Keep as written. |
| 3 | `Connection closed by X [preauth]`, `Received disconnect ... [preauth]` | **System Notification** | No failure or intrusion is stated in the line. Keep as written. |
| 4 | PAM `session opened/closed for user X` | **System Notification** (always) | A mechanical rule a model can learn. Do not try to distinguish service accounts from people. |
| 5 | `Accepted password/publickey for X` | **User Action** (always) | Same reason: mechanical. |
| 6 | `Attempting claim: memory 2048 MB ...` | **System Notification** | Requested, not measured. Keep, but see section 3. |
| 7 | Exact criterion for `Critical Error` | **Service stopped/unreachable, vital dependency unavailable (DB, system disk), data lost/corrupted, or kernel/OS fatal.** Words `CRITICAL`/`FATAL` alone do not qualify. | Gives a testable definition. |
| 8 | Failure that stops the whole service | **Critical Error** | Follows from #7. |
| 9 | Module failure that could be business or technical | **Error** (flag for review) | Safe default. |
| 10 | Action launched automatically by a named user (`Backup started by admin`) | **User Action** | The named author decides. |
| 11 | Truncated line | **Unclassified** only if the meaning is unreadable; otherwise classify the readable part | Keep as written. |
| 12 | Order of priority itself | Validate after fixing the wording in section 2 | |

Add the decision log at the bottom of `TAXONOMY.md`:

```markdown
## Decision log
| Date | Question | Decision | Decided by |
|---|---|---|---|
```

---

## 2. Fix the contradiction between the rule and the priority order

Current rule: *"the most **precise** category wins over the most general."*
But in the priority table `Error` (the generic failure bucket, rank 5) outranks `Resource Usage` (rank 6), which is more specific in meaning. So "precision" is not really what the order encodes. What it encodes is **severity**:

> **A failure or an intrusion beats a plain description.**
> Rank 1 is a format override; ranks 2-5 are failures; ranks 6-9 are descriptions; rank 10 is the fallback.

Suggested rewording of the reading rule:

> **Règle de lecture** : on applique l'ordre de haut en bas et on s'arrête à la première catégorie qui convient. Un échec ou une intrusion l'emporte sur une simple description (ex. : `No space left on device` est une `Error`, pas un `Resource Usage`).

Also group the table visually (format / failures / descriptions / fallback) so the logic is obvious.

---

## 3. Make boundaries depend on text, not on outside knowledge

A BERT model only sees the line. These rules require knowledge it does not have:

- **Service account vs real person** (`cyrus` vs `admin`): impossible to learn. Replace with the mechanical rules in the table above (#4 and #5).
- **`Attempting claim: memory 2048 MB`** (System Notification) vs **`Total memory: 64172 MB`** (Resource Usage): near-identical embeddings. Keep the distinction, but:
  - provide **many** examples of each (≥ 100 per class) in the dataset,
  - expect this pair in the confusion matrix, and consider a **regex rule** for `Attempting claim` so it never reaches BERT.

General test for every edge-case rule: *"Could someone label this correctly by reading only this one line?"* If not, rewrite the rule.

---

## 4. Keep `Unclassified` out of BERT training

- Do **not** train BERT on `Unclassified`. It becomes a junk class absorbing random lines and hides real confusion.
- Let **low confidence** route to the LLM, and let the LLM (or a human) produce `Unclassified`.
- Separate two meanings that currently look identical in the database:
  - *genuinely ambiguous line* → `Unclassified`
  - *pipeline failure (LLM down/timeout/garbled)* → `tier = fallback`

  Exclude every `tier = fallback` row from training and from reviewed-accuracy stats.

---

## 5. Measure whether the rules are learnable (inter-annotator agreement)

1. Randomly pick **100 lines**, stratified across sources.
2. Both of you label them **independently**, using only `TAXONOMY.md`.
3. Compute **Cohen's kappa**:
   ```python
   from sklearn.metrics import cohen_kappa_score
   cohen_kappa_score(labels_a, labels_b)
   ```
4. List every disagreement and fix the rule that caused it, then log it in the decision log.
5. Target kappa **≥ 0.8**. Below that, the model's ceiling is the labelers' disagreement.

Bonus: the kappa score and the "rules I fixed because of it" list make a strong section in the final report.

---

## 6. Replace synthetic examples with real ones

Marked `⚠️ synthétique` today: `User Action` (all of them except the guide line), `Critical Error` (all), `Unclassified` (all), parts of `Deprecation Warning` and `Workflow Error`.

- `Accepted password for ...` almost certainly exists in the Loghub **OpenSSH** logs; use the real line.
- Search Linux/Windows/OpenStack logs for `CRITICAL`, `FATAL`, `panic`, `down` for real `Critical Error` examples.
- Search for `deprecated` in application logs for real `Deprecation Warning` lines.
- Keep a `docs/EXAMPLES_TODO.md` listing which synthetic examples are still unreplaced.

---

## 7. Small structural improvements

- **Turn the quick tests into one decision tree.** Order the questions exactly like the priority table. The same tree becomes the **LLM prompt** (paste it in) and a labeling cheat-sheet:
  1. Contains HTTP method + path + response code? → `HTTP Status`
  2. Authentication failed / unknown user / break-in attempt? → `Security Alert`
  3. Service down, vital dependency unreachable, data lost? → `Critical Error`
  4. Business rule/process step failed? → `Workflow Error`
  5. Technical failure or exception, service still running? → `Error`
  6. Measured quantity of a machine resource, no failure? → `Resource Usage`
  7. Announces future removal/replacement? → `Deprecation Warning`
  8. Named user did something successfully? → `User Action`
  9. Normal system behavior? → `System Notification`
  10. Otherwise → `Unclassified`
- Add a **"Never decide on this alone"** table of misleading words (`ALERT`, `CRITICAL`, `HTTP`, `error`, `deprecated`, `Failed`) with one example each. You already say this in principle 3; a table makes it usable.
- State **multi-line logs** policy (stack traces): one line = one log, or merge first? Decide and write it down.
- Add a **version number and date** at the top of the file (`Taxonomy v1.0`) and bump it whenever a decision changes, so datasets can be tied to a version.

---

## 8. Code changes this review implies (not in the taxonomy file)

1. **HTTP regex too strict.** Current rule expects the status code right after `HTTP/1.1"`, but OpenStack lines have `status: 200` in between. Replace with:
   ```json
   {"pattern": "\"(GET|POST|PUT|DELETE|PATCH|HEAD) [^\"]+ HTTP/\\d\\.\\d\"\\s+(status:\\s*)?\\d{3}", "label": "HTTP Status"}
   ```
2. **LLM prompt only lists 2 categories.** It is also the fallback for uncertain logs from other sources, so it must receive the **full taxonomy + decision tree** (section 7) and be allowed to return any label.
3. **New regex rules** from your examples, ordered by priority: `Invalid user`, `authentication failure`, `POSSIBLE BREAK-IN ATTEMPT`, `Failed password`, `Attempting claim`, `session (opened|closed) for user`, `Accepted (password|publickey)`.
4. **`Unclassified` handling** in `train.py`: drop it and drop `tier = fallback` rows.

---

## Checklist before labeling starts

- [ ] All "à valider" items decided and in the decision log
- [ ] Reading rule reworded (severity, not precision)
- [ ] Edge-case rules rewritten to be line-only
- [ ] 100-line double-labeling done, kappa ≥ 0.8
- [ ] Synthetic examples tracked or replaced
- [ ] Decision tree added (also used as the LLM prompt)
- [ ] Taxonomy version number added
