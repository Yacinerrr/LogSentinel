import pytest
from fastapi.testclient import TestClient
from app.api.main import create_app
from app.config import Settings
from app.db import Database
from tests.test_core import make_pipeline


def client(**kw):
    s = Settings(api_keys="good-key", **kw)
    return TestClient(create_app(s, make_pipeline(), Database("sqlite://")))


def test_auth_required():
    c = client()
    assert c.get("/health").status_code == 200                      # liveness stays open
    assert c.get("/stats").status_code == 401                        # no key
    assert c.get("/stats", headers={"X-API-Key": "nope"}).status_code == 401
    assert c.get("/stats", headers={"X-API-Key": "good-key"}).status_code == 200


def test_fails_closed_without_keys():
    with pytest.raises(RuntimeError):
        create_app(Settings(api_keys=""), make_pipeline(), Database("sqlite://"))


def test_rate_limit():
    c = client(rate_limit_per_min=3)
    h = {"X-API-Key": "good-key"}
    assert [c.get("/stats", headers=h).status_code for _ in range(3)] == [200, 200, 200]
    r = c.get("/stats", headers=h)
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1
    assert c.get("/health").status_code == 200                       # health not limited


def test_size_limits():
    c = client(max_csv_bytes=100)
    h = {"X-API-Key": "good-key"}
    big = {"source": "a", "log_message": "x" * 10_001}
    assert c.post("/classify", json=big, headers=h).status_code == 422
    csv_big = b"source,log_message\n" + b"a,hello world\n" * 20
    assert c.post("/classify/csv", files={"file": ("t.csv", csv_big, "text/csv")}, headers=h).status_code == 413


def test_request_id_is_sanitized():
    c = client()
    assert c.get("/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"
    bad = c.get("/health", headers={"X-Request-ID": "a b;{fake}"}).headers["X-Request-ID"]
    assert bad != "a b;{fake}" and len(bad) == 12


def test_csv_formula_injection_neutralized():
    c = client()
    h = {"X-API-Key": "good-key"}
    payload = b'source,log_message\nModernCRM,"=HYPERLINK(""http://evil"",""x"")"\n'
    out = c.post("/classify/csv", files={"file": ("t.csv", payload, "text/csv")}, headers=h)
    assert out.status_code == 200
    assert "'=HYPERLINK" in out.text


def test_bad_csv_rows_and_encoding():
    c = client()
    h = {"X-API-Key": "good-key"}
    assert c.post("/classify/csv", files={"file": ("t.csv", b"source,log_message\nA,\n", "text/csv")}, headers=h).status_code == 400
    assert c.post("/classify/csv", files={"file": ("t.csv", b"\xff\xfe\x00", "text/csv")}, headers=h).status_code == 400
