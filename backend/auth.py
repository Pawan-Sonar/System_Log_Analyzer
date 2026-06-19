"""Authentication module: JWT, bcrypt, register/login/forgot/reset, TOTP 2FA."""
import os
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from io import BytesIO
import base64

import bcrypt
import jwt
import pyotp
import qrcode
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from models import (
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TOTPVerifyRequest,
    UserPublic,
)
from email_service import send_email, password_reset_email_html

logger = logging.getLogger(__name__)

JWT_ALGORITHM = "HS256"
ACCESS_MINUTES = 60 * 8  # 8 hours for analyst sessions
REFRESH_DAYS = 7
MAX_FAILED = 5
LOCKOUT_MINUTES = 15


def _jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_MINUTES),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=JWT_ALGORITHM)


def _cookie_kwargs() -> dict:
    """Cookie flags based on environment.

    In production (HTTPS, cross-site frontend/backend on Render), we need
    secure=True and samesite='none' so the browser actually stores them.
    Locally over http://localhost we keep secure=False/samesite='lax'.
    """
    is_prod = os.environ.get("ENVIRONMENT", "").lower() == "production"
    if is_prod:
        return {"httponly": True, "secure": True, "samesite": "none", "path": "/"}
    return {"httponly": True, "secure": False, "samesite": "lax", "path": "/"}


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    kw = _cookie_kwargs()
    response.set_cookie("access_token", access, max_age=ACCESS_MINUTES * 60, **kw)
    response.set_cookie("refresh_token", refresh, max_age=REFRESH_DAYS * 86400, **kw)


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def _public_user(doc: dict) -> dict:
    return {
        "id": doc["id"],
        "email": doc["email"],
        "name": doc.get("name", ""),
        "role": doc.get("role", "analyst"),
        "two_factor_enabled": doc.get("two_factor_enabled", False),
        "created_at": doc.get("created_at"),
    }


async def get_current_user(request: Request) -> dict:
    db: AsyncIOMotorDatabase = request.app.state.db
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user.pop("password_hash", None)
        user.pop("totp_secret", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------- ROUTER ----------
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(req: RegisterRequest, request: Request, response: Response):
    db = request.app.state.db
    email = req.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = secrets.token_hex(16)
    doc = {
        "id": user_id,
        "email": email,
        "name": req.name.strip(),
        "password_hash": hash_password(req.password),
        "role": "analyst",
        "two_factor_enabled": False,
        "totp_secret": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    access = create_access_token(user_id, email)
    refresh = create_refresh_token(user_id)
    _set_auth_cookies(response, access, refresh)
    return {"user": _public_user(doc), "access_token": access}


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def _check_lockout(db, identifier: str) -> None:
    rec = await db.login_attempts.find_one({"identifier": identifier})
    if not rec:
        return
    locked_until = rec.get("locked_until")
    if locked_until and datetime.fromisoformat(locked_until) > datetime.now(timezone.utc):
        raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later.")


async def _record_failure(db, identifier: str) -> None:
    rec = await db.login_attempts.find_one({"identifier": identifier})
    attempts = (rec.get("attempts", 0) if rec else 0) + 1
    update = {"identifier": identifier, "attempts": attempts}
    if attempts >= MAX_FAILED:
        update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()
        update["attempts"] = 0
    await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)


async def _clear_failures(db, identifier: str) -> None:
    await db.login_attempts.delete_one({"identifier": identifier})


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    db = request.app.state.db
    email = req.email.lower().strip()
    identifier = f"{_ip(request)}:{email}"
    await _check_lockout(db, identifier)
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not verify_password(req.password, user["password_hash"]):
        await _record_failure(db, identifier)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # 2FA check
    if user.get("two_factor_enabled"):
        if not req.totp_code:
            raise HTTPException(status_code=401, detail="2FA code required")
        secret = user.get("totp_secret")
        if not secret or not pyotp.TOTP(secret).verify(req.totp_code, valid_window=1):
            await _record_failure(db, identifier)
            raise HTTPException(status_code=401, detail="Invalid 2FA code")

    await _clear_failures(db, identifier)
    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"])
    _set_auth_cookies(response, access, refresh)
    return {"user": _public_user(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response, user=Depends(get_current_user)):
    _clear_auth_cookies(response)
    return {"status": "ok"}


@router.get("/me", response_model=UserPublic)
async def me(user=Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    db = request.app.state.db
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        new_access = create_access_token(user["id"], user["email"])
        kw = _cookie_kwargs()
        response.set_cookie("access_token", new_access, max_age=ACCESS_MINUTES * 60, **kw)
        return {"access_token": new_access}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    db = request.app.state.db
    email = req.email.lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    # Always respond OK to avoid email enumeration
    if user:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now(timezone.utc) + timedelta(hours=1))
        await db.password_reset_tokens.insert_one({
            "token": token,
            "user_id": user["id"],
            "email": email,
            "expires_at": expires,
            "used": False,
        })
        frontend = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")
        reset_link = f"{frontend}/reset-password?token={token}"
        logger.info("[FORGOT-PASSWORD] Reset link for %s: %s", email, reset_link)
        await send_email(
            to=email,
            subject="Reset your Security Log Analyzer password",
            html=password_reset_email_html(reset_link, user.get("name", "")),
            text=f"Reset your password: {reset_link}",
        )
    return {"status": "ok", "message": "If that email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, request: Request):
    db = request.app.state.db
    rec = await db.password_reset_tokens.find_one({"token": req.token})
    if not rec or rec.get("used"):
        raise HTTPException(status_code=400, detail="Invalid or used token")
    expires_at = rec.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    await db.users.update_one(
        {"id": rec["user_id"]},
        {"$set": {"password_hash": hash_password(req.new_password)}},
    )
    await db.password_reset_tokens.update_one({"token": req.token}, {"$set": {"used": True}})
    return {"status": "ok"}


# ---------- 2FA TOTP ----------
@router.post("/2fa/setup")
async def setup_2fa(request: Request, user=Depends(get_current_user)):
    """Generate a TOTP secret + QR code (returns data URI). Not enabled until verified."""
    db = request.app.state.db
    secret = pyotp.random_base32()
    issuer = os.environ.get("APP_NAME", "SecurityLogAnalyzer")
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=user["email"], issuer_name=issuer)
    img = qrcode.make(uri)
    buf = BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    # store pending secret (not yet enabled)
    await db.users.update_one({"id": user["id"]}, {"$set": {"totp_secret_pending": secret}})
    return {
        "secret": secret,
        "otpauth_uri": uri,
        "qr_code": f"data:image/png;base64,{qr_b64}",
    }


@router.post("/2fa/verify")
async def verify_2fa(req: TOTPVerifyRequest, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    full_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    secret = full_user.get("totp_secret_pending") or full_user.get("totp_secret")
    if not secret:
        raise HTTPException(status_code=400, detail="No TOTP setup in progress")
    if not pyotp.TOTP(secret).verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"two_factor_enabled": True, "totp_secret": secret},
         "$unset": {"totp_secret_pending": ""}},
    )
    return {"status": "ok", "two_factor_enabled": True}


@router.post("/2fa/disable")
async def disable_2fa(req: TOTPVerifyRequest, request: Request, user=Depends(get_current_user)):
    db = request.app.state.db
    full_user = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    secret = full_user.get("totp_secret")
    if not secret or not pyotp.TOTP(secret).verify(req.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"two_factor_enabled": False},
         "$unset": {"totp_secret": "", "totp_secret_pending": ""}},
    )
    return {"status": "ok", "two_factor_enabled": False}


async def seed_admin(db) -> None:
    """Idempotent admin seed; updates password hash if env password changed."""
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@soc.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "id": secrets.token_hex(16),
            "email": admin_email,
            "name": "Admin",
            "password_hash": hash_password(admin_password),
            "role": "admin",
            "two_factor_enabled": False,
            "totp_secret": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Seeded admin user: %s", admin_email)
    elif not verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}},
        )
