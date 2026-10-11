from fastapi.testclient import TestClient
from app.api.main import create_app
from app.classifiers.base import Prediction
from app.classifiers.llm_clf import parse_category
from app.classifiers.pipeline import Pipeline
from app.classifiers.regex_clf import RegexClassifier
from app.config import Settings
from app.db import Database
from app.text import normalize


class Never:
    def predict(self, source, message):
        return None


class FakeLLM:
    def predict(self, source, message):
        return Prediction("Workflow Error", "llm", 0.9)


def make_pipeline(llm=None):
    return Pipeline(RegexClassifier("config/regex_rules.json"), Never(), llm or FakeLLM(), {"LegacyCRM"})


def test_regex_hits():
    r = RegexClassifier("config/regex_rules.json")
    assert r.predict("x", "User User123 logged in.").label == "User Action"
    assert r.predict("x", "Failed password for root from 10.1.2.3 port 22 ssh2").label == "Security Alert"
    assert r.predict("x", "something totally unknown") is None


def test_routing():
    p = make_pipeline()
    assert p.classify("ModernCRM", "Backup completed successfully.").tier == "regex"
    assert p.classify("ModernCRM", "weird unseen message").tier == "llm"   # regex+bert miss -> llm
    assert p.classify("LegacyCRM", "Backup completed successfully.").tier == "llm"  # llm-only source


def test_parse_category():
    allowed = ["Workflow Error", "Deprecation Warning"]
    assert parse_category("<think>hmm</think><category>Workflow Error</category>", allowed) == "Workflow Error"
    assert parse_category("<category>Nonsense</category>", allowed) == "Unclassified"
    assert parse_category("no tags", allowed) == "Unclassified"


def test_normalize_shares_cache_key():
    assert normalize("Ticket 123 from 1.2.3.4") == normalize("Ticket 999 from 9.9.9.9")


def test_api_flow():
    db = Database("sqlite://")
    app = create_app(Settings(api_keys="k"), make_pipeline(), db)
    c = TestClient(app, headers={"X-API-Key": "k"})
    assert c.get("/health").json() == {"status": "ok"}
    r = c.post("/classify", json={"source": "ModernCRM", "log_message": "User User5 logged out."}).json()
    assert r["label"] == "User Action" and r["tier"] == "regex"
    c.post("/classify", json={"source": "ModernCRM", "log_message": "weird"})
    fb = c.post("/feedback", json={"log_id": r["id"], "correct_label": "System Notification"})
    assert fb.status_code == 200
    s = c.get("/stats").json()
    assert s["total"] == 2 and s["reviewed"] == 1 and s["reviewed_accuracy"] == 0.0
    assert "System Notification" in c.get("/feedback/export").text
    csv_bytes = b"source,log_message\nModernCRM,Backup completed successfully.\n"
    out = c.post("/classify/csv", files={"file": ("t.csv", csv_bytes, "text/csv")})
    assert out.status_code == 200 and "target_label" in out.text
    assert c.post("/classify/csv", files={"file": ("t.txt", b"x", "text/plain")}).status_code == 400
