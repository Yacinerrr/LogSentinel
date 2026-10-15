import logging
import os
from .base import Prediction

log = logging.getLogger(__name__)


class BertClassifier:
    """Sentence-embedding model + sklearn head. Lazy-loaded; if the model file
    is missing it simply passes everything to the next tier."""

    def __init__(self, model_name: str, model_path: str, threshold: float):
        self.model_name, self.model_path, self.threshold = model_name, model_path, threshold
        self._embedder = None
        self._clf = None
        self._loaded = False

    def _load(self):
        self._loaded = True
        if not os.path.exists(self.model_path):
            log.warning("BERT head not found at %s; tier disabled", self.model_path)
            return
        import joblib
        from sentence_transformers import SentenceTransformer
        self._embedder = SentenceTransformer(self.model_name)
        self._clf = joblib.load(self.model_path)

    def predict(self, source: str, message: str) -> Prediction | None:
        if not self._loaded:
            self._load()
        if self._clf is None:
            return None
        probs = self._clf.predict_proba(self._embedder.encode([message]))[0]
        best = int(probs.argmax())
        if probs[best] < self.threshold:
            return None
        return Prediction(str(self._clf.classes_[best]), "bert", float(probs[best]))
