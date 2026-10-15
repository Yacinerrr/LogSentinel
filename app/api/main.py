import csv
import io
import logging
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import ValidationError
from sqlalchemy import func, select

from app.classifiers.pipeline import build_pipeline
from app.config import get_settings
from app.db import Database, LogRecord
from app.logging_config import setup_logging
from app.schemas import BatchIn, FeedbackIn, LogIn, LogRow, PredictionOut
from app.security import RateLimiter, csv_safe, make_auth_dependency

log = logging.getLogger("logsentinel.access")
_REQ_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")  # untrusted header: reject anything else (log injection)


def create_app(settings=None, pipeline=None, db=None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_json)
    if settings.auth_enabled and not settings.api_key_list:
        raise RuntimeError("AUTH_ENABLED is true but API_KEYS is empty. Set API_KEYS in .env (comma-separated).")
    db = db or Database(settings.database_url)
    pipeline = pipeline or build_pipeline(settings, db)
    limiter = RateLimiter(settings.rate_limit_per_min)
    auth = make_auth_dependency(settings, limiter)

    app = FastAPI(title="LogSentinel", version="1.1.0")
    api = APIRouter(dependencies=[Depends(auth)])

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")
        rid = rid if _REQ_ID.match(rid) else uuid.uuid4().hex[:12]
        request.state.request_id = rid
        t0 = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = rid
            return response
        finally:  # never log message bodies: logs may contain secrets
            log.info("request", extra={
                "request_id": rid, "method": request.method, "path": request.url.path, "status": status,
                "duration_ms": round((time.perf_counter() - t0) * 1000, 1),
                "key_id": getattr(request.state, "key_id", None)})

    def run(items: list[LogIn]) -> list[PredictionOut]:
        with ThreadPoolExecutor(max_workers=settings.max_workers) as ex:
            preds = list(ex.map(lambda i: pipeline.classify(i.source, i.log_message), items))
        out = []
        with db.Session() as s:
            for item, p in zip(items, preds):
                rec = LogRecord(source=item.source, message=item.log_message, label=p.label,
                                tier=p.tier, confidence=p.confidence, latency_ms=p.latency_ms)
                s.add(rec)
                s.flush()
                out.append(PredictionOut(id=rec.id, source=item.source, log_message=item.log_message,
                                         label=p.label, tier=p.tier, confidence=p.confidence,
                                         latency_ms=p.latency_ms))
            s.commit()
        return out

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @api.post("/classify", response_model=PredictionOut)
    def classify(log_in: LogIn):
        return run([log_in])[0]

    @api.post("/classify/batch", response_model=list[PredictionOut])
    def classify_batch(batch: BatchIn):
        return run(batch.logs)

    @api.post("/classify/csv")
    async def classify_csv(file: UploadFile = File(...)):
        if not (file.filename or "").endswith(".csv"):
            raise HTTPException(400, "File must be a CSV")
        data = await file.read(settings.max_csv_bytes + 1)
        if len(data) > settings.max_csv_bytes:
            raise HTTPException(413, f"CSV larger than {settings.max_csv_bytes} bytes")
        try:
            reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")))
            if not reader.fieldnames or not {"source", "log_message"} <= set(reader.fieldnames):
                raise HTTPException(400, "CSV needs 'source' and 'log_message' columns")
            items = [LogIn(source=r["source"], log_message=r["log_message"]) for r in reader]
        except UnicodeDecodeError:
            raise HTTPException(400, "CSV must be UTF-8")
        except ValidationError as e:
            raise HTTPException(400, f"Invalid row: {e.errors()[0]['msg']}")
        results = run(items)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["source", "log_message", "target_label", "tier", "confidence"])
        for r in results:  # csv_safe: output is meant to be opened in Excel
            w.writerow([csv_safe(r.source), csv_safe(r.log_message), r.label, r.tier, round(r.confidence, 3)])
        buf.seek(0)
        return StreamingResponse(buf, media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=classified.csv"})

    @api.get("/logs", response_model=list[LogRow])
    def list_logs(label: str | None = None, tier: str | None = None,
                  max_confidence: float | None = None, unreviewed: bool = False, limit: int = 100):
        q = select(LogRecord).order_by(LogRecord.id.desc()).limit(max(1, min(limit, 1000)))
        if label:
            q = q.where(LogRecord.label == label)
        if tier:
            q = q.where(LogRecord.tier == tier)
        if max_confidence is not None:
            q = q.where(LogRecord.confidence <= max_confidence)
        if unreviewed:
            q = q.where(LogRecord.reviewed_label.is_(None))
        with db.Session() as s:
            return s.scalars(q).all()

    @api.post("/feedback")
    def feedback(fb: FeedbackIn):
        with db.Session() as s:
            rec = s.get(LogRecord, fb.log_id)
            if not rec:
                raise HTTPException(404, "Log not found")
            rec.reviewed_label = fb.correct_label
            s.commit()
        return {"ok": True}

    @api.get("/feedback/export", response_class=PlainTextResponse)
    def export_feedback():
        """Raw (unsanitized) training CSV for ml/train.py. Not meant to be opened in Excel."""
        with db.Session() as s:
            rows = s.scalars(select(LogRecord).where(LogRecord.reviewed_label.is_not(None))).all()
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["source", "log_message", "target_label"])
        for r in rows:
            w.writerow([r.source, r.message, r.reviewed_label])
        return buf.getvalue()

    @api.get("/stats")
    def stats():
        with db.Session() as s:
            total = s.scalar(select(func.count(LogRecord.id))) or 0
            by_tier = dict(s.execute(select(LogRecord.tier, func.count()).group_by(LogRecord.tier)).all())
            by_label = dict(s.execute(select(LogRecord.label, func.count()).group_by(LogRecord.label)).all())
            avg_lat = dict(s.execute(select(LogRecord.tier, func.avg(LogRecord.latency_ms))
                                     .group_by(LogRecord.tier)).all())
            reviewed = s.scalar(select(func.count(LogRecord.id)).where(LogRecord.reviewed_label.is_not(None))) or 0
            wrong = s.scalar(select(func.count(LogRecord.id)).where(
                LogRecord.reviewed_label.is_not(None), LogRecord.reviewed_label != LogRecord.label)) or 0
        return {
            "total": total, "by_tier": by_tier, "by_label": by_label,
            "avg_latency_ms": {k: round(v or 0, 2) for k, v in avg_lat.items()},
            "llm_share": round(by_tier.get("llm", 0) / total, 3) if total else 0,
            "reviewed": reviewed,
            "reviewed_accuracy": round(1 - wrong / reviewed, 3) if reviewed else None,
        }

    app.include_router(api)
    return app
