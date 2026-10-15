import os
import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
H = {"X-API-Key": os.getenv("API_KEY", "")}
st.set_page_config(page_title="LogSentinel", layout="wide")
st.title("LogSentinel")
tab1, tab2, tab3 = st.tabs(["Overview", "Try it / Upload", "Review queue"])

with tab1:
    s = requests.get(f"{API}/stats", headers=H, timeout=10).json()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Logs classified", s["total"])
    c2.metric("LLM share", f"{s['llm_share']*100:.1f}%")
    c3.metric("Reviewed", s["reviewed"])
    c4.metric("Reviewed accuracy", s["reviewed_accuracy"] if s["reviewed_accuracy"] is not None else "n/a")
    l, r = st.columns(2)
    l.subheader("By tier"); l.bar_chart(pd.Series(s["by_tier"]))
    r.subheader("By label"); r.bar_chart(pd.Series(s["by_label"]))
    st.subheader("Avg latency (ms) per tier"); st.json(s["avg_latency_ms"])

with tab2:
    src = st.text_input("Source", "ModernCRM")
    msg = st.text_area("Log message", "Failed password for root from 10.0.0.5 port 22 ssh2")
    if st.button("Classify"):
        st.json(requests.post(f"{API}/classify", headers=H, json={"source": src, "log_message": msg}, timeout=120).json())
    st.divider()
    up = st.file_uploader("CSV with source, log_message", type="csv")
    if up and st.button("Classify CSV"):
        res = requests.post(f"{API}/classify/csv", headers=H, files={"file": (up.name, up.getvalue())}, timeout=600)
        st.download_button("Download results", res.content, "classified.csv", "text/csv")

with tab3:
    st.caption("Lowest-confidence, unreviewed logs. Corrections become training data.")
    rows = requests.get(f"{API}/logs", headers=H, params={"unreviewed": True, "max_confidence": 0.9, "limit": 50}, timeout=10).json()
    for r in rows:
        a, b, c = st.columns([5, 2, 1])
        a.write(f"**[{r['source']}]** {r['message']}")
        new = b.text_input("label", r["label"], key=f"l{r['id']}", label_visibility="collapsed")
        if c.button("Save", key=f"s{r['id']}"):
            requests.post(f"{API}/feedback", headers=H, json={"log_id": r["id"], "correct_label": new}, timeout=10)
            st.rerun()
