"""Évaluation du LLM sur les jeux A1.4 : parsing, taux d'échec de format, accuracy."""
import json
import os
import time
import random
import argparse
import pandas as pd
import requests
from llm_prompt import build_messages

LABELS = [
    "HTTP Status", "Security Alert", "Critical Error", "Workflow Error", "Error",
    "Resource Usage", "Deprecation Warning", "User Action",
    "System Notification", "Unclassified",
]


def parse_response(raw):
    """Renvoie (label, reason, echec). echec vaut None si la réponse est valide,
    sinon une des raisons : empty, invalid_json, not_object, missing_label,
    missing_reason, bad_label."""
    if raw is None or not raw.strip():
        return None, None, "empty"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, None, "invalid_json"   # couvre aussi les réponses tronquées
    if not isinstance(data, dict):
        return None, None, "not_object"
    if "label" not in data:
        return None, None, "missing_label"
    if "reason" not in data:
        return None, None, "missing_reason"
    if data["label"] not in LABELS:
        return None, None, "bad_label"
    return data["label"], data["reason"], None


MODEL = "gemini-3.1-flash-lite"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
PAUSE = 4.5          # 15 requêtes/minute => 4 s minimum entre deux appels
RUNS_DIR = "llm_runs"


def load_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    with open(".env", encoding="utf-8") as f:
        for line in f:
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"')
    raise SystemExit("GEMINI_API_KEY introuvable (.env ou variable d'environnement)")


def call_gemini(system, user, structured, key, temperature=0.0):
    """Renvoie (texte, finishReason). Si l'appel échoue côté infra : (None, 'HTTP_xxx')."""
    gen = {"temperature": temperature, "maxOutputTokens": 400}
    if structured:
        gen["responseMimeType"] = "application/json"
        gen["responseSchema"] = {
            "type": "OBJECT",
            "properties": {
                "label": {"type": "STRING", "enum": LABELS},
                "reason": {"type": "STRING"},
            },
            "required": ["label", "reason"],
        }
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": gen,
    }
    for wait in (0, 20, 60, 120):          # reprises en cas de 429 (quota)
        time.sleep(wait)
        r = requests.post(URL, headers={"x-goog-api-key": key}, json=body, timeout=60)
        if r.status_code != 429:
            break
    if r.status_code != 200:
        return None, f"HTTP_{r.status_code}"
    cand = r.json().get("candidates", [{}])[0]
    parts = cand.get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    return text, cand.get("finishReason")


def fake_response(i, attempt):
    """Réponses inventées pour tester sans quota : ~15 % d'échecs au 1er essai, ~5 % au 2e."""
    rnd = random.Random(i * 10 + attempt)
    if rnd.random() < (0.15 if attempt == 1 else 0.05):
        return rnd.choice(["", '{"label": "Err', '```json\n{"label": "Error", "reason": "x"}\n```',
                           '{"label": "Warning", "reason": "x"}', '{"label": "Error"}'])
    return json.dumps({"label": rnd.choice(LABELS), "reason": "simulated"})


def run(df, name, structured, simulate, retry=True):
    d = os.path.join(RUNS_DIR, name)
    os.makedirs(d, exist_ok=True)
    key = None if simulate else load_key()
    for i, row in df.reset_index(drop=True).iterrows():
        for attempt in (1, 2):
            path = os.path.join(d, f"{i:04d}_{attempt}.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    rec = json.load(f)
            else:
                if simulate:
                    raw, fin = fake_response(i, attempt), "STOP"
                else:
                    system, user = build_messages(row["log_message"])
                    temp = 0.0 if attempt == 1 else 0.5
                    raw, fin = call_gemini(system, user, structured, key, temp)
                    if raw is None:
                        print(f"Arrêt à la ligne {i} ({fin}). Relance la même commande plus tard.")
                        return
                    time.sleep(PAUSE)
                rec = {"i": i, "attempt": attempt, "raw": raw, "finish": fin}
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(rec, f, ensure_ascii=False)
            if parse_response(rec["raw"])[2] is None or not retry:
                break
    print(f"Terminé : {name}")


def report(df, name):
    d = os.path.join(RUNS_DIR, name)
    rows = []
    for i, row in df.reset_index(drop=True).iterrows():
        p1 = os.path.join(d, f"{i:04d}_1.json")
        if not os.path.exists(p1):
            continue
        with open(p1, encoding="utf-8") as f:
            r1 = json.load(f)
        label, _, fail1 = parse_response(r1["raw"])
        fail2 = fail1
        p2 = os.path.join(d, f"{i:04d}_2.json")
        if fail1 and os.path.exists(p2):
            with open(p2, encoding="utf-8") as f:
                r2 = json.load(f)
            label, _, fail2 = parse_response(r2["raw"])
        rows.append({"source": row["source"], "target": row["target_label"],
                     "fail1": fail1, "fail2": fail2, "finish": r1["finish"],
                     "label": label})
    r = pd.DataFrame(rows)
    n = len(r)
    if n == 0:
        print("Aucune réponse à mesurer.")
        return
    f1, f2 = r["fail1"].notna().sum(), r["fail2"].notna().sum()
    print(f"\n=== {name} : {n} lignes mesurées ===")
    print(f"Échec de format avant retry : {f1}/{n} = {100*f1/n:.1f} %")
    print(f"Échec de format après retry : {f2}/{n} = {100*f2/n:.1f} %")
    print(f"Parsable après retry : {100*(n-f2)/n:.1f} %  (critère : >= 95 %)")
    print("Raisons d'échec (avant retry) :", r["fail1"].value_counts().to_dict())
    print("Champ finish :", r["finish"].value_counts().to_dict())
    groups = [("tout", r),
              ("réel", r[r["source"] != "synthetic"]),
              ("synthétique", r[r["source"] == "synthetic"])]
    for g, sub in groups:
        if len(sub) == 0:
            continue
        ok = (sub["label"] == sub["target"]).sum()
        valid = sub["fail2"].isna().sum()
        acc_valid = f"{100*ok/valid:.1f} %" if valid else "n/a"
        print(f"Accuracy {g:12} : {ok}/{len(sub)} = {100*ok/len(sub):.1f} % (échecs comptés faux)"
              f" | sur réponses valides : {acc_valid}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["fewshot", "tune", "final"], default="tune")
    ap.add_argument("--structured", action="store_true", help="sortie structurée forcée")
    ap.add_argument("--simulate", action="store_true", help="réponses inventées, sans API")
    ap.add_argument("--tag", default="v1", help="change-le à chaque version du prompt")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    df = pd.read_csv(f"data/llm_eval/{a.set}.csv")
    if a.limit:
        df = df.head(a.limit)
    mode = "struct" if a.structured else "free"
    sim = "_sim" if a.simulate else ""
    name = f"{a.set}_{mode}_{a.tag}{sim}"
    run(df, name, a.structured, a.simulate)
    report(df, name)