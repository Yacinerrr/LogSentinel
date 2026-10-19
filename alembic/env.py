import sys
from pathlib import Path

# The `alembic` command does not put the project root on sys.path (unlike `python -m ...`),
# so `import app` would fail. Add it explicitly so it works from any directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alembic import context
from sqlalchemy import engine_from_config, inspect, pool, text

from app.config import get_settings
from app.db import Base

config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    # URL set programmatically by app/migrations.py, else DATABASE_URL from .env (CLI use)
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        # render_as_batch: lets SQLite do ALTER TABLE changes (it can't natively)
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=True, compare_type=True)
        with context.begin_transaction():
            tables = set(inspect(connection).get_table_names())
            adopted = False
            if {"logs", "llm_cache"} <= tables:
                version = None
                if "alembic_version" in tables:
                    version = connection.execute(
                        text("select version_num from alembic_version limit 1")
                    ).scalar()
                if version is None:
                    # Adopt databases created before Alembic, including an interrupted
                    # first upgrade that left an empty version table.
                    if "alembic_version" not in tables:
                        connection.execute(text(
                            "create table alembic_version "
                            "(version_num varchar(32) not null)"
                        ))
                    connection.execute(
                        text("insert into alembic_version (version_num) values (:revision)"),
                        {"revision": "0001"},
                    )
                    connection.commit()
                    adopted = True
            if not adopted:
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()