# Privacy: what leaves your machine

Only the **LLM tier** (DeepSeek R1) talks to an outside service. Regex and BERT run locally.

## What is sent to the LLM
For each log that reaches the LLM tier:
1. the `source` name (e.g. `LegacyCRM`),
2. the category list and instructions (fixed text),
3. the log message **after masking, then truncated** to `LLM_MAX_CHARS` (default 2000).

Nothing else: no database content, no other logs, no API keys, no users.

## What masking replaces (`app/masking.py`)
| Kind | Example in | Becomes |
|---|---|---|
| Private key blocks (even if cut off) | `-----BEGIN RSA PRIVATE KEY-----...` | `<PRIVATE_KEY>` |
| Credentials in URLs | `postgres://admin:s3cr3t@host` | `postgres://<CREDENTIALS>@host` |
| JWTs | `eyJhbGci...` | `<JWT>` |
| Known API key formats (AWS, `sk-`, GitHub, Slack, Google) | `AKIA...`, `ghp_...` | `<API_KEY>` |
| `Bearer`/`Basic` tokens | `Bearer abc123...` | `Bearer <TOKEN>` |
| `password=`, `secret:`, `api_key=`, `token=`, ... values | `password=Hunter2` | `password=<SECRET>` |
| Emails | `a@b.com` | `<EMAIL>` |
| Credit cards (13-19 digits, Luhn-valid, starting with 3-6, not one repeated digit) | `4111 1111 1111 1111` | `<CARD>` |
| Phone numbers (international `+..`, Algerian mobile `05/06/07..`) | `+213 555 12 34 56` | `<PHONE>` |
| IPv4 addresses (`MASK_IPS`, default on) | `10.0.0.5` | `<IP>` |
| `rhost=` / `host=` values, and the hostname after an IP: `from 1.2.3.4 (name.isp.net)` | `rhost=1-2-3-4.isp.net` | `rhost=<HOST>` |
| Usernames in common patterns (`MASK_USERNAMES`, default on) | `Failed password for root`, `Invalid user bob`, `user=alice` | `<USER>` |
| Long token-like strings (32+ letters/digits/_) | `54fadb41...` | `<TOKEN>` |

A log that changes is logged as `masked before LLM: {kind: count}`. **Only kinds and counts, never values.**

## Safety behavior
- **Fail closed:** if masking raises an error, the LLM is **not called** and the log is `Unclassified` (tier `fallback`).
- **Cache:** the LLM cache key is built from the *masked* text, so secrets never end up in the cache table. Two logs differing only by a masked value share one cache entry (fewer paid calls).
- **Truncate after masking**, so a secret cut in half can't slip through.
- **Hostile input:** all patterns are linear-time; a test feeds 50,000-character adversarial strings.

## What is NOT covered (be honest in the report)
- Hostnames and domain names **outside** the patterns above (e.g. `getaddrinfo for ns.example.com`), file paths, free-text names ("John Smith called").
- IPv6 addresses, MAC addresses.
- Secrets with no recognizable shape (a password in plain prose: "the password is blue42").
- Non-Latin phone formats other than the two listed.
- Anything else that is personal data but looks like normal text.

**Therefore:** do not send logs that are regulated (medical, financial, children's data) to the LLM tier. For those sources keep the LLM off (no `DEEPSEEK_API_KEY`) or add rules first.

## What we store locally
The `logs` table keeps the **raw** message (needed for review and training). Protect `data/` and the database like the logs themselves; `data/` and `.env` are git-ignored.

## Adding or fixing a rule
1. Add the pattern in `app/masking.py` (no nested quantifiers; anchor with a lookbehind if it scans a run of characters).
2. Add a case in `tests/test_masking.py` (`CASES` for masked, the untouched list for false positives).
3. Run `python -m pytest -q`; the hostile-input test must stay green.
4. Check real data: `python scripts/preview_masking.py data/train.csv`.
