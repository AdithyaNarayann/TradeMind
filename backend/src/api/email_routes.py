"""
Email settings routes.

GET    /api/v1/email/settings      → get email settings for current user
PUT    /api/v1/email/settings      → update email settings
POST   /api/v1/email/test          → send a test email
"""
import aiomysql
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional

import asyncio

from ..db.mysql import get_conn
from .auth_routes import get_current_user
from ..services.email_service import EmailService, template_test_email

router = APIRouter(prefix="/api/v1/email", tags=["Email"])


# ── Models ─────────────────────────────────────────────────────────

class EmailSettingsUpdate(BaseModel):
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""
    from_name: str = "TradeMind"
    use_tls: bool = True
    notifications_enabled: bool = True
    notify_on_deal: bool = True
    notify_on_new_session: bool = True
    notify_on_api_key: bool = True


class TestEmailRequest(BaseModel):
    to_email: Optional[str] = None  # defaults to user's email


# ── Helpers ────────────────────────────────────────────────────────

async def _ensure_table():
    """Create email_settings table if it doesn't exist."""
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS email_settings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    smtp_host VARCHAR(255) DEFAULT 'smtp.gmail.com',
                    smtp_port INT DEFAULT 587,
                    smtp_user VARCHAR(255) DEFAULT '',
                    smtp_password VARCHAR(255) DEFAULT '',
                    from_email VARCHAR(255) DEFAULT '',
                    from_name VARCHAR(100) DEFAULT 'TradeMind',
                    use_tls TINYINT(1) DEFAULT 1,
                    notifications_enabled TINYINT(1) DEFAULT 1,
                    notify_on_deal TINYINT(1) DEFAULT 1,
                    notify_on_new_session TINYINT(1) DEFAULT 1,
                    notify_on_api_key TINYINT(1) DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)


def _build_service(settings: dict) -> EmailService:
    """Build an EmailService from a settings dict."""
    return EmailService(
        smtp_host=settings["smtp_host"],
        smtp_port=settings["smtp_port"],
        smtp_user=settings["smtp_user"],
        smtp_password=settings["smtp_password"],
        from_email=settings["from_email"],
        from_name=settings.get("from_name", "TradeMind"),
        use_tls=bool(settings.get("use_tls", True)),
    )


async def get_user_email_settings(user_id: int) -> Optional[dict]:
    """Fetch email settings for a user. Returns None if not configured."""
    async with get_conn() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT * FROM email_settings WHERE user_id = %s", (user_id,)
            )
            return await cur.fetchone()


async def send_notification_email(user_id: int, subject: str, html_body: str) -> bool:
    """
    Send a notification email to a user if they have email configured.
    Used by other modules (chat sessions, API keys, etc.) to trigger emails.
    Returns True if sent successfully, False otherwise.
    """
    settings = await get_user_email_settings(user_id)
    if not settings or not settings.get("notifications_enabled"):
        return False
    if not settings.get("smtp_user") or not settings.get("smtp_password"):
        return False

    service = _build_service(settings)
    to_email = settings["from_email"] or settings["smtp_user"]
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, service.send, to_email, subject, html_body)


# ── Routes ─────────────────────────────────────────────────────────

@router.get("/settings")
async def get_email_settings(user=Depends(get_current_user)):
    """Get email settings for the current user."""
    await _ensure_table()
    settings = await get_user_email_settings(user["id"])
    if not settings:
        return {
            "configured": False,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_password": "",
            "from_email": "",
            "from_name": "TradeMind",
            "use_tls": True,
            "notifications_enabled": True,
            "notify_on_deal": True,
            "notify_on_new_session": True,
            "notify_on_api_key": True,
        }
    # Mask password for response
    masked_pw = "•" * len(settings["smtp_password"]) if settings["smtp_password"] else ""
    return {
        "configured": True,
        "smtp_host": settings["smtp_host"],
        "smtp_port": settings["smtp_port"],
        "smtp_user": settings["smtp_user"],
        "smtp_password": masked_pw,
        "from_email": settings["from_email"],
        "from_name": settings["from_name"] or "TradeMind",
        "use_tls": bool(settings["use_tls"]),
        "notifications_enabled": bool(settings["notifications_enabled"]),
        "notify_on_deal": bool(settings["notify_on_deal"]),
        "notify_on_new_session": bool(settings["notify_on_new_session"]),
        "notify_on_api_key": bool(settings["notify_on_api_key"]),
    }


@router.put("/settings")
async def update_email_settings(body: EmailSettingsUpdate, user=Depends(get_current_user)):
    """Create or update email settings."""
    await _ensure_table()
    async with get_conn() as conn:
        async with conn.cursor() as cur:
            # Upsert
            await cur.execute(
                """INSERT INTO email_settings
                   (user_id, smtp_host, smtp_port, smtp_user, smtp_password,
                    from_email, from_name, use_tls,
                    notifications_enabled, notify_on_deal, notify_on_new_session, notify_on_api_key)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                    smtp_host = VALUES(smtp_host),
                    smtp_port = VALUES(smtp_port),
                    smtp_user = VALUES(smtp_user),
                    smtp_password = IF(VALUES(smtp_password) = '' OR VALUES(smtp_password) LIKE %s,
                                       smtp_password, VALUES(smtp_password)),
                    from_email = VALUES(from_email),
                    from_name = VALUES(from_name),
                    use_tls = VALUES(use_tls),
                    notifications_enabled = VALUES(notifications_enabled),
                    notify_on_deal = VALUES(notify_on_deal),
                    notify_on_new_session = VALUES(notify_on_new_session),
                    notify_on_api_key = VALUES(notify_on_api_key)
                """,
                (
                    user["id"],
                    body.smtp_host, body.smtp_port,
                    body.smtp_user, body.smtp_password,
                    body.from_email, body.from_name,
                    int(body.use_tls),
                    int(body.notifications_enabled),
                    int(body.notify_on_deal),
                    int(body.notify_on_new_session),
                    int(body.notify_on_api_key),
                    "•%",  # pattern for masked password
                ),
            )
    return {"updated": True}


@router.post("/test")
async def send_test_email(body: TestEmailRequest = None, user=Depends(get_current_user)):
    """Send a test email to verify configuration."""
    await _ensure_table()
    settings = await get_user_email_settings(user["id"])
    if not settings or not settings.get("smtp_user") or not settings.get("smtp_password"):
        raise HTTPException(status_code=400, detail="Email not configured. Save your SMTP settings first.")

    service = _build_service(settings)
    to_email = (body and body.to_email) or settings["from_email"] or settings["smtp_user"]
    subject, html = template_test_email(user["full_name"])

    success = service.send(to_email, subject, html)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send test email. Check your SMTP settings.")
    return {"sent": True, "to": to_email}
