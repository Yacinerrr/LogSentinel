# LogSentinel

Hybrid log classification: **Regex → BERT embeddings → DeepSeek R1**, with API, dashboard, feedback loop.
See `docs/PLAN.md` for the team plan.

## Quick start
```bash
cp .env.example .env          # add DEEPSEEK_API_KEY, set API_KEYS (auth is on by default)
make install
make data && make train       # synthetic data + BERT head
make test
make api                      # http://localhost:8000/docs  (send X-API-Key header)
make dash                     # http://localhost:8501
```
Or: `docker compose up --build`

## Pipeline
`source in LLM_ONLY_SOURCES` → R1 · else regex → BERT (if conf ≥ `BERT_THRESHOLD`) → R1 · R1 results are cached by a normalized message key.

## Layout
```
app/classifiers/   regex, bert, llm, pipeline   (Dev A)
app/api/           FastAPI endpoints            (Dev B)
app/db.py          SQLAlchemy models + LLM cache
ml/                synthetic data, train, evaluate
dashboard/         Streamlit UI
tests/             pytest
```
