"""Cross-Platform Arbitrage module for AI Product Factory.

Feature 13: Detects pricing/performance differences across platforms.
Suggests optimizations like price adjustments and promotion strategies.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "research"


async def analyze_arbitrage() -> dict:
    """Analyze cross-platform pricing and performance differences.

    Compares products across Gumroad, Payhip, Lemon Squeezy to find
    optimization opportunities.
    """
    with get_db() as conn:
        # Get per-platform variant pricing
        variants = conn.execute(
            """SELECT pv.product_id, p.name as product_name, pv.platform,
                      pv.price, pv.title
               FROM product_variants pv
               JOIN products p ON pv.product_id = p.id
               ORDER BY p.id, pv.platform"""
        ).fetchall()

        # Get per-platform sales data
        sales = conn.execute(
            """SELECT product_id, platform,
                      SUM(revenue) as total_revenue,
                      COUNT(*) as sale_count
               FROM analytics
               WHERE event_type = 'sale'
               GROUP BY product_id, platform"""
        ).fetchall()

        # Get per-platform views
        views = conn.execute(
            """SELECT product_id, platform, COUNT(*) as view_count
               FROM analytics
               WHERE event_type = 'view'
               GROUP BY product_id, platform"""
        ).fetchall()

    variant_data = [dict(v) for v in variants]
    sales_data = [dict(s) for s in sales]
    views_data = [dict(v) for v in views]

    # Build per-product cross-platform comparison
    products_map: dict[int, dict] = {}
    for v in variant_data:
        pid = v["product_id"]
        if pid not in products_map:
            products_map[pid] = {"name": v["product_name"], "platforms": {}}
        products_map[pid]["platforms"][v["platform"]] = {
            "price": v["price"],
            "title": v["title"],
            "revenue": 0,
            "sales": 0,
            "views": 0,
        }

    for s in sales_data:
        pid = s["product_id"]
        if pid in products_map and s["platform"] in products_map[pid]["platforms"]:
            products_map[pid]["platforms"][s["platform"]]["revenue"] = s["total_revenue"]
            products_map[pid]["platforms"][s["platform"]]["sales"] = s["sale_count"]

    for v in views_data:
        pid = v["product_id"]
        if pid in products_map and v["platform"] in products_map[pid]["platforms"]:
            products_map[pid]["platforms"][v["platform"]]["views"] = v["view_count"]

    # Generate opportunities
    opportunities = []
    for pid, pdata in products_map.items():
        platforms = pdata["platforms"]
        if len(platforms) < 2:
            continue

        # Find price differences
        prices = {}
        for plat, info in platforms.items():
            try:
                price_val = float(str(info["price"]).replace("$", "").strip()) if info["price"] else 0
            except (ValueError, AttributeError):
                price_val = 0
            prices[plat] = price_val

        if prices:
            min_price = min(p for p in prices.values() if p > 0) if any(p > 0 for p in prices.values()) else 0
            max_price = max(prices.values())

            if max_price > 0 and min_price > 0 and max_price > min_price * 1.3:
                min_plat = [k for k, v in prices.items() if v == min_price][0]
                max_plat = [k for k, v in prices.items() if v == max_price][0]
                opportunities.append({
                    "product_id": pid,
                    "product_name": pdata["name"],
                    "type": "price_difference",
                    "description": f"'{pdata['name']}' sells for ${min_price:.0f} on {min_plat} but ${max_price:.0f} on {max_plat}",
                    "suggestion": f"Consider raising {min_plat} price to match {max_plat}",
                    "potential_gain": f"${max_price - min_price:.2f} per sale on {min_plat}",
                    "platforms": {min_plat: f"${min_price:.2f}", max_plat: f"${max_price:.2f}"},
                })

        # Find conversion rate differences
        for plat, info in platforms.items():
            if info["views"] > 5 and info["sales"] > 0:
                conv_rate = info["sales"] / info["views"] * 100
                if conv_rate > 5:
                    opportunities.append({
                        "product_id": pid,
                        "product_name": pdata["name"],
                        "type": "high_conversion",
                        "description": f"'{pdata['name']}' has {conv_rate:.1f}% conversion on {plat}",
                        "suggestion": f"Promote {plat} version more aggressively",
                        "potential_gain": "Increased sales volume",
                        "platforms": {plat: f"{conv_rate:.1f}% conversion"},
                    })

    # If we have data, also ask AI for insights
    ai_insights = ""
    if products_map:
        summary = json.dumps(
            {str(k): v for k, v in list(products_map.items())[:10]},
            default=str,
        )[:1500]

        prompt = f"""You are a cross-platform digital product pricing analyst.

Analyze this cross-platform product data and provide optimization insights:

{summary}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "insights": [
    {{
      "finding": "What you found",
      "recommendation": "What to do about it",
      "impact": "high/medium/low",
      "platform_focus": "Which platform to optimize"
    }}
  ],
  "summary": "2-3 sentence overall cross-platform strategy recommendation"
}}"""

        ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
        if ai_result["success"]:
            raw = ai_result["result"].strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()
            try:
                ai_data = json.loads(raw)
                ai_insights = ai_data.get("summary", "")
                for insight in ai_data.get("insights", []):
                    opportunities.append({
                        "product_id": None,
                        "product_name": "",
                        "type": "ai_insight",
                        "description": insight.get("finding", ""),
                        "suggestion": insight.get("recommendation", ""),
                        "potential_gain": insight.get("impact", "medium"),
                        "platforms": {insight.get("platform_focus", "all"): "focus"},
                    })
            except json.JSONDecodeError:
                pass

    return {
        "success": True,
        "opportunities": opportunities,
        "product_count": len(products_map),
        "ai_summary": ai_insights,
        "analyzed_at": datetime.utcnow().isoformat(),
        "message": f"Found {len(opportunities)} arbitrage opportunities across {len(products_map)} products",
    }
