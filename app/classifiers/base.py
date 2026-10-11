from dataclasses import dataclass
from typing import Protocol


@dataclass
class Prediction:
    label: str
    tier: str            # regex | bert | llm | fallback
    confidence: float
    latency_ms: float = 0.0


class Classifier(Protocol):
    """Contract between the ML side and the platform side.
    Return a Prediction, or None to pass the log to the next tier."""

    def predict(self, source: str, message: str) -> Prediction | None: ...
