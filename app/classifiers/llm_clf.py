import logging
import re
import time
from openai import OpenAI
from app.text import normalize
from .base import Prediction

log = logging.getLogger(__name__)

PROMPT = """You are a log classification engine.
Classify the log message into exactly one of these categories:
{cats}
If none fit, answer "Unclassified".
Reply with the category inside <category></category> tags and nothing after it.

Source: {source}
Log message: {log}"""


def parse_category(text: str, allowed: list[str]) -> str:
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.S)
    m = re.search(r"<category>(.*?)</category>", text, flags=re.S)
    label = m.group(1).strip() if m else "Unclassified"
    return label if label in allowed or label == "Unclassified" else "Unclassified"


class LLMClassifier:
    """DeepSeek R1 (OpenAI-compatible API) with a persistent cache."""

    def __init__(self, settings, db):
        self.s, self.db = settings, db
        self.categories = settings.llm_category_list
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = OpenAI(api_key=self.s.deepseek_api_key,
                                  base_url=self.s.deepseek_base_url,
                                  timeout=self.s.llm_timeout_s)
        return self._client

    def predict(self, source: str, message: str) -> Prediction:
        key = f"{source}|{normalize(message)}"
        cached = self.db.cache_get(key)
        if cached:
            return Prediction(cached, "llm", 0.9)
        if not self.s.deepseek_api_key:
            return Prediction("Unclassified", "fallback", 0.0)

        prompt = PROMPT.format(cats=", ".join(self.categories), source=source, log=message)
        for attempt in range(self.s.llm_retries + 1):
            try:
                resp = self.client.chat.completions.create(
                    model=self.s.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                )
                label = parse_category(resp.choices[0].message.content, self.categories)
                self.db.cache_set(key, label)
                return Prediction(label, "llm", 0.9)
            except Exception as e:  # network / rate limit
                log.warning("LLM call failed (%s), attempt %d", e, attempt + 1)
                time.sleep(2 ** attempt)
        return Prediction("Unclassified", "fallback", 0.0)
