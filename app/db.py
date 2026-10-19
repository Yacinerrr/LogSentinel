import os
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


def _now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class LogRecord(Base):
    __tablename__ = "logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(100), index=True)
    message: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(String(100), index=True)
    tier: Mapped[str] = mapped_column(String(20), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    reviewed_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LLMCache(Base):
    __tablename__ = "llm_cache"
    key: Mapped[str] = mapped_column(String(600), primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Database:
    def __init__(self, url: str, migrate: bool = True):
        kwargs = {}
        in_memory = url in ("sqlite://", "sqlite:///:memory:")
        if url.startswith("sqlite"):
            kwargs["connect_args"] = {"check_same_thread": False}
            if url in ("sqlite://", "sqlite:///:memory:"):
                kwargs["poolclass"] = StaticPool
            else:
                path = url.replace("sqlite:///", "", 1)
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.engine = create_engine(url, **kwargs)
        if in_memory or not migrate:
            Base.metadata.create_all(self.engine)   # throwaway DBs (tests)
        else:
            from app.migrations import run_migrations  # real DBs: schema comes from Alembic
            run_migrations(self.engine, url)
        self.Session = sessionmaker(self.engine, expire_on_commit=False)

    # --- LLM cache (cuts repeated R1 calls) ---
    def cache_get(self, key: str) -> str | None:
        with self.Session() as s:
            row = s.get(LLMCache, key)
            return row.label if row else None

    def cache_set(self, key: str, label: str) -> None:
        with self.Session() as s:
            s.merge(LLMCache(key=key[:600], label=label))
            s.commit()
