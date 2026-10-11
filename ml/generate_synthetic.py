"""Generate a synthetic labeled dataset so both of you can start before real data exists.
Usage: python -m ml.generate_synthetic --n 300 --out data/synthetic.csv
"""
import argparse
import csv
import random

T = {
    "User Action": ["User User{n} logged in.", "User User{n} logged out.", "Account with ID {n} created by admin{n}.",
                    "User {user} updated profile settings.", "User {user} changed password successfully."],
    "System Notification": ["Backup started at {n}:00.", "Backup completed successfully.", "System updated to version {n}.{n}.{n}.",
                            "File data_{n}.csv uploaded successfully by user User{n}.", "Disk cleanup completed successfully.",
                            "Scheduled maintenance window starts in {n} minutes.", "Cache rebuilt in {ms} ms."],
    "HTTP Status": ['{ip} - - [12/May/2026:10:{n}:01] "GET /api/v{n}/items HTTP/1.1" 200 {n}',
                    '{ip} - - [12/May/2026:10:{n}:09] "POST /login HTTP/1.1" 401 {n}',
                    'nova.osapi_compute.wsgi.server "GET /v2/{id}/servers/detail HTTP/1.1" status: 500 len: {n} time: 0.{n}'],
    "Security Alert": ["Failed password for root from {ip} port {n} ssh2", "Multiple failed login attempts detected for {user}",
                       "Unauthorized access attempt on /admin from {ip}", "Suspicious privilege escalation by {user}",
                       "Port scan detected from {ip}, {n} ports probed"],
    "Critical Error": ["Email service experiencing issues with sending, retrying in {n}s", "Database connection lost: pool exhausted",
                       "Kernel panic: unable to mount root fs", "Service payment-gateway crashed with exit code {n}",
                       "Out of memory: process {n} killed"],
    "Error": ["Unexpected exception in handler {user}: NullPointerException", "Request {id} failed with timeout after {ms} ms",
              "Failed to parse config file line {n}", "Shard {n} replication lag exceeded threshold"],
    "Resource Usage": ["Nova compute claim successful: memory {n} MB, disk {n} GB, vcpus {n}", "CPU usage at {n}% on node-{n}",
                       "Memory usage {n}% exceeds soft limit", "Disk /var/log {n}% full"],
    "Workflow Error": ["Escalation rule failed for ticket ID {id}: undefined assignee", "Task assignment error for case {id}: no eligible agent",
                       "Process step {n} of workflow {id} aborted: missing approval"],
    "Deprecation Warning": ["The '{user}' module will be retired in version {n}.0", "API endpoint /v{n}/export is deprecated, use /v{n}/exports",
                            "Function legacy_sync() is deprecated and will be removed"],
}
SOURCES = ["ModernCRM", "BillingSystem", "AnalyticsEngine", "ThirdPartyAPI", "ModernHR"]
LLM_CATS = {"Workflow Error", "Deprecation Warning"}


def fill(t):
    return t.format(n=random.randint(1, 999), ms=random.randint(5, 9000), id=random.randint(10000, 99999),
                    ip=".".join(str(random.randint(1, 254)) for _ in range(4)),
                    user=random.choice(["alice", "bob", "svc_api", "legacy_auth", "mailer"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="rows per category")
    ap.add_argument("--out", default="data/synthetic.csv")
    a = ap.parse_args()
    random.seed(42)
    rows = []
    for label, templates in T.items():
        n = 40 if label in LLM_CATS else a.n   # LLM categories are deliberately low-data
        for _ in range(n):
            src = "LegacyCRM" if label in LLM_CATS else random.choice(SOURCES)
            rows.append((src, fill(random.choice(templates)), label))
    random.shuffle(rows)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "log_message", "target_label"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {a.out}")


if __name__ == "__main__":
    main()
