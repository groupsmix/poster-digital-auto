"""AI-powered Customer Persona generation for AI Product Factory.

Feature 9 Enhancement: Auto-generate customer personas from sales data analysis.
Uses AI to analyze product performance, platform demographics, and sales patterns
to create detailed buyer personas.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "research"


async def generate_personas_from_data(count: int = 3) -> dict:
    """Generate customer personas by analyzing existing sales and product data.

    Analyzes products, sales analytics, platform performance, and existing
    personas to generate data-driven buyer personas.
    """
    with get_db() as conn:
        # Gather product data
        products = conn.execute(
            "SELECT name, product_type, brief FROM products ORDER BY created_at DESC LIMIT 20"
        ).fetchall()

        # Gather sales analytics
        sales_by_platform = conn.execute(
            """SELECT platform, COUNT(*) as sale_count, SUM(revenue) as total_revenue,
                      AVG(revenue) as avg_revenue
               FROM analytics WHERE event_type = 'sale'
               GROUP BY platform"""
        ).fetchall()

        # Gather views analytics
        views_by_platform = conn.execute(
            """SELECT platform, COUNT(*) as view_count
               FROM analytics WHERE event_type = 'view'
               GROUP BY platform"""
        ).fetchall()

        # Get existing personas to avoid duplicates
        existing_personas = conn.execute(
            "SELECT name, demographics FROM customer_personas"
        ).fetchall()

        # Get product types distribution
        type_dist = conn.execute(
            "SELECT product_type, COUNT(*) as cnt FROM products GROUP BY product_type"
        ).fetchall()

        # Get trend data
        trends = conn.execute(
            "SELECT topic, trend_score FROM trend_predictions ORDER BY trend_score DESC LIMIT 5"
        ).fetchall()

    product_summary = "\n".join(
        f"- {p['name']} ({p['product_type']}): {(p.get('brief') or '')[:80]}"
        for p in products
    ) if products else "No products yet"

    sales_summary = "\n".join(
        f"- {s['platform']}: {s['sale_count']} sales, ${s['total_revenue']:.2f} revenue, ${s['avg_revenue']:.2f} avg"
        for s in sales_by_platform
    ) if sales_by_platform else "No sales data yet"

    existing_names = [p["name"] for p in existing_personas]
    existing_text = ", ".join(existing_names) if existing_names else "None"

    trend_text = ", ".join(t["topic"] for t in trends) if trends else "No trend data"

    prompt = f"""You are a marketing analyst specializing in digital product buyer personas.

Analyze the following business data and create {count} detailed, data-driven customer personas.

PRODUCT CATALOG:
{product_summary}

SALES DATA BY PLATFORM:
{sales_summary}

PRODUCT TYPES: {', '.join(f"{t['product_type']}({t['cnt']})" for t in type_dist) if type_dist else 'Mixed digital products'}

TRENDING TOPICS: {trend_text}

EXISTING PERSONAS (avoid duplicating): {existing_text}

Create {count} NEW unique personas. Return ONLY valid JSON (no markdown, no code fences):
{{
  "personas": [
    {{
      "name": "Persona Name (e.g., 'Busy Corporate Manager')",
      "demographics": "Age range, occupation, income level, location type",
      "interests": "Key interests and hobbies related to your products",
      "pain_points": "3-4 specific pain points your products solve",
      "buying_behavior": "How they discover, evaluate, and purchase digital products",
      "preferred_platforms": ["Platform 1", "Platform 2"],
      "price_sensitivity": "low/medium/high",
      "content_preferences": "What type of content/marketing resonates with them",
      "lifetime_value": "Estimated lifetime value range",
      "acquisition_channels": ["Channel 1", "Channel 2"],
      "confidence_score": 75
    }}
  ],
  "insights": "2-3 sentences about overall audience patterns from the data"
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {"success": False, "message": f"Persona generation failed: {ai_result['message']}"}

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
        return {"success": False, "message": "Failed to parse persona generation response"}

    # Save generated personas to DB
    saved_personas = []
    with get_db() as conn:
        for p in data.get("personas", []):
            cursor = conn.execute(
                """INSERT INTO customer_personas
                   (name, demographics, interests, pain_points, buying_behavior, source)
                   VALUES (?, ?, ?, ?, ?, 'ai_generated')""",
                (
                    p.get("name", ""),
                    p.get("demographics", ""),
                    p.get("interests", ""),
                    p.get("pain_points", ""),
                    p.get("buying_behavior", ""),
                ),
            )
            row = conn.execute(
                "SELECT * FROM customer_personas WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            persona = dict(row)
            # Add AI-generated fields that don't have DB columns
            persona["preferred_platforms"] = p.get("preferred_platforms", [])
            persona["price_sensitivity"] = p.get("price_sensitivity", "medium")
            persona["content_preferences"] = p.get("content_preferences", "")
            persona["lifetime_value"] = p.get("lifetime_value", "")
            persona["acquisition_channels"] = p.get("acquisition_channels", [])
            persona["confidence_score"] = p.get("confidence_score", 50)
            saved_personas.append(persona)

    return {
        "success": True,
        "personas": saved_personas,
        "insights": data.get("insights", ""),
        "count": len(saved_personas),
        "provider": ai_result.get("provider"),
        "generated_at": datetime.utcnow().isoformat(),
        "message": f"Generated {len(saved_personas)} AI-powered personas",
    }
