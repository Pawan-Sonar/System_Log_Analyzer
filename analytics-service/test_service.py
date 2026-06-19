import pytest
from service import analyze


def test_empty():
    out = analyze([])
    assert out["risk_score"] == 0
    assert out["risk_level"] == "low"


def test_brute_force_detection():
    logs = [
        {"timestamp": "2025-01-01T12:00:00Z", "ip_address": "1.2.3.4",
         "username": "alice", "event_type": "failed_login", "status": "failure"}
        for _ in range(25)
    ]
    out = analyze(logs)
    assert any(a["type"] == "brute_force" for a in out["alerts"])
    assert out["risk_level"] in {"high", "critical"}


def test_clean_dataset():
    logs = [
        {"timestamp": "2025-01-01T12:00:00Z", "ip_address": "10.0.0.1",
         "username": "bob", "event_type": "login", "status": "success"}
        for _ in range(20)
    ]
    out = analyze(logs)
    assert out["risk_level"] == "low"
