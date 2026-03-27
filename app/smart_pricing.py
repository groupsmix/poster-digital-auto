"""Smart Pricing module for AI Product Factory.

Provides AI-powered price suggestions based on competitor analysis,
platform-specific pricing, historical sales data, launch pricing rules,
and bundle pricing calculations.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


async def get_price_suggestions(product_id: int) -> dict:
    """Get AI-powered price suggestions for a product.

    Considers:
    - Competitor analysis from research data
    - Platform-specific pricing norms
    - Historical sales data from the system
    - Product type and brief
    """
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_dict = dict(product)
        research_data = product_dict.get("research_data", "{}")
        if isinstance(research_data, str):
            try:
                research_data = json.loads(research_data)
            except (json.JSONDecodeError, TypeError):
                research_data = {}

        # Get platform targets
        platforms_raw = product_dict.get("target_platforms", "[]")
        if isinstance(platforms_raw, str):
            try:
                platforms = json.loads(platforms_raw)
            except (json.JSONDecodeError, TypeError):
                platforms = []
        else:
            platforms = platforms_raw

        # Get historical sales data
        avg_sale = conn.execute(
            """SELECT AVG(revenue) as avg_rev, COUNT(*) as cnt
               FROM analytics WHERE event_type = 'sale' AND revenue > 0"""
        ).fetchone()
        avg_revenue = round(avg_sale["avg_rev"], 2) if avg_sale and avg_sale["avg_rev"] else 0
        total_sales = avg_sale["cnt"] if avg_sale else 0

        # Get platform-specific average prices
        platform_avg = conn.execute(
            """SELECT platform, AVG(revenue) as avg_rev
               FROM analytics WHERE event_type = 'sale' AND revenue > 0
               GROUP BY platform"""
        ).fetchall()
        platform_pricing = {row["platform"]: round(row["avg_rev"], 2) for row in platform_avg}

        # Get existing variant prices for context
        variants = conn.execute(
            "SELECT platform, price FROM product_variants WHERE product_id = ?",
            (product_id,),
        ).fetchall()
        existing_prices = {v["platform"]: v["price"] for v in variants if v["price"]}

    prompt = f"""You are a pricing strategy expert for digital products sold on platforms like Gumroad, Payhip, and Lemon Squeezy.

Analyze this product and suggest optimal pricing:

Product: {product_dict['name']}
Type: {product_dict.get('product_type', 'digital')}
Brief: {product_dict.get('brief', '')}
Target Platforms: {', '.join(platforms) if platforms else 'Gumroad, Payhip'}
Research Data: {json.dumps(research_data)[:500] if research_data else 'None'}

Historical Data:
- Average sale price across all products: ${avg_revenue}
- Total sales recorded: {total_sales}
- Platform-specific averages: {json.dumps(platform_pricing)}
- Current prices set: {json.dumps(existing_prices)}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "base_price": "$X.XX",
  "platform_prices": {{
    "Gumroad": {{"price": "$X.XX", "reasoning": "..."}},
    "Payhip": {{"price": "$X.XX", "reasoning": "..."}},
    "Lemon Squeezy": {{"price": "$X.XX", "reasoning": "..."}}
  }},
  "launch_pricing": {{
    "launch_price": "$X.XX",
    "launch_duration_hours": 48,
    "regular_price": "$X.XX",
    "reasoning": "..."
  }},
  "bundle_pricing": {{
    "bundle_3_price": "$XX.XX",
    "individual_total": "$XX.XX",
    "savings_percent": "XX%",
    "reasoning": "..."
  }},
  "pricing_tiers": [
    {{"tier": "Budget", "price": "$X.XX", "includes": "..."}},
    {{"tier": "Standard", "price": "$X.XX", "includes": "..."}},
    {{"tier": "Premium", "price": "$X.XX", "includes": "..."}}
  ],
  "competitor_analysis": "Brief analysis of competitor pricing in this niche",
  "confidence": 85
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {
            "success": False,
            "message": f"AI pricing failed: {ai_result['message']}",
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
        return {"success": False, "message": "Failed to parse AI pricing response"}

    return {
        "success": True,
        "product_id": product_id,
        "product_name": product_dict["name"],
        "suggestions": data,
        "provider": ai_result.get("provider"),
        "generated_at": datetime.utcnow().isoformat(),
        "message": "Price suggestions generated",
    }


def calculate_launch_pricing(
    regular_price: float,
    discount_percent: float = 40,
    duration_hours: int = 48,
) -> dict:
    """Calculate launch pricing details."""
    launch_price = round(regular_price * (1 - discount_percent / 100), 2)
    savings = round(regular_price - launch_price, 2)
    return {
        "regular_price": f"${regular_price:.2f}",
        "launch_price": f"${launch_price:.2f}",
        "discount_percent": f"{discount_percent}%",
        "savings": f"${savings:.2f}",
        "duration_hours": duration_hours,
        "description": f"${launch_price:.2f} for {duration_hours} hours, then ${regular_price:.2f}",
    }


def calculate_bundle_pricing(
    individual_prices: list[float],
    bundle_discount_percent: float = 25,
) -> dict:
    """Calculate bundle pricing for multiple products."""
    individual_total = sum(individual_prices)
    bundle_price = round(individual_total * (1 - bundle_discount_percent / 100), 2)
    savings = round(individual_total - bundle_price, 2)
    return {
        "individual_total": f"${individual_total:.2f}",
        "bundle_price": f"${bundle_price:.2f}",
        "savings": f"${savings:.2f}",
        "savings_percent": f"{bundle_discount_percent}%",
        "item_count": len(individual_prices),
        "description": f"Buy {len(individual_prices)} for ${bundle_price:.2f} instead of ${individual_total:.2f}",
    }
