"""Email Marketing module for AI Product Factory.

Generates email campaigns with subject line variations,
promo email body, day 3 follow-up (tip/value), and
day 7 follow-up (related product upsell).
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


async def generate_email_campaign(product_id: int) -> dict:
    """Generate a full email campaign for a product.

    Creates:
    - 3 subject line variations
    - Short promo email body
    - Day 3 follow-up (tip/value-focused)
    - Day 7 follow-up (related product upsell)
    """
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_dict = dict(product)

        # Get variant info for richer context
        variants = conn.execute(
            "SELECT title, description, platform, price FROM product_variants WHERE product_id = ? LIMIT 3",
            (product_id,),
        ).fetchall()
        variant_info = [dict(v) for v in variants]

        # Check if campaign already exists
        existing = conn.execute(
            "SELECT * FROM email_campaigns WHERE product_id = ?",
            (product_id,),
        ).fetchone()

    product_name = product_dict["name"]
    brief = product_dict.get("brief", "")
    variant_context = ""
    if variant_info:
        variant_context = "\n".join(
            f"- {v.get('platform', 'N/A')}: {v.get('title', '')} (Price: {v.get('price', 'N/A')})"
            for v in variant_info
        )

    # Fetch upsell suggestions to embed in follow-up emails
    upsell_context = ""
    try:
        with get_db() as upsell_conn:
            related = upsell_conn.execute(
                """SELECT p.id, p.name, p.product_type
                   FROM products p WHERE p.id != ? AND p.status = 'published'
                   ORDER BY p.created_at DESC LIMIT 5""",
                (product_id,),
            ).fetchall()
            if related:
                upsell_context = "\n\nRelated products to suggest in follow-up emails:\n" + "\n".join(
                    f"- {r['name']} ({r['product_type']})" for r in related
                )
    except Exception:
        pass

    prompt = f"""You are an email marketing expert for digital product creators.

Create a complete email campaign for this product:

Product: {product_name}
Brief: {brief}
Variants:
{variant_context or 'No variants yet'}
{upsell_context}

Generate a 3-email campaign sequence. For the Day 3 and Day 7 follow-ups, include
specific upsell/cross-sell product suggestions from the related products above.
Return ONLY valid JSON (no markdown, no code fences):
{{
  "subject_lines": [
    "Subject line 1 - curiosity/benefit angle",
    "Subject line 2 - urgency/scarcity angle",
    "Subject line 3 - social proof/results angle"
  ],
  "promo_email": {{
    "subject": "Best subject line for the launch email",
    "body": "Full HTML-free email body (plain text with line breaks). Include: hook, value prop, features, CTA, P.S. line. Keep under 300 words."
  }},
  "day3_followup": {{
    "subject": "Subject for day 3 follow-up",
    "body": "Tip/value email. Share a useful tip related to the product's niche. Soft mention of the product. Include a 'You might also like' section with 1-2 related products. Keep under 200 words."
  }},
  "day7_followup": {{
    "subject": "Subject for day 7 follow-up",
    "body": "Upsell/reminder email. Mention the product again, add urgency or bonus. Include specific cross-sell suggestions with short pitches for 1-2 related products. Keep under 200 words."
  }}
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {
            "success": False,
            "message": f"AI email generation failed: {ai_result['message']}",
        }

    raw_text = ai_result["result"]
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"success": False, "message": "Failed to parse AI email response"}

    subject_lines = data.get("subject_lines", [])
    promo = data.get("promo_email", {})
    day3 = data.get("day3_followup", {})
    day7 = data.get("day7_followup", {})

    with get_db() as conn:
        if existing:
            # Update existing campaign
            conn.execute(
                """UPDATE email_campaigns
                   SET subject_lines = ?, email_body = ?,
                       follow_up_day3 = ?, follow_up_day7 = ?,
                       status = 'draft'
                   WHERE product_id = ?""",
                (
                    json.dumps(subject_lines),
                    json.dumps(promo),
                    json.dumps(day3),
                    json.dumps(day7),
                    product_id,
                ),
            )
            campaign = conn.execute(
                "SELECT * FROM email_campaigns WHERE product_id = ?",
                (product_id,),
            ).fetchone()
        else:
            cursor = conn.execute(
                """INSERT INTO email_campaigns
                   (product_id, subject_lines, email_body, follow_up_day3, follow_up_day7, status)
                   VALUES (?, ?, ?, ?, ?, 'draft')""",
                (
                    product_id,
                    json.dumps(subject_lines),
                    json.dumps(promo),
                    json.dumps(day3),
                    json.dumps(day7),
                ),
            )
            campaign = conn.execute(
                "SELECT * FROM email_campaigns WHERE id = ?",
                (cursor.lastrowid,),
            ).fetchone()

    campaign_dict = dict(campaign)
    campaign_dict["subject_lines"] = _parse_json(campaign_dict.get("subject_lines", "[]"), [])
    campaign_dict["email_body"] = _parse_json(campaign_dict.get("email_body", "{}"), {})
    campaign_dict["follow_up_day3"] = _parse_json(campaign_dict.get("follow_up_day3", "{}"), {})
    campaign_dict["follow_up_day7"] = _parse_json(campaign_dict.get("follow_up_day7", "{}"), {})

    return {
        "success": True,
        "campaign": campaign_dict,
        "provider": ai_result.get("provider"),
        "message": "Email campaign generated with 3 subject lines and 3 emails",
    }


def get_email_campaign(product_id: int) -> dict | None:
    """Get the email campaign for a product."""
    with get_db() as conn:
        campaign = conn.execute(
            "SELECT * FROM email_campaigns WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if not campaign:
            return None

    campaign_dict = dict(campaign)
    campaign_dict["subject_lines"] = _parse_json(campaign_dict.get("subject_lines", "[]"), [])
    campaign_dict["email_body"] = _parse_json(campaign_dict.get("email_body", "{}"), {})
    campaign_dict["follow_up_day3"] = _parse_json(campaign_dict.get("follow_up_day3", "{}"), {})
    campaign_dict["follow_up_day7"] = _parse_json(campaign_dict.get("follow_up_day7", "{}"), {})
    return campaign_dict


def _parse_json(value: str, default=None):
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
