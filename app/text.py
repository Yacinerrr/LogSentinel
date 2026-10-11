import re

_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_IP = re.compile(r"\b\d{1,3}(\.\d{1,3}){3}\b")
_NUM = re.compile(r"\d+")


def normalize(message: str) -> str:
    """Mask variable parts so similar logs share one LLM cache entry."""
    m = _UUID.sub("<UUID>", message.strip().lower())
    m = _IP.sub("<IP>", m)
    return _NUM.sub("<N>", m)
