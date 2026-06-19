"""Pydantic models for Security Log Analyzer."""
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, ConfigDict
import uuid


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


# ---------- USER ----------
class UserPublic(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: EmailStr
    name: str
    role: str = "analyst"
    two_factor_enabled: bool = False
    created_at: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class TOTPVerifyRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


# ---------- LOG ----------
class LogEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uid)
    user_id: str
    timestamp: datetime
    ip_address: str
    username: str
    event_type: str  # login, logout, failed_login, password_reset
    status: str  # success | failure
    risk_score: int = 0
    upload_id: Optional[str] = None
    raw: Optional[str] = None
    geo_country: Optional[str] = None
    geo_city: Optional[str] = None


# ---------- ALERT ----------
class Alert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uid)
    user_id: str
    type: str
    severity: str  # critical|high|medium|low
    message: str
    ip_address: Optional[str] = None
    username: Optional[str] = None
    mitre_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utcnow)
    acknowledged: bool = False


# ---------- ANALYSIS REPORT ----------
class AnalysisReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=_uid)
    user_id: str
    report_date: datetime = Field(default_factory=_utcnow)
    risk_score: int
    risk_level: str
    total_logs: int
    failed_logins: int
    suspicious_ips: int
    summary: str
    top_threats: List[dict] = []


# ---------- DASHBOARD / KPI ----------
class KPI(BaseModel):
    total_logs: int
    failed_logins: int
    suspicious_ips: int
    risk_score: int
    risk_level: str


class TimeSeriesPoint(BaseModel):
    bucket: str
    success: int = 0
    failure: int = 0
    total: int = 0
