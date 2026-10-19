import sqlite3
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.db import Base, Database, LogRecord
from app.migrations import alembic_config


def head_revision(url):
    return ScriptDirectory.from_config(alembic_config(url)).get_current_head()


def url_for(tmp_path, name="t.db"):
    return f"sqlite:///{(tmp_path / name).as_posix()}"


def test_fresh_db_is_created_by_migrations(tmp_path):
    url = url_for(tmp_path)
    db = Database(url)
    insp = inspect(db.engine)
    assert {"logs", "llm_cache", "alembic_version"} <= set(insp.get_table_names())
    with db.engine.connect() as c:
        assert c.execute(text("select version_num from alembic_version")).scalar() == head_revision(url)
    # indexes from the models exist
    assert {"ix_logs_source", "ix_logs_label", "ix_logs_tier"} <= {i["name"] for i in insp.get_indexes("logs")}


def test_startup_is_idempotent(tmp_path):
    url = url_for(tmp_path)
    Database(url)
    Database(url)   # second start must not fail or duplicate anything


LEGACY_SCHEMA = """
CREATE TABLE logs (id INTEGER PRIMARY KEY, source VARCHAR(100) NOT NULL, message TEXT NOT NULL,
  label VARCHAR(100) NOT NULL, tier VARCHAR(20) NOT NULL, confidence FLOAT NOT NULL,
  latency_ms FLOAT NOT NULL, reviewed_label VARCHAR(100), created_at DATETIME NOT NULL);
CREATE INDEX ix_logs_source ON logs (source);
CREATE INDEX ix_logs_label ON logs (label);
CREATE INDEX ix_logs_tier ON logs (tier);
CREATE TABLE llm_cache (key VARCHAR(600) PRIMARY KEY, label VARCHAR(100) NOT NULL, created_at DATETIME NOT NULL);
"""   # frozen copy of the schema as it was before Alembic: must never change


def test_legacy_db_without_alembic_is_adopted_and_keeps_data(tmp_path):
    url = url_for(tmp_path)
    con = sqlite3.connect(tmp_path / "t.db")
    con.executescript(LEGACY_SCHEMA)
    con.execute("insert into logs (source,message,label,tier,confidence,latency_ms,created_at) "
                "values ('S','m','L','regex',1.0,0.1,'2026-01-01 00:00:00')")
    con.commit()
    con.close()

    db = Database(url)                          # adopts (stamps 0001) then upgrades to head
    with db.engine.connect() as c:
        assert c.execute(text("select count(*) from logs")).scalar() == 1
        assert c.execute(text("select version_num from alembic_version")).scalar() == head_revision(url)


def test_no_schema_drift_between_models_and_migrations(tmp_path):
    """Fails if someone changes app/db.py without adding a migration."""
    url = url_for(tmp_path)
    Database(url)
    command.check(alembic_config(url))          # raises if models != migrated schema


def test_downgrade_then_upgrade(tmp_path):
    url = url_for(tmp_path)
    Database(url)
    cfg = alembic_config(url)
    command.downgrade(cfg, "base")
    assert not {"logs", "llm_cache"} & set(inspect(create_engine(url)).get_table_names())
    command.upgrade(cfg, "head")
    assert "logs" in inspect(create_engine(url)).get_table_names()
