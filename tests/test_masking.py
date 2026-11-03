import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.classifiers.llm_clf as llm_module
from app.api.main import create_app
from app.classifiers.llm_clf import LLMClassifier
from app.classifiers.pipeline import Pipeline
from app.config import Settings
from app.db import Database, LLMCache
from app.masking import mask
from tests.test_core import Never

# ---------- unit: what gets masked ----------

CASES = [
    ("email", "login by alice.martin@example.com failed", "alice.martin@example.com", "<EMAIL>"),
    ("password kv", "connect failed password=Hunter2!xyz retry", "Hunter2!xyz", "password=<SECRET>"),
    ("json password", '{"user":"a","password": "p4ss w0rd"}', "p4ss w0rd", "<SECRET>"),
    ("api_key kv", "api_key: abcDEF123456", "abcDEF123456", "api_key: <SECRET>"),
    ("bearer", "Authorization: Bearer abcdefgh12345678", "abcdefgh12345678", "<TOKEN>"),
    ("jwt", "token eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.SflKxwRJSMeKKF2QT4fwpM", "eyJhbGciOiJIUzI1NiJ9", "<JWT>"),
    ("aws key", "key AKIAIOSFODNN7EXAMPLE used", "AKIAIOSFODNN7EXAMPLE", "<API_KEY>"),
    ("openai-style key", "using sk-proj-abcdefghijklmnopqrstuvwx", "sk-proj-abcdefghijklmnopqrstuvwx", "<API_KEY>"),
    ("github token", "push with ghp_" + "a1B2c3D4e5" * 4, "ghp_a1B2", "<API_KEY>"),
    ("url credentials", "db at postgres://admin:s3cr3t@db.internal:5432/app", "s3cr3t", "postgres://<CREDENTIALS>@db.internal"),
    ("valid card", "payment card 4111 1111 1111 1111 declined", "4111 1111 1111 1111", "<CARD>"),
    ("amex test card", "card 3782 822463 10005 expired", "3782 822463 10005", "<CARD>"),
    ("mastercard test card", "charge 5500000000000004 failed", "5500000000000004", "<CARD>"),
    ("intl phone", "call +213 555 12 34 56 now", "555 12 34 56", "<PHONE>"),
    ("dz mobile", "sms to 0555 12 34 56 sent", "0555 12 34 56", "<PHONE>"),
    ("ip", "Failed from 192.168.1.77 port 22", "192.168.1.77", "<IP>"),
    ("ssh user", "Failed password for root from 10.0.0.5 port 22 ssh2", "for root", "Failed password for <USER> from <IP>"),
    ("invalid user", "Invalid user webmaster from 173.234.31.186", "webmaster", "Invalid user <USER> from <IP>"),
    ("pam user", "session opened for user cyrus by (uid=0)", "cyrus", "session opened for user <USER>"),
    ("kv user", "authentication failure; ruser= rhost=x user=alice", "alice", "user=<USER>"),
    ("rhost with embedded ip", "authentication failure; rhost=5.36.59.76.dynamic-dsl-ip.omantel.net.om  user=root", "omantel", "rhost=<HOST>"),
    ("rhost dashed ip", "authentication failure; ruser= rhost=220-135-151-1.hinet-ip.hinet.net  user=root", "hinet", "rhost=<HOST>"),
    ("ip with hostname in parens", "connection from 24.54.76.216 (24-54-76-216.bflony.adelphia.net) at Sat", "adelphia", "<IP> (<HOST>)"),
    ("hex token", "tenant 54fadb412c4e40cdbaed9335e4c35a9e created", "54fadb412c4e40cdbaed9335e4c35a9e", "<TOKEN>"),
]


@pytest.mark.parametrize("name,text,secret,expected", CASES, ids=[c[0] for c in CASES])
def test_masks(name, text, secret, expected):
    r = mask(text)
    assert secret not in r.text, r.text
    assert expected in r.text, r.text
    assert r.changed and r.counts


def test_private_key_complete_and_truncated():
    body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC"
    full = f"-----BEGIN PRIVATE KEY-----\n{body}\n-----END PRIVATE KEY----- trailing"
    assert body not in mask(full).text and "trailing" in mask(full).text
    cut = f"oops -----BEGIN RSA PRIVATE KEY-----\n{body}\nmore"          # log line cut before END
    assert body not in mask(cut).text


@pytest.mark.parametrize("text", [
    "Backup completed successfully.",
    "System updated to version 4.0",
    'GET /v2/servers/detail HTTP/1.1" status: 200 len: 1874 time: 0.2106130',
    "req-a0893d5a-dc60-4c49-82e5-b9f7dfc2f6ab Took 1.05 seconds to destroy the instance",
    "Total memory: 64172 MB, used: 512.00 MB",
    "Escalation rule failed for ticket ID 71234: undefined assignee",
    "User User123 logged in.",
    "invoice 1234 5678 9012 3456 paid",            # 16 digits but fails Luhn: not a card
    "check pass; user unknown",
    "BIOS-e820: 0000000000000000 - 00000000000a0000 (usable)",      # real Loghub line: all zeros passes Luhn
    "BIOS-e820: 0000000000100000 - 000000007fff0000 (usable)",
    "timestamp 1478114573123456 recorded",                           # starts with 1: not a card network
])
def test_normal_logs_are_untouched(text):
    r = mask(text)
    assert r.text == text and not r.changed


def test_flags_can_keep_ips_and_usernames():
    t = "Failed password for root from 10.0.0.5 port 22 ssh2"
    r = mask(t, ips=False, usernames=False)
    assert r.text == t


def test_counts_never_contain_values():
    r = mask("password=Zq9!secretvalue from 10.1.2.3")
    assert "secretvalue" not in str(r.counts) and set(r.counts) == {"secret_value", "ip"}


def test_idempotent():
    once = mask("user=alice password=abc123xyz ip 1.2.3.4").text
    assert mask(once).text == once


def test_hostile_inputs_are_fast():
    nasty = ["a" * 50_000, "password=" * 5_000, "1 " * 20_000, "-----BEGIN PRIVATE KEY-----" + "x" * 50_000,
             "user=" * 10_000, "<IP> (" * 10_000, "<IP> (" + "a." * 20_000, "rhost=" * 10_000, ("1." * 3) * 10_000, "a1" * 30_000, "(" * 20_000]
    for s in nasty:
        t0 = time.time()
        mask(s)
        assert time.time() - t0 < 1.0, f"slow on {s[:20]!r}"


# ---------- integration: what the LLM actually receives ----------

class FakeClient:
    def __init__(self):
        self.prompts = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, model, messages):
        self.prompts.append(messages[0]["content"])
        content = "<category>Workflow Error</category>"
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def make_llm(**kw):
    s = Settings(api_keys="k", deepseek_api_key="test-key", **kw)
    db = Database("sqlite://")
    llm = LLMClassifier(s, db)
    llm._client = FakeClient()
    return llm, db


SECRET_LOG = ("Escalation failed for ticket 9 user=alice password=Hunter2!xyz email bob@corp.com "
              "from 10.20.30.40 Bearer abcdefgh12345678")
SECRETS = ["alice", "Hunter2!xyz", "bob@corp.com", "10.20.30.40", "abcdefgh12345678"]


def test_secrets_never_reach_the_llm_prompt_or_cache():
    llm, db = make_llm()
    pred = llm.predict("LegacyCRM", SECRET_LOG)
    assert pred.label == "Workflow Error"
    prompt = llm._client.prompts[0]
    for secret in SECRETS:
        assert secret not in prompt, secret
    assert "Escalation failed for ticket" in prompt              # the useful part is still there
    with db.Session() as s:
        keys = s.scalars(select(LLMCache.key)).all()
    assert keys and not any(sec in k for k in keys for sec in SECRETS)


def test_cache_hit_avoids_second_call_even_with_different_secrets():
    llm, _ = make_llm()
    llm.predict("LegacyCRM", "Rule failed user=alice password=aaaaaaa1")
    llm.predict("LegacyCRM", "Rule failed user=bobby password=bbbbbbb2")
    assert len(llm._client.prompts) == 1                         # same masked text -> one paid call


def test_fail_closed_when_masking_crashes(monkeypatch):
    llm, _ = make_llm()
    monkeypatch.setattr(llm_module, "mask", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    pred = llm.predict("LegacyCRM", SECRET_LOG)
    assert pred.tier == "fallback" and pred.label == "Unclassified"
    assert llm._client.prompts == []                             # nothing was sent


def test_truncation_happens_after_masking():
    """An email straddling the cut: if we truncated first, 'bob@corp' (no TLD) would escape the email rule."""
    llm, _ = make_llm(llm_max_chars=58)
    llm.predict("LegacyCRM", "x" * 50 + " bob@corp.com and more text after")
    prompt = llm._client.prompts[0]
    assert "bob" not in prompt and "<EMAIL>" in prompt


def test_end_to_end_through_the_api():
    """The 'Done when' of B1.4: post a log with secrets to the real endpoint, inspect what the LLM saw."""
    llm, db = make_llm()
    pipe = Pipeline(Never(), Never(), llm, set())
    c = TestClient(create_app(Settings(api_keys="k"), pipe, db))
    r = c.post("/classify", json={"source": "ModernCRM", "log_message": SECRET_LOG}, headers={"X-API-Key": "k"})
    assert r.status_code == 200 and r.json()["tier"] == "llm"
    for secret in SECRETS:
        assert secret not in llm._client.prompts[0]
