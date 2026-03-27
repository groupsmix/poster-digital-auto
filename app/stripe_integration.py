"""Stripe Integration Stub for AI Product Factory.

Feature 26 Enhancement: Subscription billing via Stripe.
This is a stub implementation that simulates Stripe subscription management.
Replace with real Stripe API calls when ready to go live.
"""

import logging
import os
from datetime import datetime

from app.database import get_db
from app.white_label import TIERS, get_tenant, update_tenant

logger = logging.getLogger(__name__)

# In production, set STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET env vars
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_CONFIGURED = bool(STRIPE_SECRET_KEY)

# Price IDs would map to real Stripe price IDs in production
STRIPE_PRICE_IDS = {
    "free": None,
    "pro": "price_pro_monthly_stub",
    "agency": "price_agency_monthly_stub",
}


def get_stripe_status() -> dict:
    """Get current Stripe integration status."""
    return {
        "configured": STRIPE_CONFIGURED,
        "mode": "live" if STRIPE_CONFIGURED else "stub",
        "tiers": {
            tier_id: {
                "name": tier["name"],
                "price_monthly": tier["price_monthly"],
                "stripe_price_id": STRIPE_PRICE_IDS.get(tier_id),
            }
            for tier_id, tier in TIERS.items()
        },
        "message": (
            "Stripe is configured and ready"
            if STRIPE_CONFIGURED
            else "Stripe is in stub mode. Set STRIPE_SECRET_KEY to enable."
        ),
    }


def create_subscription(tenant_id: int, tier: str) -> dict:
    """Create or update a subscription for a tenant.

    In stub mode, this directly updates the tenant's tier.
    In production, this would create a Stripe Checkout session.
    """
    if tier not in TIERS:
        return {"success": False, "message": f"Invalid tier: {tier}"}

    tenant = get_tenant(tenant_id)
    if not tenant:
        return {"success": False, "message": "Tenant not found"}

    if STRIPE_CONFIGURED:
        # Production: would call stripe.checkout.Session.create()
        # and return the checkout URL
        logger.info("Would create Stripe checkout for tenant %d, tier %s", tenant_id, tier)

    # Update tenant tier directly (stub behavior)
    updated = update_tenant(tenant_id, tier=tier)
    if not updated:
        return {"success": False, "message": "Failed to update tenant"}

    # Record the subscription event
    with get_db() as conn:
        conn.execute(
            """INSERT INTO analytics (product_id, platform, event_type, revenue, data, recorded_at)
               VALUES (NULL, 'stripe', 'subscription', ?, ?, ?)""",
            (
                TIERS[tier]["price_monthly"],
                f'{{"tenant_id": {tenant_id}, "tier": "{tier}", "mode": "{"live" if STRIPE_CONFIGURED else "stub"}"}}',
                datetime.utcnow().isoformat(),
            ),
        )

    return {
        "success": True,
        "tenant_id": tenant_id,
        "tier": tier,
        "price_monthly": TIERS[tier]["price_monthly"],
        "mode": "live" if STRIPE_CONFIGURED else "stub",
        "message": f"Subscription updated to {tier} tier",
        "checkout_url": None if not STRIPE_CONFIGURED else "https://checkout.stripe.com/stub",
    }


def cancel_subscription(tenant_id: int) -> dict:
    """Cancel a tenant's subscription (downgrade to free).

    In stub mode, directly sets tier to free.
    In production, would cancel the Stripe subscription.
    """
    tenant = get_tenant(tenant_id)
    if not tenant:
        return {"success": False, "message": "Tenant not found"}

    current_tier = tenant.get("tier", "free")
    if current_tier == "free":
        return {"success": True, "message": "Already on free tier", "tenant_id": tenant_id}

    if STRIPE_CONFIGURED:
        logger.info("Would cancel Stripe subscription for tenant %d", tenant_id)

    updated = update_tenant(tenant_id, tier="free")
    if not updated:
        return {"success": False, "message": "Failed to update tenant"}

    return {
        "success": True,
        "tenant_id": tenant_id,
        "previous_tier": current_tier,
        "current_tier": "free",
        "mode": "live" if STRIPE_CONFIGURED else "stub",
        "message": f"Subscription cancelled. Downgraded from {current_tier} to free.",
    }


def get_invoices(tenant_id: int) -> dict:
    """Get billing invoices for a tenant.

    In stub mode, returns subscription events from analytics.
    In production, would fetch from Stripe API.
    """
    tenant = get_tenant(tenant_id)
    if not tenant:
        return {"invoices": [], "count": 0, "message": "Tenant not found"}

    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM analytics
               WHERE platform = 'stripe' AND event_type = 'subscription'
               AND data LIKE ?
               ORDER BY recorded_at DESC LIMIT 20""",
            (f'%"tenant_id": {tenant_id}%',),
        ).fetchall()

    invoices = []
    for r in rows:
        invoices.append({
            "id": r["id"],
            "amount": r["revenue"],
            "date": r["recorded_at"],
            "status": "paid",
            "mode": "stub" if not STRIPE_CONFIGURED else "live",
        })

    return {
        "invoices": invoices,
        "count": len(invoices),
        "tenant_id": tenant_id,
        "mode": "live" if STRIPE_CONFIGURED else "stub",
    }
