"""Mask secrets and personal data BEFORE a log line leaves the machine (LLM tier only).

Design rules:
- Mask first, then truncate, then send. The raw message never goes to the LLM or into the LLM cache key.
- Fail closed: if masking raises, the LLM is not called (see LLMClassifier).
- Best effort, not a guarantee: see docs/PRIVACY.md for what is NOT covered.
- Every pattern is linear-time: no nested quantifiers, and patterns that scan a run of characters start only at
  the beginning of that run (lookbehind), otherwise each start would rescan the whole run (quadratic).
  tests/test_masking.py::test_hostile_inputs_are_fast guards this.
"""
import re
from dataclasses import dataclass, field


@dataclass
class MaskResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)   # kind -> how many hits (never the values)

    @property
    def changed(self) -> bool:
        return bool(self.counts)


_PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----|.*\Z)", re.S)
_URL_CREDS = re.compile(r"(?<![A-Za-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/@:]+:[^\s/@]+@", re.I)
_JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b")
_API_KEY = re.compile(
    r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b|\bsk-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{30,}"
    r"|\bgithub_pat_[A-Za-z0-9_]{20,}|\bxox[abprs]-[A-Za-z0-9-]{10,}|\bAIza[0-9A-Za-z_-]{35}")
_BEARER = re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.I)
_KV = re.compile(
    r"""(?ix)\b(pass(?:word|wd)?|pwd|secret|token|api[_-]?key|apikey|access[_-]?key|private[_-]?key
        |authorization|credentials?|client[_-]?secret)(["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|\S+)""")
_EMAIL = re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_CARD = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
_PHONE_INTL = re.compile(r"(?<!\w)\+\d{1,3}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}(?!\d)")
_PHONE_DZ = re.compile(r"(?<!\d)0[567](?:[\s.-]?\d{2}){4}(?!\d)")
_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
_IPV4 = re.compile(rf"\b{_OCTET}(?:\.{_OCTET}){{3}}\b")
_USER = re.compile(
    r"(?i)\b(invalid user |failed password for (?:invalid user )?|accepted (?:password|publickey) for "
    r"|session (?:opened|closed) for user |for user |by user |user[=:] ?|ruser=|logname=)([^\s;,\]]+)")
_TOKEN = re.compile(r"\b(?=[A-Za-z0-9_]*\d)(?=[A-Za-z0-9_]*[A-Za-z])[A-Za-z0-9_]{32,}\b")


def _luhn(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def mask(text: str, *, ips: bool = True, usernames: bool = True) -> MaskResult:
    counts: dict[str, int] = {}

    def apply(kind: str, pattern: re.Pattern, repl) -> None:
        nonlocal text
        text, n = pattern.subn(repl, text)
        if n:
            counts[kind] = counts.get(kind, 0) + n

    def card(m: re.Match) -> str:
        if _luhn(m.group()):
            counts["card"] = counts.get("card", 0) + 1
            return "<CARD>"
        return m.group()

    apply("private_key", _PRIVATE_KEY, "<PRIVATE_KEY>")
    apply("url_credentials", _URL_CREDS, r"\1<CREDENTIALS>@")
    apply("jwt", _JWT, "<JWT>")
    apply("api_key", _API_KEY, "<API_KEY>")
    apply("bearer", _BEARER, r"\1 <TOKEN>")
    apply("secret_value", _KV, r"\1\2<SECRET>")
    apply("email", _EMAIL, "<EMAIL>")
    text = _CARD.sub(card, text)
    apply("phone", _PHONE_INTL, "<PHONE>")
    apply("phone", _PHONE_DZ, "<PHONE>")
    if ips:
        apply("ip", _IPV4, "<IP>")
    if usernames:
        apply("username", _USER, r"\1<USER>")
    apply("token", _TOKEN, "<TOKEN>")
    return MaskResult(text, counts)
