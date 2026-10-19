# Database migrations (Alembic)

The database schema is defined by the models in `app/db.py` and **versioned by migrations** in `alembic/versions/`.
The API applies pending migrations automatically at startup, so `uvicorn` and `docker compose up` always give you an up-to-date DB.

## Changing a table (the only correct way)
1. Edit the model in `app/db.py` (e.g. add a column).
2. Generate the migration (activate `.venv` first):
   ```bash
   alembic revision --autogenerate -m "add notes to logs"
   ```
   (uses `DATABASE_URL` from `.env`; run `alembic upgrade head` once before so the DB is current)
3. **Open the new file in `alembic/versions/` and read it.** Autogenerate is a draft, not magic.
4. `python -m pytest -q`. `test_no_schema_drift...` fails if the model and the migrations disagree.
5. Commit the model change **and** the migration file in the same PR.

## Rules
- **Never edit a migration that is already merged to `main`.** Add a new one.
- Never edit `LEGACY_SCHEMA` in `tests/test_migrations.py`: it is the frozen pre-Alembic schema.
- Adding a NOT NULL column to a table with data? Give it a `server_default` in the migration.
- One PR that changes the schema → tell the teammate (it changes their local DB on next run).

## Useful commands
| Command | Meaning |
|---|---|
| `alembic upgrade head` | Apply all pending migrations |
| `alembic current` | Which version is this DB at? |
| `alembic history` | List all migrations |
| `alembic downgrade -1` | Undo the last migration (local DBs only) |
| `alembic upgrade head --sql` | Print the SQL instead of running it |

## Existing databases
A database created before Alembic existed (it has the legacy `logs` and `llm_cache` tables but no `alembic_version`) is adopted automatically by both the app and the Alembic CLI: it is recorded at `0001` without recreating tables or touching data. An empty `alembic_version` left by an interrupted first upgrade is handled the same way.

## Limits (known)
Migrations run at app startup. With several API workers starting at once they could race; we run one worker today. If we scale out, run `alembic upgrade head` as a separate step before starting the workers.
