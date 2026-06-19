"""Email service. Logs to console; switches to Resend if RESEND_API_KEY env var is set.

This abstraction lets you plug in Resend later via env vars without code changes.
"""
import os
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def send_email(*, to: str, subject: str, html: str, text: Optional[str] = None) -> dict:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")

    if not api_key:
        # Placeholder mode: log content for development.
        logger.info("=" * 70)
        logger.info("[EMAIL PLACEHOLDER] (set RESEND_API_KEY to enable real delivery)")
        logger.info("To: %s", to)
        logger.info("From: %s", sender)
        logger.info("Subject: %s", subject)
        if text:
            logger.info("Text:\n%s", text)
        logger.info("HTML:\n%s", html)
        logger.info("=" * 70)
        return {"status": "logged", "provider": "console"}

    try:
        import resend  # lazy import
        resend.api_key = api_key
        params = {"from": sender, "to": [to], "subject": subject, "html": html}
        if text:
            params["text"] = text
        result = await asyncio.to_thread(resend.Emails.send, params)
        return {"status": "sent", "provider": "resend", "id": result.get("id")}
    except Exception as e:  # noqa: BLE001
        logger.error("Resend send failed: %s", e)
        return {"status": "error", "provider": "resend", "error": str(e)}


def password_reset_email_html(reset_link: str, name: str = "") -> str:
    greet = f"Hi {name}," if name else "Hi,"
    return f"""
    <table style="background:#0A0A0A;color:#F9FAFB;font-family:Arial;padding:24px;width:100%">
      <tr><td>
        <h2 style="color:#3B82F6;margin:0 0 16px">Security Log Analyzer</h2>
        <p>{greet}</p>
        <p>We received a request to reset your password. Click the button below to continue.</p>
        <p style="margin:24px 0">
          <a href="{reset_link}" style="background:#3B82F6;color:#000;padding:12px 20px;text-decoration:none;border-radius:4px;font-weight:bold">Reset Password</a>
        </p>
        <p style="font-size:12px;color:#9CA3AF">If the button does not work, copy this link:<br>{reset_link}</p>
        <p style="font-size:12px;color:#9CA3AF">This link expires in 1 hour. If you did not request this, ignore this email.</p>
      </td></tr>
    </table>
    """
