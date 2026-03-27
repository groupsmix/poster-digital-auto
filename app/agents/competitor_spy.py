"""Competitor Spy Agent for AI Product Factory.

Feature 8: Monitors competitors automatically - tracks new products from
top sellers on Gumroad/Payhip/Etsy, price changes, trending products in
your niches, gaps in the market.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "research"


async def run_competitor_scan(niches: str = "") -> dict:
    """Run a competitor analysis scan using AI.

    Analyzes the competitive landscape across digital product platforms.
    """
    # Gather context from existing products and niches
    with get_db() as conn:
        products = conn.execute(
            "SELECT name, product_type FROM products ORDER BY created_at DESC LIMIT 20"
        ).fetchall()
        existing_niches = conn.execute(
            "SELECT product_name, competition FROM niche_ideas ORDER BY demand_score DESC LIMIT 10"
        ).fetchall()

    product_context = ", ".join(p["name"] for p in products) if products else "No products yet"
    niche_context = ", ".join(n["product_name"] for n in existing_niches) if existing_niches else "No niches discovered"

    prompt = f"""You are a competitive intelligence analyst for digital product creators selling on Gumroad, Payhip, and Etsy.

Current user's products: {product_context}
Known niches: {niche_context}
Additional focus niches: {niches or 'General digital products (planners, templates, printables)'}

Perform a comprehensive competitor analysis. Return ONLY valid JSON (no markdown, no code fences):
{{
  "competitors": [
    {{
      "seller_name": "Competitor seller name or store",
      "platform": "Gumroad/Payhip/Etsy",
      "top_products": ["product 1", "product 2"],
      "price_range": "$X-$Y",
      "strengths": "What they do well",
      "weaknesses": "Where they fall short",
      "threat_level": "low/medium/high"
    }}
  ],
  "price_alerts": [
    {{
      "product_type": "Type of product",
      "your_price": "$X",
      "competitor_price": "$Y",
      "platform": "Platform name",
      "recommendation": "What to do about it"
    }}
  ],
  "market_gaps": [
    {{
      "gap": "Description of the gap",
      "opportunity_score": 8,
      "difficulty": "easy/medium/hard",
      "suggested_product": "What product to create",
      "estimated_price": "$X"
    }}
  ],
  "trending_products": [
    {{
      "product_type": "What's trending",
      "platforms": ["Where it's trending"],
      "growth_rate": "Estimated growth",
      "time_to_act": "How soon to act"
    }}
  ],
  "summary": "Overall competitive landscape summary in 2-3 sentences"
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {
            "success": False,
            "message": f"Competitor scan failed: {ai_result['message']}",
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
        return {"success": False, "message": "Failed to parse competitor scan results"}

    # Store results in DB
    with get_db() as conn:
        for comp in data.get("competitors", []):
            conn.execute(
                """INSERT INTO competitor_tracking
                   (seller_name, platform, top_products, price_range,
                    strengths, weaknesses, threat_level)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    comp.get("seller_name", ""),
                    comp.get("platform", ""),
                    json.dumps(comp.get("top_products", [])),
                    comp.get("price_range", ""),
                    comp.get("strengths", ""),
                    comp.get("weaknesses", ""),
                    comp.get("threat_level", "medium"),
                ),
            )

        for alert in data.get("price_alerts", []):
            conn.execute(
                """INSERT INTO competitor_alerts
                   (alert_type, product_type, details, platform, recommendation)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    "price_change",
                    alert.get("product_type", ""),
                    json.dumps(alert),
                    alert.get("platform", ""),
                    alert.get("recommendation", ""),
                ),
            )

        for gap in data.get("market_gaps", []):
            conn.execute(
                """INSERT INTO competitor_alerts
                   (alert_type, product_type, details, platform, recommendation)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    "market_gap",
                    gap.get("suggested_product", ""),
                    json.dumps(gap),
                    "",
                    f"Opportunity score: {gap.get('opportunity_score', 0)}/10",
                ),
            )

    return {
        "success": True,
        "competitors": data.get("competitors", []),
        "price_alerts": data.get("price_alerts", []),
        "market_gaps": data.get("market_gaps", []),
        "trending_products": data.get("trending_products", []),
        "summary": data.get("summary", ""),
        "provider": ai_result.get("provider"),
        "scanned_at": datetime.utcnow().isoformat(),
        "message": "Competitor scan complete",
    }


def get_competitors(platform: str | None = None) -> list[dict]:
    """Get all tracked competitors."""
    with get_db() as conn:
        if platform:
            rows = conn.execute(
                "SELECT * FROM competitor_tracking WHERE platform = ? ORDER BY created_at DESC",
                (platform,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM competitor_tracking ORDER BY created_at DESC"
            ).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["top_products"] = _parse_json(d.get("top_products"), [])
        result.append(d)
    return result


def get_competitor_alerts(alert_type: str | None = None) -> list[dict]:
    """Get competitor alerts (price changes, market gaps, etc.)."""
    with get_db() as conn:
        if alert_type:
            rows = conn.execute(
                "SELECT * FROM competitor_alerts WHERE alert_type = ? AND status = 'active' ORDER BY created_at DESC",
                (alert_type,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM competitor_alerts WHERE status = 'active' ORDER BY created_at DESC"
            ).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["details"] = _parse_json(d.get("details"), {})
        result.append(d)
    return result


def dismiss_alert(alert_id: int) -> bool:
    """Dismiss a competitor alert."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM competitor_alerts WHERE id = ?", (alert_id,)
        ).fetchone()
        if not existing:
            return False
        conn.execute(
            "UPDATE competitor_alerts SET status = 'dismissed' WHERE id = ?",
            (alert_id,),
        )
    return True


def _parse_json(value, default=None):
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return default
