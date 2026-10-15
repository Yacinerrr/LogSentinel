from datetime import datetime
from pydantic import BaseModel, Field


class LogIn(BaseModel):
    source: str = Field(..., examples=["ModernCRM"])
    log_message: str = Field(..., min_length=1, max_length=10_000)


class BatchIn(BaseModel):
    logs: list[LogIn] = Field(..., max_length=1000)


class PredictionOut(BaseModel):
    id: int | None = None
    source: str
    log_message: str
    label: str
    tier: str
    confidence: float
    latency_ms: float


class FeedbackIn(BaseModel):
    log_id: int
    correct_label: str


class LogRow(BaseModel):
    id: int
    source: str
    message: str
    label: str
    tier: str
    confidence: float
    reviewed_label: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
