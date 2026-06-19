"""Standalone Pandas analytics microservice.

This mirrors the logic embedded in the FastAPI backend's analytics.py module
and exposes it over HTTP. The Docker deliverable runs this as a separate
service so a Node.js-only backend can offload analytics to Python.

Endpoint:
  POST /analyze   { "logs": [ { timestamp, ip_address, username, event_type, status }, ... ] }
"""
import os
import sys
from datetime import datetime, timezone
import pandas as pd
from flask import Flask, request, jsonify

app = Flask(__name__)

MITRE = {
    "brute_force": "T1110",
    "credential_stuffing": "T1110.004",
    "unusual_time": "T1078",
}


def to_df(logs):
    rows = []
    for entry in logs:
        ts = entry.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = None
        rows.append({
            "timestamp": ts,
            "ip": entry.get("ip_address"),
            "username": entry.get("username"),
            "event_type": entry.get("event_type"),
            "status": (entry.get("status") or "").lower(),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def analyze(logs):
    df = to_df(logs)
    if df.empty:
        return {"risk_score": 0, "risk_level": "low", "alerts": [], "total": 0}
    fail = df[df["status"] == "failure"]
    succ = df[df["status"] == "success"]
    alerts = []
    top_ips = []
    if not fail.empty:
        bf = fail.groupby("ip").size().reset_index(name="count").sort_values("count", ascending=False)
        for _, r in bf[bf["count"] >= 20].iterrows():
            alerts.append({"type": "brute_force", "severity": "critical",
                           "message": f"IP {r['ip']} attempted {int(r['count'])} failed logins.",
                           "ip_address": r["ip"], "mitre_id": MITRE["brute_force"]})
        top_ips = [{"ip": r["ip"], "count": int(r["count"])} for _, r in bf.head(10).iterrows()]
    failed = int(len(fail))
    total = int(len(df))
    fail_ratio = failed / total if total else 0
    score = min(40, int(fail_ratio * 100)) + min(60, 15 * len([a for a in alerts if a["type"] == "brute_force"]))
    score = max(0, min(100, score))
    level = "critical" if score >= 75 else "high" if score >= 50 else "medium" if score >= 25 else "low"
    return {
        "risk_score": score, "risk_level": level,
        "total": total, "failed_logins": failed,
        "success_logins": int(len(succ)),
        "alerts": alerts, "top_suspicious_ips": top_ips,
    }


@app.post("/analyze")
def analyze_endpoint():
    payload = request.get_json(silent=True) or {}
    logs = payload.get("logs", [])
    return jsonify(analyze(logs))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9000"))
    app.run(host="0.0.0.0", port=port)
