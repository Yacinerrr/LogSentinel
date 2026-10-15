import json
import re
from .base import Prediction


class RegexClassifier:
    def __init__(self, rules_path: str):
        with open(rules_path, encoding="utf-8") as f:
            rules = json.load(f)
        self.rules = [(re.compile(r["pattern"], re.I), r["label"]) for r in rules]

    def predict(self, source: str, message: str) -> Prediction | None:
        for pattern, label in self.rules:
            if pattern.search(message):
                return Prediction(label, "regex", 1.0)
        return None
