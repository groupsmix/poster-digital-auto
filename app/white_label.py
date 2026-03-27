"""White-Label Resell module for AI Product Factory.

Feature 26: Package the system as a SaaS for other creators.
Multi-tenant support, branded dashboards, subscription tiers.
"""

import json
import logging
import secrets
from datetime import datetime

from app.database import get_db

logger = logging.getLogger(__name__)


# ── Subscription Tiers ────────────────────────────────────────────────

TIERS = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "products_per_month": 5,
        "ai_requests_per_day": 10,
        "platforms": 2,
        "features": ["basic_pipeline", "copy_center"],
        "description": "Get started with 5 products/month",
    },
    "pro": {
        "name": "Pro",
        "price_monthly": 29,
        "products_per_month": -1,  # unlimited
        "ai_requests_per_day": 100,
        "platforms": -1,  # unlimited
        "features": [
            "basic_pipeline", "copy_center", "ab_testing",
            "analytics", "content_calendar", "remix_engine",
            "email_marketing", "smart_pricing",
        ],
        "description": "Unlimited products, full feature access",
    },
    "agency": {
        "name": "Agency",
        "price_monthly": 99,
        "products_per_month": -1,
        "ai_requests_per_day": 500,
        "platforms": -1,
        "features": [
            "basic_pipeline", "copy_center", "ab_testing",
            "analytics", "content_calendar", "remix_engine",
            "email_marketing", "smart_pricing", "competitor_spy",
            "arbitrage", "affiliate_system", "piracy_protection",
            "white_label_branding", "multi_user",
        ],
        "description": "Multi-user, white-label branding, all features",
    },
}


def get_tiers() -> list[dict]:
    """Get all available subscription tiers."""
    return [{"id": k, **v} for k, v in TIERS.items()]


# ── Tenants ───────────────────────────────────────────────────────────


def create_tenant(
    name: str,
    owner_email: str,
    brand_name: str = "",
    brand_color: str = "#7c3aed",
    tier: str = "free",
    custom_domain: str = "",
) -> dict:
    """Create a new white-label tenant."""
    if tier not in TIERS:
        return {"success": False, "message": f"Invalid tier: {tier}. Must be one of: {', '.join(TIERS.keys())}"}

    api_key = f"wl_{secrets.token_urlsafe(32)}"
    tenant_slug = name.lower().replace(" ", "-").replace("_", "-")[:50]

    with get_db() as conn:
        # Check for duplicate slug
        existing = conn.execute(
            "SELECT id FROM white_label_tenants WHERE slug = ?", (tenant_slug,)
        ).fetchone()
        if existing:
            tenant_slug = f"{tenant_slug}-{secrets.token_urlsafe(4)}"

        cursor = conn.execute(
            """INSERT INTO white_label_tenants
               (name, slug, owner_email, brand_name, brand_color,
                tier, api_key, custom_domain, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
            (
                name, tenant_slug, owner_email,
                brand_name or name,
                brand_color, tier, api_key, custom_domain,
            ),
        )
        row = conn.execute(
            "SELECT * FROM white_label_tenants WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    tenant = dict(row)
    tenant["tier_details"] = TIERS[tier]

    return {
        "success": True,
        "tenant": tenant,
        "message": f"Tenant '{name}' created on {tier} tier",
    }


def get_all_tenants(status: str | None = None) -> list[dict]:
    """Get all tenants."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM white_label_tenants WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM white_label_tenants ORDER BY created_at DESC"
            ).fetchall()

    tenants = []
    for r in rows:
        t = dict(r)
        t["tier_details"] = TIERS.get(t["tier"], TIERS["free"])
        # Mask API key
        if t.get("api_key"):
            t["api_key_masked"] = f"{t['api_key'][:8]}...{t['api_key'][-4:]}"
        tenants.append(t)
    return tenants


def get_tenant(tenant_id: int) -> dict | None:
    """Get a single tenant by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM white_label_tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
    if not row:
        return None
    t = dict(row)
    t["tier_details"] = TIERS.get(t["tier"], TIERS["free"])
    return t


def update_tenant(tenant_id: int, **kwargs) -> dict | None:
    """Update a tenant."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM white_label_tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
        if not existing:
            return None

        allowed = {"name", "brand_name", "brand_color", "tier", "custom_domain",
                    "status", "owner_email"}
        fields = []
        values = []
        for key, val in kwargs.items():
            if val is not None and key in allowed:
                if key == "tier" and val not in TIERS:
                    continue
                fields.append(f"{key} = ?")
                values.append(val)

        if not fields:
            return dict(existing)

        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(tenant_id)

        conn.execute(
            f"UPDATE white_label_tenants SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM white_label_tenants WHERE id = ?", (tenant_id,)
        ).fetchone()

    t = dict(row)
    t["tier_details"] = TIERS.get(t["tier"], TIERS["free"])
    return t


def delete_tenant(tenant_id: int) -> bool:
    """Delete a tenant."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM white_label_tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM white_label_tenants WHERE id = ?", (tenant_id,))
    return True


def check_tenant_limits(tenant_id: int) -> dict:
    """Check a tenant's usage against their tier limits."""
    with get_db() as conn:
        tenant = conn.execute(
            "SELECT * FROM white_label_tenants WHERE id = ?", (tenant_id,)
        ).fetchone()
        if not tenant:
            return {"success": False, "message": "Tenant not found"}

        tenant_dict = dict(tenant)
        tier = TIERS.get(tenant_dict["tier"], TIERS["free"])

        # Count products this month
        products_count = conn.execute(
            """SELECT COUNT(*) as cnt FROM products
               WHERE created_at >= date('now', 'start of month')"""
        ).fetchone()["cnt"]

        # Count AI requests today
        ai_requests = conn.execute(
            """SELECT SUM(requests_today) as total FROM ai_status"""
        ).fetchone()["total"] or 0

    products_limit = tier["products_per_month"]
    ai_limit = tier["ai_requests_per_day"]

    return {
        "tenant_id": tenant_id,
        "tier": tenant_dict["tier"],
        "products_used": products_count,
        "products_limit": products_limit if products_limit > 0 else "unlimited",
        "products_remaining": max(0, products_limit - products_count) if products_limit > 0 else "unlimited",
        "ai_requests_used": ai_requests,
        "ai_requests_limit": ai_limit,
        "ai_requests_remaining": max(0, ai_limit - ai_requests),
        "within_limits": (
            (products_limit < 0 or products_count < products_limit)
            and ai_requests < ai_limit
        ),
    }


def get_tenant_stats() -> dict:
    """Get aggregate statistics across all tenants."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) as cnt FROM white_label_tenants").fetchone()["cnt"]
        active = conn.execute(
            "SELECT COUNT(*) as cnt FROM white_label_tenants WHERE status = 'active'"
        ).fetchone()["cnt"]
        by_tier = conn.execute(
            "SELECT tier, COUNT(*) as cnt FROM white_label_tenants GROUP BY tier"
        ).fetchall()

    tier_counts = {r["tier"]: r["cnt"] for r in by_tier}
    monthly_revenue = sum(
        TIERS.get(tier, {}).get("price_monthly", 0) * count
        for tier, count in tier_counts.items()
    )

    return {
        "total_tenants": total,
        "active_tenants": active,
        "by_tier": tier_counts,
        "monthly_revenue": monthly_revenue,
    }
