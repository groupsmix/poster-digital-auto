"""Affiliate & Referral System for AI Product Factory.

Feature 23: Auto-generate referral links, AI-created affiliate marketing kits
(pre-written tweets, blog paragraphs, email copy), commission tracking.
"""

import json
import logging
import secrets
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


# ── Affiliates ────────────────────────────────────────────────────────


def create_affiliate(
    name: str,
    email: str = "",
    commission_rate: float = 20.0,
    notes: str = "",
) -> dict:
    """Register a new affiliate partner."""
    affiliate_code = secrets.token_urlsafe(8)

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO affiliates
               (name, email, affiliate_code, commission_rate, notes, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (name, email, affiliate_code, commission_rate, notes),
        )
        row = conn.execute(
            "SELECT * FROM affiliates WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return {"success": True, "affiliate": dict(row), "message": f"Affiliate '{name}' created"}


def get_all_affiliates(status: str | None = None) -> list[dict]:
    """Get all affiliates."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM affiliates WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM affiliates ORDER BY created_at DESC"
            ).fetchall()

        affiliates = []
        for r in rows:
            a = dict(r)
            # Get stats
            stats = conn.execute(
                """SELECT COUNT(*) as total_referrals,
                          SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) as conversions,
                          SUM(CASE WHEN status = 'converted' THEN commission_amount ELSE 0 END) as total_earned
                   FROM referral_tracking WHERE affiliate_id = ?""",
                (a["id"],),
            ).fetchone()
            a["total_referrals"] = stats["total_referrals"] if stats["total_referrals"] else 0
            a["conversions"] = stats["conversions"] if stats["conversions"] else 0
            a["total_earned"] = round(stats["total_earned"], 2) if stats["total_earned"] else 0.0
            affiliates.append(a)

    return affiliates


def update_affiliate(affiliate_id: int, **kwargs) -> dict | None:
    """Update an affiliate."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM affiliates WHERE id = ?", (affiliate_id,)
        ).fetchone()
        if not existing:
            return None

        fields = []
        values = []
        for key, val in kwargs.items():
            if val is not None and key in {"name", "email", "commission_rate", "notes", "status"}:
                fields.append(f"{key} = ?")
                values.append(val)

        if not fields:
            return dict(existing)

        values.append(affiliate_id)
        conn.execute(
            f"UPDATE affiliates SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM affiliates WHERE id = ?", (affiliate_id,)
        ).fetchone()
    return dict(row)


def delete_affiliate(affiliate_id: int) -> bool:
    """Delete an affiliate and their referral links."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM affiliates WHERE id = ?", (affiliate_id,)
        ).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM referral_links WHERE affiliate_id = ?", (affiliate_id,))
        conn.execute("DELETE FROM referral_tracking WHERE affiliate_id = ?", (affiliate_id,))
        conn.execute("DELETE FROM affiliates WHERE id = ?", (affiliate_id,))
    return True


# ── Referral Links ────────────────────────────────────────────────────


def generate_referral_link(affiliate_id: int, product_id: int) -> dict:
    """Generate a unique referral link for an affiliate + product."""
    with get_db() as conn:
        affiliate = conn.execute(
            "SELECT * FROM affiliates WHERE id = ?", (affiliate_id,)
        ).fetchone()
        if not affiliate:
            return {"success": False, "message": "Affiliate not found"}

        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        # Check if link already exists
        existing = conn.execute(
            "SELECT * FROM referral_links WHERE affiliate_id = ? AND product_id = ?",
            (affiliate_id, product_id),
        ).fetchone()
        if existing:
            return {
                "success": True,
                "link": dict(existing),
                "message": "Referral link already exists",
            }

        ref_code = f"{affiliate['affiliate_code']}-{secrets.token_urlsafe(4)}"
        cursor = conn.execute(
            """INSERT INTO referral_links
               (affiliate_id, product_id, ref_code, clicks, conversions)
               VALUES (?, ?, ?, 0, 0)""",
            (affiliate_id, product_id, ref_code),
        )
        row = conn.execute(
            "SELECT * FROM referral_links WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return {
        "success": True,
        "link": dict(row),
        "referral_url": f"?ref={ref_code}",
        "message": f"Referral link created for product '{product['name']}'",
    }


def get_referral_links(affiliate_id: int | None = None, product_id: int | None = None) -> list[dict]:
    """Get referral links with optional filters."""
    with get_db() as conn:
        query = """SELECT rl.*, a.name as affiliate_name, p.name as product_name
                   FROM referral_links rl
                   JOIN affiliates a ON rl.affiliate_id = a.id
                   JOIN products p ON rl.product_id = p.id
                   WHERE 1=1"""
        params: list = []

        if affiliate_id is not None:
            query += " AND rl.affiliate_id = ?"
            params.append(affiliate_id)
        if product_id is not None:
            query += " AND rl.product_id = ?"
            params.append(product_id)

        query += " ORDER BY rl.created_at DESC"
        rows = conn.execute(query, params).fetchall()

    return [dict(r) for r in rows]


# ── Referral Tracking ─────────────────────────────────────────────────


def track_referral_click(ref_code: str) -> dict:
    """Track a click on a referral link."""
    with get_db() as conn:
        link = conn.execute(
            "SELECT * FROM referral_links WHERE ref_code = ?", (ref_code,)
        ).fetchone()
        if not link:
            return {"success": False, "message": "Invalid referral code"}

        conn.execute(
            "UPDATE referral_links SET clicks = clicks + 1 WHERE id = ?",
            (link["id"],),
        )

        conn.execute(
            """INSERT INTO referral_tracking
               (affiliate_id, product_id, ref_code, status)
               VALUES (?, ?, ?, 'clicked')""",
            (link["affiliate_id"], link["product_id"], ref_code),
        )

    return {"success": True, "message": "Click tracked"}


def track_referral_conversion(ref_code: str, revenue: float) -> dict:
    """Track a conversion (sale) from a referral."""
    with get_db() as conn:
        link = conn.execute(
            "SELECT rl.*, a.commission_rate
             FROM referral_links rl
             JOIN affiliates a ON rl.affiliate_id = a.id
             WHERE rl.ref_code = ?",
            (ref_code,),
        ).fetchone()
        if not link:
            return {"success": False, "message": "Invalid referral code"}

        commission = round(revenue * link["commission_rate"] / 100, 2)

        conn.execute(
            "UPDATE referral_links SET conversions = conversions + 1 WHERE id = ?",
            (link["id"],),
        )

        conn.execute(
            """INSERT INTO referral_tracking
               (affiliate_id, product_id, ref_code, status,
                sale_amount, commission_amount)
               VALUES (?, ?, ?, 'converted', ?, ?)""",
            (link["affiliate_id"], link["product_id"], ref_code, revenue, commission),
        )

        # Update affiliate total earnings
        conn.execute(
            "UPDATE affiliates SET total_earned = total_earned + ? WHERE id = ?",
            (commission, link["affiliate_id"]),
        )

    return {
        "success": True,
        "commission": commission,
        "message": f"Conversion tracked. Commission: ${commission:.2f}",
    }


def get_referral_stats(affiliate_id: int | None = None) -> dict:
    """Get overall referral statistics."""
    with get_db() as conn:
        if affiliate_id:
            stats = conn.execute(
                """SELECT
                      COUNT(*) as total_events,
                      SUM(CASE WHEN status = 'clicked' THEN 1 ELSE 0 END) as total_clicks,
                      SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) as total_conversions,
                      SUM(CASE WHEN status = 'converted' THEN sale_amount ELSE 0 END) as total_revenue,
                      SUM(CASE WHEN status = 'converted' THEN commission_amount ELSE 0 END) as total_commissions
                   FROM referral_tracking WHERE affiliate_id = ?""",
                (affiliate_id,),
            ).fetchone()
        else:
            stats = conn.execute(
                """SELECT
                      COUNT(*) as total_events,
                      SUM(CASE WHEN status = 'clicked' THEN 1 ELSE 0 END) as total_clicks,
                      SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) as total_conversions,
                      SUM(CASE WHEN status = 'converted' THEN sale_amount ELSE 0 END) as total_revenue,
                      SUM(CASE WHEN status = 'converted' THEN commission_amount ELSE 0 END) as total_commissions
                   FROM referral_tracking"""
            ).fetchone()

    return {
        "total_clicks": stats["total_clicks"] or 0,
        "total_conversions": stats["total_conversions"] or 0,
        "total_revenue": round(stats["total_revenue"] or 0, 2),
        "total_commissions": round(stats["total_commissions"] or 0, 2),
        "conversion_rate": round(
            (stats["total_conversions"] or 0) / max(stats["total_clicks"] or 1, 1) * 100, 1
        ),
    }


# ── Affiliate Marketing Kit ──────────────────────────────────────────


async def generate_affiliate_kit(product_id: int) -> dict:
    """AI generates a complete affiliate marketing kit for a product."""
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_dict = dict(product)

        variant = conn.execute(
            "SELECT title, description, price, platform FROM product_variants WHERE product_id = ? LIMIT 1",
            (product_id,),
        ).fetchone()

    variant_info = dict(variant) if variant else {}

    prompt = f"""You are an affiliate marketing expert. Create a complete marketing kit that affiliates can use to promote this digital product.

Product: {product_dict['name']}
Type: {product_dict.get('product_type', 'digital')}
Brief: {product_dict.get('brief', '')}
Price: {variant_info.get('price', 'TBD')}
Description: {variant_info.get('description', '')[:300]}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "tweets": [
    "Pre-written tweet 1 (max 280 chars)",
    "Pre-written tweet 2 (max 280 chars)",
    "Pre-written tweet 3 (max 280 chars)"
  ],
  "blog_paragraphs": [
    "Blog paragraph 1 - Review style",
    "Blog paragraph 2 - How-to style"
  ],
  "email_copy": {{
    "subject": "Email subject line",
    "body": "Email body (plain text, under 200 words)"
  }},
  "instagram_caption": "Instagram caption with hashtags",
  "facebook_post": "Facebook post text",
  "key_selling_points": ["point 1", "point 2", "point 3"],
  "target_audience": "Who to target",
  "best_platforms": ["platform 1", "platform 2"]
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {"success": False, "message": f"Kit generation failed: {ai_result['message']}"}

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
        return {"success": False, "message": "Failed to parse affiliate kit response"}

    return {
        "success": True,
        "product_id": product_id,
        "product_name": product_dict["name"],
        "kit": data,
        "provider": ai_result.get("provider"),
        "generated_at": datetime.utcnow().isoformat(),
        "message": "Affiliate marketing kit generated",
    }
