from time import perf_counter
from app.config import Settings
from app.db import Database
from .base import Prediction
from .bert_clf import BertClassifier
from .llm_clf import LLMClassifier
from .regex_clf import RegexClassifier


class Pipeline:
    def __init__(self, regex, bert, llm, llm_only_sources: set[str]):
        self.regex, self.bert, self.llm = regex, bert, llm
        self.llm_only_sources = llm_only_sources

    def classify(self, source: str, message: str) -> Prediction:
        t0 = perf_counter()
        pred = None
        if source in self.llm_only_sources:
            pred = self.llm.predict(source, message)
        else:
            for tier in (self.regex, self.bert):
                pred = tier.predict(source, message)
                if pred:
                    break
            if pred is None:
                pred = self.llm.predict(source, message)
        pred.latency_ms = (perf_counter() - t0) * 1000
        return pred


def build_pipeline(s: Settings, db: Database) -> Pipeline:
    return Pipeline(
        RegexClassifier(s.regex_rules_path),
        BertClassifier(s.bert_model_name, s.bert_model_path, s.bert_threshold),
        LLMClassifier(s, db),
        s.llm_only_source_set,
    )
