import threading
import time

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.classifiers.base import Prediction
from app.classifiers.pipeline import Pipeline
from app.classifiers.regex_clf import RegexClassifier
from app.config import Settings
from app.db import Database
from tests.test_core import FakeLLM, Never, make_pipeline

H = {"X-API-Key": "k1"}


def make_client(tmp_path, pipeline=None, **kw):
    s = Settings(api_keys="k1,k2", jobs_dir=str(tmp_path / "jobs"), **kw)
    return TestClient(create_app(s, pipeline or make_pipeline(), Database("sqlite://")))


def csv_bytes(n, msg="User User{i} logged out."):
    return ("source,log_message\n" + "".join(f"ModernCRM,{msg.format(i=i)}\n" for i in range(n))).encode()


def post_job(c, data, headers=H):
    return c.post("/classify/csv/jobs", files={"file": ("t.csv", data, "text/csv")}, headers=headers)


def wait_done(c, job_id, headers=H, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = c.get(f"/jobs/{job_id}", headers=headers).json()
        if s["status"] in ("done", "failed"):
            return s
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_job_lifecycle_and_result(tmp_path):
    c = make_client(tmp_path, job_chunk_size=50)
    r = post_job(c, csv_bytes(230))
    assert r.status_code == 202 and r.json()["total"] == 230
    s = wait_done(c, r.json()["job_id"])
    assert s["status"] == "done" and s["processed"] == 230 and s["progress"] == 1.0
    res = c.get(f"/jobs/{r.json()['job_id']}/result", headers=H)
    lines = res.text.strip().splitlines()
    assert lines[0].startswith("source,log_message,target_label") and len(lines) == 231
    assert "User Action" in lines[1]
    assert c.get("/stats", headers=H).json()["total"] == 230       # everything was stored


def test_sync_endpoint_rejects_big_files_and_points_to_jobs(tmp_path):
    c = make_client(tmp_path, sync_csv_max_rows=10)
    r = c.post("/classify/csv", files={"file": ("t.csv", csv_bytes(11), "text/csv")}, headers=H)
    assert r.status_code == 413 and "/classify/csv/jobs" in r.json()["detail"]


def test_job_row_limit(tmp_path):
    c = make_client(tmp_path, max_csv_rows=5)
    assert post_job(c, csv_bytes(6)).status_code == 413


def test_empty_csv_is_rejected(tmp_path):
    c = make_client(tmp_path)
    assert post_job(c, b"source,log_message\n").status_code == 400


def test_other_api_key_cannot_see_job(tmp_path):
    c = make_client(tmp_path)
    job_id = post_job(c, csv_bytes(3)).json()["job_id"]
    wait_done(c, job_id)
    other = {"X-API-Key": "k2"}
    assert c.get(f"/jobs/{job_id}", headers=other).status_code == 404
    assert c.get(f"/jobs/{job_id}/result", headers=other).status_code == 404
    assert c.get("/jobs/doesnotexist", headers=H).status_code == 404


def test_jobs_require_auth(tmp_path):
    c = make_client(tmp_path)
    assert c.post("/classify/csv/jobs", files={"file": ("t.csv", csv_bytes(1), "text/csv")}).status_code == 401
    assert c.get("/jobs/x").status_code == 401


def test_too_many_running_jobs(tmp_path):
    c = make_client(tmp_path, max_running_jobs=0)
    r = post_job(c, csv_bytes(1))
    assert r.status_code == 429 and r.headers["Retry-After"] == "30"


class Blocking:
    """Tier that blocks until released, to observe a job while it is running."""
    def __init__(self):
        self.gate = threading.Event()

    def predict(self, source, message):
        self.gate.wait(10)
        return Prediction("System Notification", "bert", 0.9)


def test_result_before_done_is_409(tmp_path):
    blocker = Blocking()
    pipe = Pipeline(RegexClassifier("config/regex_rules.json"), blocker, FakeLLM(), set())
    c = make_client(tmp_path, pipe)
    job_id = post_job(c, csv_bytes(3, "unknown thing {i}")).json()["job_id"]
    time.sleep(0.2)
    assert c.get(f"/jobs/{job_id}", headers=H).json()["status"] == "running"
    assert c.get(f"/jobs/{job_id}/result", headers=H).status_code == 409
    blocker.gate.set()
    assert wait_done(c, job_id)["status"] == "done"
    assert c.get(f"/jobs/{job_id}/result", headers=H).status_code == 200


class Exploding:
    def predict(self, source, message):
        raise RuntimeError("secret internal detail")


def test_failed_job_does_not_leak_internals(tmp_path):
    pipe = Pipeline(RegexClassifier("config/regex_rules.json"), Exploding(), FakeLLM(), set())
    c = make_client(tmp_path, pipe)
    job_id = post_job(c, csv_bytes(2, "unknown {i}")).json()["job_id"]
    s = wait_done(c, job_id)
    assert s["status"] == "failed" and s["error"] == "internal error"
    assert "secret" not in str(s)
    assert c.get(f"/jobs/{job_id}/result", headers=H).status_code == 409


def test_old_jobs_are_cleaned_up(tmp_path):
    c = make_client(tmp_path, jobs_ttl_s=0)
    first = post_job(c, csv_bytes(2)).json()["job_id"]
    wait_done(c, first)
    time.sleep(0.05)
    post_job(c, csv_bytes(1))                  # creating a job triggers cleanup of expired ones
    assert c.get(f"/jobs/{first}", headers=H).status_code == 404
    assert not (tmp_path / "jobs" / f"{first}.csv").exists()


def test_formula_injection_neutralized_in_job_output(tmp_path):
    c = make_client(tmp_path)
    job_id = post_job(c, b'source,log_message\nA,"=cmd|\' /C calc\'!A0"\n').json()["job_id"]
    wait_done(c, job_id)
    assert "'=cmd" in c.get(f"/jobs/{job_id}/result", headers=H).text
