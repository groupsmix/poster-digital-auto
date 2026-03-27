"""Upsell & Cross-sell Engine for AI Product Factory.

Feature 21: Auto-matches related products from your catalog.
Generates "You might also like" suggestions, thank-you page recommendations,
and follow-up email product suggestions.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


async def get_recommendations(product_id: int, limit: int = 5) -> dict:
    """Get AI-powered product recommendations for upsell/cross-sell.

    Analyzes the product catalog to find related products that complement
    the given product.
    """
    with get_db() as conn:
        # Get the target product
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_dict = dict(product)

        # Get all other products for matching
        all_products = conn.execute(
            "SELECT id, name, product_type, brief, status FROM products WHERE id != ? ORDER BY created_at DESC LIMIT 50",
            (product_id,),
        ).fetchall()

        # Get sales data for popularity weighting
        sales = conn.execute(
            """SELECT product_id, COUNT(*) as sale_count, SUM(revenue) as total_revenue
               FROM analytics WHERE event_type = 'sale'
               GROUP BY product_id"""
        ).fetchall()

        # Get variant info for pricing context
        variants = conn.execute(
            "SELECT product_id, platform, price FROM product_variants WHERE product_id = ?",
            (product_id,),
        ).fetchall()

    if not all_products:
        return {
            "success": True,
            "product_id": product_id,
            "recommendations": [],
            "message": "No other products available for recommendations",
        }

    sales_map = {s["product_id"]: {"sales": s["sale_count"], "revenue": s["total_revenue"]} for s in sales}
    catalog = []
    for p in all_products:
        pd = dict(p)
        pd["sales_data"] = sales_map.get(pd["id"], {"sales": 0, "revenue": 0})
        catalog.append(pd)

    current_price = ""
    if variants:
        current_price = variants[0]["price"] or ""

    catalog_text = "\n".join(
        f"- ID:{p['id']} | {p['name']} ({p['product_type']}) | Sales: {p['sales_data']['sales']} | {p.get('brief', '')[:80]}"
        for p in catalog[:30]
    )

    prompt = f"""You are a product recommendation engine for a digital product store.

Current product the customer is viewing/buying:
- Name: {product_dict['name']}
- Type: {product_dict.get('product_type', 'digital')}
- Brief: {product_dict.get('brief', '')}
- Price: {current_price}

Available products in catalog:
{catalog_text}

Select the top {limit} most relevant products for cross-selling/upselling.
Consider: complementary products, same audience, logical bundles, price tiers.

Return ONLY valid JSON (no markdown, no code fences):
{{
  "recommendations": [
    {{
      "product_id": 123,
      "product_name": "Product name",
      "relationship": "complementary/upgrade/bundle/same_audience",
      "reason": "Why this product complements the current one",
      "pitch": "Short 1-line sales pitch for the recommendation",
      "confidence": 85
    }}
  ],
  "thank_you_message": "A short thank-you message to show after purchase with product suggestions",
  "email_day3_suggestion": "Product suggestion text for Day 3 follow-up email",
  "email_day7_suggestion": "Product suggestion text for Day 7 follow-up email"
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {
            "success": False,
            "message": f"Recommendation engine failed: {ai_result['message']}",
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
        return {"success": False, "message": "Failed to parse recommendation response"}

    # Validate product IDs exist
    valid_ids = {p["id"] for p in all_products}
    recommendations = [
        r for r in data.get("recommendations", [])
        if r.get("product_id") in valid_ids
    ][:limit]

    return {
        "success": True,
        "product_id": product_id,
        "product_name": product_dict["name"],
        "recommendations": recommendations,
        "thank_you_message": data.get("thank_you_message", ""),
        "email_day3_suggestion": data.get("email_day3_suggestion", ""),
        "email_day7_suggestion": data.get("email_day7_suggestion", ""),
        "provider": ai_result.get("provider"),
        "generated_at": datetime.utcnow().isoformat(),
        "message": f"Generated {len(recommendations)} recommendations",
    }


def get_frequently_bought_together(product_id: int) -> list[dict]:
    """Find products frequently bought by the same customers.

    Uses analytics data to find purchase correlations.
    """
    with get_db() as conn:
        # This uses a simplified correlation: products bought on the same day
        related = conn.execute(
            """SELECT a2.product_id, p.name, COUNT(*) as co_purchase_count
               FROM analytics a1
               JOIN analytics a2 ON date(a1.recorded_at) = date(a2.recorded_at)
                   AND a1.product_id != a2.product_id
               JOIN products p ON a2.product_id = p.id
               WHERE a1.product_id = ? AND a1.event_type = 'sale' AND a2.event_type = 'sale'
               GROUP BY a2.product_id
               ORDER BY co_purchase_count DESC
               LIMIT 5""",
            (product_id,),
        ).fetchall()

    return [dict(r) for r in related]
