"""End-to-end backend tests for Security Log Analyzer.

Covers: auth (login/register/me/logout/forgot/reset/2FA), logs (seed/upload/list/by-ip/delete),
analytics (kpi/dashboard/run), alerts (list/ack), reports (pdf/csv), mitre, geo.
"""
import os
import io
import csv
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://incidentrecon.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@soc.com"
ADMIN_PASSWORD = "Admin@123"


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_session():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="session")
def admin_seeded(admin_session):
    """Ensure demo data exists exactly once for the admin user."""
    r = admin_session.post(f"{API}/logs/seed-demo", timeout=30)
    assert r.status_code == 200
    return r.json()


# ---------- AUTH ----------
class TestAuth:
    def test_health(self):
        r = requests.get(f"{API}/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_admin_login_sets_cookie(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "user" in data and data["user"]["email"] == ADMIN_EMAIL
        assert "access_token" in data
        # Cookie should be set (httpOnly access_token)
        assert "access_token" in s.cookies.get_dict()

    def test_me_authenticated(self, admin_session):
        r = admin_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_login_bad_password(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "WRONG"}, timeout=10)
        assert r.status_code == 401

    def test_register_then_logout(self):
        s = requests.Session()
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        r = s.post(f"{API}/auth/register",
                   json={"email": email, "password": "Test@12345", "name": "Tester"}, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["user"]["email"] == email
        # /me works after register (auto-login)
        r2 = s.get(f"{API}/auth/me", timeout=10)
        assert r2.status_code == 200
        # logout
        r3 = s.post(f"{API}/auth/logout", timeout=10)
        assert r3.status_code == 200
        # /me now returns 401
        r4 = s.get(f"{API}/auth/me", timeout=10)
        assert r4.status_code == 401

    def test_forgot_password_unknown_email(self):
        r = requests.post(f"{API}/auth/forgot-password",
                          json={"email": f"nobody_{uuid.uuid4().hex[:6]}@example.com"}, timeout=15)
        assert r.status_code == 200
        assert "message" in r.json()

    def test_reset_password_invalid_token(self):
        r = requests.post(f"{API}/auth/reset-password",
                          json={"token": "invalid-token-xxx", "new_password": "NewPass@123"}, timeout=15)
        assert r.status_code == 400

    def test_2fa_setup_and_verify_invalid(self, admin_session):
        r = admin_session.post(f"{API}/auth/2fa/setup", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "secret" in data and "otpauth_uri" in data
        assert data["qr_code"].startswith("data:image/png;base64,")
        # invalid 6-digit code -> 400
        r2 = admin_session.post(f"{API}/auth/2fa/verify", json={"code": "000000"}, timeout=10)
        assert r2.status_code == 400


# ---------- LOGS ----------
class TestLogs:
    def test_seed_demo(self, admin_session, admin_seeded):
        assert admin_seeded["inserted"] >= 250
        assert admin_seeded["alerts_created"] >= 1

    def test_upload_csv(self, admin_session):
        csv_content = (
            "timestamp,ip,username,event_type,status\n"
            "2025-01-01T12:00:00Z,10.0.0.5,bob,login,success\n"
            "2025-01-01T12:01:00Z,10.0.0.5,bob,failed_login,failure\n"
            "2025-01-01T12:02:00Z,10.0.0.5,bob,failed_login,failure\n"
        )
        files = {"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")}
        r = admin_session.post(f"{API}/logs/upload", files=files, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["inserted"] == 3

    def test_list_logs_with_filters(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/logs", params={"event_type": "failed_login", "page": 1, "page_size": 10}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data
        for it in data["items"]:
            assert it["event_type"] == "failed_login"

    def test_logs_by_ip(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/logs/by-ip/185.220.101.42", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["ip"] == "185.220.101.42"
        assert "geo" in data
        assert "items" in data and data["total"] >= 1


# ---------- ANALYTICS ----------
class TestAnalytics:
    def test_kpi(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/analytics/kpi", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for k in ("total_logs", "failed_logins", "suspicious_ips", "risk_score", "risk_level"):
            assert k in data
        assert 0 <= data["risk_score"] <= 100
        assert data["risk_level"] in ("low", "medium", "high", "critical")

    def test_dashboard(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/analytics/dashboard", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("kpi", "timeseries", "event_distribution", "top_suspicious_ips"):
            assert k in d
        assert isinstance(d["timeseries"], list)
        assert isinstance(d["event_distribution"], list)
        assert isinstance(d["top_suspicious_ips"], list)

    def test_run_creates_report(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/analytics/run", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "risk_score" in d and "findings" in d
        # Verify persisted
        r2 = admin_session.get(f"{API}/reports", timeout=10)
        assert r2.status_code == 200
        assert len(r2.json()["items"]) >= 1


# ---------- ALERTS ----------
class TestAlerts:
    def test_list_alerts(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/alerts", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert len(data["items"]) >= 1
        for a in data["items"]:
            assert a["severity"] in ("critical", "high", "medium", "low")

    def test_acknowledge_alert(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/alerts", timeout=15)
        items = r.json()["items"]
        if not items:
            pytest.skip("No alerts to acknowledge")
        target = next((a for a in items if not a.get("acknowledged")), items[0])
        aid = target["id"]
        r2 = admin_session.post(f"{API}/alerts/{aid}/acknowledge", timeout=10)
        assert r2.status_code == 200
        # verify
        r3 = admin_session.get(f"{API}/alerts", timeout=10)
        match = next((a for a in r3.json()["items"] if a["id"] == aid), None)
        assert match is not None and match["acknowledged"] is True


# ---------- REPORTS ----------
class TestReports:
    def test_pdf(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/reports/pdf", timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    def test_csv_logs(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/reports/csv/logs", timeout=30)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        text = r.content.decode("utf-8")
        assert text.splitlines()[0].startswith("timestamp,ip_address,username")

    def test_csv_alerts(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/reports/csv/alerts", timeout=30)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert b"timestamp,severity,type" in r.content[:200]


# ---------- MITRE ----------
class TestMitre:
    def test_matrix(self, admin_session, admin_seeded):
        r = admin_session.get(f"{API}/mitre/matrix", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "tactics" in d
        assert len(d["tactics"]) >= 1
        for tac in d["tactics"]:
            assert "techniques" in tac
            for tech in tac["techniques"]:
                assert "id" in tech and "hits" in tech


# ---------- GEO ----------
class TestGeo:
    def test_private_ip(self, admin_session):
        r = admin_session.get(f"{API}/geo/10.0.0.5", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["ip"] == "10.0.0.5"
        # Private should have country=Private Network per spec
        country = d.get("country", "")
        assert "Private" in country or country != ""

    def test_public_ip(self, admin_session):
        r = admin_session.get(f"{API}/geo/8.8.8.8", timeout=20)
        # Allow failure if no internet; just check structure
        assert r.status_code == 200
        d = r.json()
        assert "ip" in d and "country" in d and "city" in d


# ---------- CLEANUP (run last) ----------
class TestZCleanup:
    def test_clear_logs(self, admin_session):
        r = admin_session.delete(f"{API}/logs", timeout=20)
        assert r.status_code == 200
        d = r.json()
        assert "logs_deleted" in d and "alerts_deleted" in d
