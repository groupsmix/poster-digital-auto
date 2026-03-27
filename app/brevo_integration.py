"""Brevo (formerly Sendinblue) email integration for AI Product Factory.

Feature 20 Enhancement: Actually send AI-generated email campaigns
using the Brevo transactional email API.
"""

import json
import logging
import os
from datetime import datetime, timedelta

import httpx

from app.database import get_db

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3"


def _get_api_key() -> str | None:
    """Get the Brevo API key from environment or settings."""
    key = os.getenv("BREVO_API_KEY", "")
    if key:
        return key

    # Fallback: check settings_preferences table
    with get_db() as conn:
        row = conn.execute(
            "SELECT value FROM settings_preferences WHERE key = 'brevo_api_key'"
        ).fetchone()
        if row and row["value"]:
            return row["value"]

    return None


def is_configured() -> bool:
    """Check if Brevo API is configured."""
    return bool(_get_api_key())


async def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
    sender_name: str = "AI Product Factory",
    sender_email: str = "noreply@example.com",
) -> dict:
    """Send a single transactional email via Brevo API."""
    api_key = _get_api_key()
    if not api_key:
        return {
            "success": False,
            "message": "Brevo API key not configured. Set BREVO_API_KEY env var or add in Settings > API Keys.",
        }

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{BREVO_API_URL}/smtp/email",
                json=payload,
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            return {
                "success": True,
                "message_id": data.get("messageId", ""),
                "message": "Email sent successfully",
            }
        else:
            return {
                "success": False,
                "status_code": resp.status_code,
                "message": f"Brevo API error: {resp.text}",
            }

    except httpx.HTTPError as e:
        return {"success": False, "message": f"HTTP error sending email: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Error sending email: {e}"}


async def send_campaign_email(
    campaign_id: int,
    email_type: str,
    to_email: str,
    to_name: str = "",
) -> dict:
    """Send a specific email from an existing campaign.

    email_type: 'promo', 'day3_followup', or 'day7_followup'
    """
    with get_db() as conn:
        campaign = conn.execute(
            "SELECT * FROM email_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if not campaign:
            return {"success": False, "message": "Campaign not found"}

        campaign_dict = dict(campaign)

    # Parse campaign data
    subject_lines = campaign_dict.get("subject_lines", "[]")
    try:
        subjects = json.loads(subject_lines) if isinstance(subject_lines, str) else subject_lines
    except (json.JSONDecodeError, TypeError):
        subjects = ["Your Digital Product"]

    email_content_map = {
        "promo": ("promo_email", subjects[0] if subjects else "Special Offer"),
        "day3_followup": ("day3_followup", subjects[1] if len(subjects) > 1 else "Quick Follow-Up"),
        "day7_followup": ("day7_followup", subjects[2] if len(subjects) > 2 else "Last Chance"),
    }

    if email_type not in email_content_map:
        return {"success": False, "message": f"Invalid email type: {email_type}. Use: promo, day3_followup, day7_followup"}

    content_field, subject = email_content_map[email_type]
    body = campaign_dict.get(content_field, "")

    if not body:
        return {"success": False, "message": f"No {email_type} content in campaign"}

    # Wrap in simple HTML template
    html = f"""<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
{body.replace(chr(10), '<br>')}
</body>
</html>"""

    result = await send_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        html_content=html,
    )

    # Update campaign status
    if result["success"]:
        with get_db() as conn:
            now = datetime.utcnow().isoformat()
            status_field = f"{email_type}_sent"
            # Store send status in the campaign record
            conn.execute(
                """UPDATE email_campaigns
                   SET status = 'sent', updated_at = ?
                   WHERE id = ?""",
                (now, campaign_id),
            )

    return {
        **result,
        "campaign_id": campaign_id,
        "email_type": email_type,
        "to_email": to_email,
    }


async def schedule_campaign_sequence(
    campaign_id: int,
    to_email: str,
    to_name: str = "",
) -> dict:
    """Schedule the full email sequence: promo now, Day 3, Day 7.

    Note: In production, you'd use Brevo's automation workflows.
    This creates scheduled entries that a cron job would process.
    """
    with get_db() as conn:
        campaign = conn.execute(
            "SELECT * FROM email_campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if not campaign:
            return {"success": False, "message": "Campaign not found"}

        now = datetime.utcnow()
        schedule = [
            {"email_type": "promo", "send_at": now.isoformat(), "status": "pending"},
            {"email_type": "day3_followup", "send_at": (now + timedelta(days=3)).isoformat(), "status": "pending"},
            {"email_type": "day7_followup", "send_at": (now + timedelta(days=7)).isoformat(), "status": "pending"},
        ]

        conn.execute(
            """UPDATE email_campaigns
               SET status = 'scheduled', schedule_data = ?, updated_at = ?
               WHERE id = ?""",
            (json.dumps({"to_email": to_email, "to_name": to_name, "schedule": schedule}),
             now.isoformat(), campaign_id),
        )

    # Send the promo email immediately
    promo_result = await send_campaign_email(campaign_id, "promo", to_email, to_name)

    return {
        "success": True,
        "campaign_id": campaign_id,
        "promo_sent": promo_result.get("success", False),
        "day3_scheduled": (now + timedelta(days=3)).isoformat(),
        "day7_scheduled": (now + timedelta(days=7)).isoformat(),
        "message": "Campaign sequence scheduled",
    }


def get_brevo_status() -> dict:
    """Get Brevo integration status and account info."""
    configured = is_configured()
    return {
        "configured": configured,
        "provider": "Brevo (Sendinblue)",
        "api_url": BREVO_API_URL,
        "status": "ready" if configured else "not_configured",
        "message": "Brevo API is ready" if configured else "Set BREVO_API_KEY to enable email sending",
    }
