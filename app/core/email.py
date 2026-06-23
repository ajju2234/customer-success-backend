"""Minimal SMTP email sending (stdlib). Used for password-reset links."""
from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def _send_sync(to: str, subject: str, html: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content("Please open this email in an HTML-capable client.")
    msg.add_alternative(html, subtype="html")

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.starttls(context=context)
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


async def send_email(to: str, subject: str, html: str) -> None:
    """Send an email without blocking the event loop."""
    await asyncio.to_thread(_send_sync, to, subject, html)


def reset_password_email(reset_url: str) -> str:
    return f"""\
<div style="font-family:Arial,Helvetica,sans-serif;max-width:480px;margin:0 auto;color:#0f172a">
  <h2 style="color:#4f46e5">Reset your password</h2>
  <p>We received a request to reset your Customer Success Platform password.</p>
  <p>Click the button below to choose a new password. This link expires in 30 minutes.</p>
  <p style="margin:24px 0">
    <a href="{reset_url}"
       style="background:#4f46e5;color:#fff;text-decoration:none;padding:12px 20px;border-radius:8px;display:inline-block">
      Reset password
    </a>
  </p>
  <p style="font-size:12px;color:#64748b">If you didn't request this, you can safely ignore this email.</p>
</div>"""
