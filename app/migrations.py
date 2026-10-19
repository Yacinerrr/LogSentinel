"""Run Alembic migrations from application code (so `docker compose up` and `uvicorn` just work)."""
from pathlib import Path

from alembic import command
from alembic.config import Config


ROOT = Path(__file__).resolve().parent.parent
BASELINE = "0001"


def alembic_config(url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))  # configparser escaping
    return cfg


def run_migrations(engine, url: str) -> None:
    # Legacy databases are adopted by the Alembic environment before upgrading.
    command.upgrade(alembic_config(url), "head")
