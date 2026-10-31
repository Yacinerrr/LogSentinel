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

if __name__ == "__main__":
    FAKES = {
        "ok": '{"label": "Error", "reason": "Technical failure."}',
        "empty": "",
        "tronque": '{"label": "Error", "rea',
        "fence": '```json\n{"label": "Error", "reason": "x"}\n```',
        "sans_reason": '{"label": "Error"}',
        "sans_label": '{"reason": "x"}',
        "hors_taxonomie": '{"label": "Warning", "reason": "x"}',
        "minuscules": '{"label": "error", "reason": "x"}',
        "liste": '[{"label": "Error", "reason": "x"}]',
    }
    for name, raw in FAKES.items():
        print(f"{name:15} -> {parse_response(raw)}")