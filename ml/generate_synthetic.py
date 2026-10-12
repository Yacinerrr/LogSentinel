import csv
import random
import re

random.seed(42)

# 1. Les valeurs qui remplissent les {trous}
LISTES = {
    "user": ["alice", "bob", "omar", "sara", "karim", "nadia", "youcef", "lina", "admin", "manager1", "dev02", "support"],
    "doc": ["purchase order", "invoice", "sales order", "ticket", "maintenance request", "manufacturing order", "transfer", "quotation"],
    "model": ["sale.order", "purchase.order", "res.partner", "stock.picking", "account.move"],
    "report": ["monthly_sales", "stock_valuation", "aged_receivable", "maintenance_summary"],
    "filename": ["invoice_2026.pdf", "contract.docx", "inventory.xlsx", "photo.png", "notes.txt"],
    "module": ["ReportGenerator", "LegacyExporter", "PdfBuilder", "MailBridge", "SyncAgent", "OldScheduler", "CsvImporter", "AuthProxy"],
    "version": ["2.0", "3.1", "4.0", "5.2", "6.0", "17.0", "18.0", "19.0"],
    "func": ["get_records", "render_page", "load_config", "send_notification", "parse_date", "open_session", "build_query", "format_amount"],
    "newfunc": ["fetch_records", "render_view", "read_config", "notify", "parse_datetime", "start_session", "make_query", "format_currency"],
    "option": ["xmlrpc_port", "longpolling_port", "db_host", "log_handler", "workers_legacy"],
    "newoption": ["http_port", "gevent_port", "db_hostname", "log_level", "workers"],
    "api": ["Legacy REST", "SOAP", "XML-RPC", "v1 Reports", "Old Auth"],
    "tech": ["Python", "PostgreSQL", "Node.js", "OpenSSL", "Java"],
    "techver": ["3.8", "9.6", "12", "1.0.2", "8"],
    "feature": ["classic dashboard", "legacy export wizard", "old calendar view", "inline editor"],
    "newfeature": ["new dashboard", "export tool", "scheduler view", "rich editor"],
    "param": ["timeout_ms", "use_cache", "legacy_mode", "mode", "batch_size"],
    "state": ["draft", "pending", "waiting approval", "in progress", "done", "cancelled"],
    "field": ["customer", "assignee", "due date", "warehouse", "currency", "approver", "payment term", "responsible"],
    "action": ["notify manager", "close ticket", "assign team", "send reminder", "create task"],
    "policy": ["Gold support", "Standard SLA", "Critical incidents", "VIP customers"],
    "rule": ["round robin", "by team", "by region", "workload balancing"],
    "service": ["PostgreSQL", "Odoo server", "nginx", "redis", "RabbitMQ", "Apache", "MySQL"],
    "reason": ["Fatal exception in interrupt", "VFS: Unable to mount root fs", "Attempted to kill init", "Out of memory and no killable processes"],
    "path": ["/var/lib/postgresql/data", "/var/lib/mysql", "/opt/odoo/data", "/srv/db"],
    "mount": ["/var", "/data", "/home", "/srv", "/backup"],
    "store": ["orders table", "audit log", "customer database", "message queue", "ledger"],
    "md": ["md0", "md1", "md2"],
}
LISTES["state2"] = LISTES["state"]

FONCTIONS = {
    "ip": lambda: ".".join(str(random.randint(1, 254)) for _ in range(4)),
    "port": lambda: random.randint(1024, 65535),
    "id": lambda: random.randint(1000, 99999),
    "n": lambda: random.randint(1, 5000),
    "pid": lambda: random.randint(100, 32000),
    "retries": lambda: random.randint(2, 10),
    "hex": lambda: "%08x" % random.getrandbits(32),
}


def valeur(nom):
    if nom in FONCTIONS:
        return FONCTIONS[nom]()
    return random.choice(LISTES[nom])


def remplir(phrase):
    return re.sub(r"\{(\w+)\}", lambda m: str(valeur(m.group(1))), phrase)


# 2. Les phrases à trous : (nombre de lignes voulu, liste de phrases)
MODELES = {
    "Deprecation Warning": (200, [
        "The '{module}' module will be retired in version {version}",
        "DeprecationWarning: {func}() is deprecated and will be removed in version {version}, use {newfunc}() instead",
        "WARNING: option '{option}' is deprecated and will be removed in a future release, use '{newoption}' instead",
        "The {api} API is deprecated since version {version} and scheduled for removal",
        "Support for {tech} {techver} is deprecated and will be dropped in version {version}",
        "The {feature} has been marked obsolete, please migrate to the {newfeature} before version {version}",
        "Usage of the '{param}' parameter is deprecated and will be ignored starting with version {version}",
        "{module}.{func} is deprecated, please use {module}.{newfunc}",
    ]),
    "Workflow Error": (200, [
        "Escalation rule failed for ticket ID {id}: undefined assignee",
        "Approval workflow stopped for {doc} {id}: no approver defined",
        "Validation failed for {doc} {id}: required field '{field}' is empty",
        "Cannot confirm {doc} {id}: related {doc} is still in state '{state}'",
        "Workflow transition '{state}' -> '{state2}' is not allowed for {doc} {id}",
        "Automated action '{action}' failed on {doc} {id}: missing {field}",
        "SLA policy '{policy}' could not be applied to ticket {id}: no matching team",
        "UserError: you cannot validate {doc} {id} while the {field} is not set",
        "Assignment rule '{rule}' found no eligible user for {doc} {id}",
    ]),
    "Critical Error": (200, [
        "Database connection lost, service down",
        "CRITICAL: {service} service stopped unexpectedly and could not be restarted",
        "kernel panic - not syncing: {reason}",
        "FATAL: the database cluster at '{path}' is corrupted, server cannot start",
        "Filesystem {mount} is corrupted and was remounted read-only, data may be lost",
        "Data loss detected: {n} records in {store} could not be recovered",
        "CRITICAL: all worker processes of {service} have crashed, application is unavailable",
        "RAID array {md} has failed, volume {mount} is offline",
        "FATAL: {service} unreachable after {retries} retries, shutting down",
    ]),
    "User Action": (250, [
        "User {user} logged in.",
        "User {user} logged out.",
        "Accepted password for {user} from {ip} port {port} ssh2",
        "{user} created {doc} {id}",
        "{user} updated {doc} {id}",
        "{user} deleted {doc} {id}",
        "User {user} downloaded report '{report}'",
        "User {user} changed their password",
        "User {user} exported {n} records from {model}",
        "Login successful for user '{user}' from {ip}",
        "Received disconnect from {ip}: 11: disconnected by user",
        "User {user} uploaded file '{filename}'",
    ]),
    "Unclassified": (120, [
        "-- MARK --",
        "ok",
        "...",
        "{hex}",
        "0x{hex} 0x{hex}",
        "{n} {n} {n}",
        "[{n}]",
        "== {n} ==",
        "Connection to {ip} est",
        "{pid}]: session op",
        "kernel: xyz 0x{hex}",
    ]),
}

# 3. Génération : on tire jusqu'à avoir assez de lignes toutes différentes
lignes = []
for label, (cible, phrases) in MODELES.items():
    textes = set()
    essais = 0
    while len(textes) < cible and essais < cible * 50:
        essais += 1
        textes.add(remplir(random.choice(phrases)))
    for texte in sorted(textes):
        lignes.append(("synthetic", texte, label))
    print(f"{len(textes):4d}  {label}")

with open("data/synthetic_logs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["source", "log_message", "target_label"])
    w.writerows(lignes)