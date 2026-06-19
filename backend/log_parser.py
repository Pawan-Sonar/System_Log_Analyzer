"""Parse uploaded security logs (CSV, JSON, TXT)."""
from __future__ import annotations
import csv
import json
import io
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

# TXT line patterns we accept (very flexible):
#   2024-01-15 12:34:56 192.168.1.10 alice failed_login failure
#   2024-01-15T12:34:56Z,192.168.1.10,bob,login,success
TXT_SPLIT_RE = re.compile(r"[\s,;|\t]+")


VALID_EVENTS = {"login", "logout", "failed_login", "password_reset"}
VALID_STATUS = {"success", "failure"}


def _normalize(row: Dict[str, Any]) -> Dict[str, Any] | None:
    """Coerce a row dict to canonical log shape. Returns None if invalid."""
    keys = {k.lower().strip(): v for k, v in row.items() if k is not None}
    ts_raw = keys.get("timestamp") or keys.get("time") or keys.get("date")
    ip = (keys.get("ip") or keys.get("ip_address") or keys.get("ipaddress") or "").strip()
    user = (keys.get("username") or keys.get("user") or "").strip()
    event = (keys.get("event_type") or keys.get("event") or keys.get("action") or "").strip().lower()
    status = (keys.get("status") or keys.get("result") or "").strip().lower()
    if not (ts_raw and ip and user):
        return None
    ts = _parse_ts(str(ts_raw))
    if not ts:
        return None
    # Infer event/status if missing
    if event == "" and status in VALID_STATUS:
        event = "login" if status == "success" else "failed_login"
    if event not in VALID_EVENTS:
        # try map common variants
        if "fail" in event or status == "failure":
            event = "failed_login"
        elif "logout" in event:
            event = "logout"
        elif "reset" in event:
            event = "password_reset"
        else:
            event = "login"
    if status not in VALID_STATUS:
        status = "failure" if event == "failed_login" else "success"
    return {
        "timestamp": ts.isoformat(),
        "ip_address": ip,
        "username": user,
        "event_type": event,
        "status": status,
    }


def _parse_ts(s: str) -> datetime | None:
    s = s.strip().strip('"').strip("'")
    fmts = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
    ]
    # Try ISO with timezone first
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:  # noqa: BLE001
        pass
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            continue
    return None


def parse_csv(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for row in reader:
        n = _normalize(row)
        if n:
            out.append(n)
    return out


def parse_json(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8", errors="replace")
    data = json.loads(text)
    if isinstance(data, dict):
        # Look for nested arrays
        for v in data.values():
            if isinstance(v, list):
                data = v
                break
    if not isinstance(data, list):
        return []
    out = []
    for row in data:
        if isinstance(row, dict):
            n = _normalize(row)
            if n:
                out.append(n)
    return out


def parse_txt(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8", errors="replace")
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p for p in TXT_SPLIT_RE.split(line) if p]
        if len(parts) < 4:
            continue
        # Heuristic: first 1-2 tokens are date/time, then ip, user, event, status
        ts_candidate = parts[0]
        rest = parts[1:]
        # combine first two if first looks like date (YYYY-MM-DD)
        if re.match(r"^\d{4}-\d{2}-\d{2}$", ts_candidate) and rest and re.match(r"^\d{2}:\d{2}", rest[0]):
            ts_candidate = f"{ts_candidate} {rest[0]}"
            rest = rest[1:]
        ip = rest[0] if len(rest) > 0 else ""
        user = rest[1] if len(rest) > 1 else ""
        event = rest[2] if len(rest) > 2 else "login"
        status = rest[3] if len(rest) > 3 else "success"
        n = _normalize({
            "timestamp": ts_candidate,
            "ip": ip,
            "username": user,
            "event_type": event,
            "status": status,
        })
        if n:
            out.append(n)
    return out


def parse(filename: str, content: bytes) -> List[Dict[str, Any]]:
    name = filename.lower()
    if name.endswith(".csv"):
        return parse_csv(content)
    if name.endswith(".json"):
        return parse_json(content)
    if name.endswith(".txt") or name.endswith(".log"):
        return parse_txt(content)
    # try all
    for fn in (parse_json, parse_csv, parse_txt):
        try:
            res = fn(content)
            if res:
                return res
        except Exception:  # noqa: BLE001
            continue
    return []
