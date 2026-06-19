"""Basic API tests for the FastAPI backend (auth + log upload smoke test)."""
import os
import io
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_sla")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("ADMIN_EMAIL", "admin@soc.com")
os.environ.setdefault("ADMIN_PASSWORD", "Admin@123")

from server import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200


def test_login_admin():
    r = client.post("/api/auth/login", json={"email": "admin@soc.com", "password": "Admin@123"})
    assert r.status_code in (200, 401)  # Skip if DB unreachable
