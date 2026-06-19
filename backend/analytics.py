"""Security analytics engine using pandas. Detects attacks and computes risk scores."""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import Iterable, List, Dict, Any
import pandas as pd

logger = logging.getLogger(__name__)


# Heuristic MITRE ATT&CK mappings used across detectors
MITRE = {
    "brute_force": "T1110",  # Brute Force
    "password_spraying": "T1110.003",
    "credential_stuffing": "T1110.004",
    "valid_accounts": "T1078",
    "unusual_time": "T1078",
}


def _df(logs: Iterable[dict]) -> pd.DataFrame:
    rows = []
    for entry in logs:
        ts = entry.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:  # noqa: BLE001
                ts = None
        rows.append({
            "id": entry.get("id"),
            "timestamp": ts,
            "ip": entry.get("ip_address"),
            "username": entry.get("username"),
            "event_type": entry.get("event_type"),
            "status": entry.get("status"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    return df


def detect(logs: List[dict]) -> Dict[str, Any]:
    """Run all detectors. Returns dict of findings + alerts + risk score."""
    df = _df(logs)
    findings: Dict[str, Any] = {
        "alerts": [],
        "top_suspicious_ips": [],
        "failed_per_user": [],
        "unusual_hours": [],
        "brute_force_ips": [],
    }
    total = len(df)
    if total == 0:
        findings["risk_score"] = 0
        findings["risk_level"] = "low"
        return findings

    df_fail = df[df["status"].str.lower() == "failure"]
    df_succ = df[df["status"].str.lower() == "success"]

    failed_logins = int(len(df_fail))
    success_logins = int(len(df_succ))

    # --- Brute force: 20+ failures from same IP overall ---
    if not df_fail.empty:
        bf = df_fail.groupby("ip").size().reset_index(name="count")
        bf = bf.sort_values("count", ascending=False)
        brute_ips = bf[bf["count"] >= 20]
        for _, row in brute_ips.iterrows():
            findings["brute_force_ips"].append({"ip": row["ip"], "count": int(row["count"])})
            findings["alerts"].append({
                "type": "brute_force",
                "severity": "critical",
                "message": f"IP {row['ip']} attempted {int(row['count'])} failed logins.",
                "ip_address": row["ip"],
                "mitre_id": MITRE["brute_force"],
            })
        # Top suspicious IPs (top 10)
        findings["top_suspicious_ips"] = [
            {"ip": r["ip"], "count": int(r["count"])} for _, r in bf.head(10).iterrows()
        ]

    # --- Failed login burst per user: 5+ within 10 minutes ---
    if not df_fail.empty:
        for username, sub in df_fail.groupby("username"):
            sub = sub.sort_values("timestamp")
            ts = sub["timestamp"].dropna().tolist()
            window_hits = 0
            for i in range(len(ts)):
                j = i
                count = 0
                while j < len(ts) and (ts[j] - ts[i]).total_seconds() <= 600:
                    count += 1
                    j += 1
                if count >= 5:
                    window_hits = max(window_hits, count)
            if window_hits:
                findings["failed_per_user"].append({"username": username, "count": int(window_hits)})
                sev = "high" if window_hits < 10 else "critical"
                findings["alerts"].append({
                    "type": "failed_login_burst",
                    "severity": sev,
                    "message": f"User '{username}' received {window_hits} failed logins in 10 min window.",
                    "username": username,
                    "mitre_id": MITRE["credential_stuffing"],
                })

    # --- Unusual login hours (00:00–05:00) for successful logins ---
    if not df_succ.empty:
        succ = df_succ.dropna(subset=["timestamp"]).copy()
        if not succ.empty:
            succ["hour"] = succ["timestamp"].dt.hour
            night = succ[(succ["hour"] >= 0) & (succ["hour"] < 5)]
            if not night.empty:
                by_user = night.groupby("username").size().reset_index(name="count")
                for _, r in by_user.iterrows():
                    findings["unusual_hours"].append({"username": r["username"], "count": int(r["count"])})
                    findings["alerts"].append({
                        "type": "unusual_hours",
                        "severity": "medium",
                        "message": f"User '{r['username']}' had {int(r['count'])} login(s) between 00:00–05:00.",
                        "username": r["username"],
                        "mitre_id": MITRE["unusual_time"],
                    })

    # --- Risk score calculation ---
    fail_ratio = (failed_logins / total) if total else 0
    score = 0
    score += min(40, int(fail_ratio * 100))  # up to 40 from failure ratio
    score += min(30, len(findings["brute_force_ips"]) * 15)
    score += min(20, len(findings["failed_per_user"]) * 5)
    score += min(10, len(findings["unusual_hours"]) * 2)
    score = max(0, min(100, score))

    level = "low"
    if score >= 75:
        level = "critical"
    elif score >= 50:
        level = "high"
    elif score >= 25:
        level = "medium"

    findings["risk_score"] = score
    findings["risk_level"] = level
    findings["failed_logins"] = failed_logins
    findings["success_logins"] = success_logins
    findings["total"] = total
    findings["suspicious_ips_count"] = len(findings["top_suspicious_ips"])
    return findings


def timeseries(logs: List[dict], bucket: str = "hour") -> List[dict]:
    """Aggregate logs into time buckets for charts (default: hour)."""
    df = _df(logs).dropna(subset=["timestamp"])
    if df.empty:
        return []
    freq = {"hour": "1h", "day": "1D"}.get(bucket, "1h")
    df["bucket"] = df["timestamp"].dt.floor(freq)
    grp = df.groupby(["bucket", "status"]).size().unstack(fill_value=0).reset_index()
    out = []
    for _, r in grp.iterrows():
        success = int(r.get("success", 0)) if "success" in r else 0
        failure = int(r.get("failure", 0)) if "failure" in r else 0
        out.append({
            "bucket": r["bucket"].isoformat(),
            "success": success,
            "failure": failure,
            "total": success + failure,
        })
    return out


def event_distribution(logs: List[dict]) -> List[dict]:
    df = _df(logs)
    if df.empty:
        return []
    grp = df.groupby("event_type").size().reset_index(name="count")
    return [{"event_type": r["event_type"], "count": int(r["count"])} for _, r in grp.iterrows()]
