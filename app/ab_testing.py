"""A/B Testing module for AI Product Factory.

Provides A/B/C variant generation, sales tracking per variant,
automatic winner detection, and pattern learning.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


async def create_ab_test(variant_id: int) -> dict:
    """Create an A/B/C test for a variant by generating alternative titles/descriptions.

    Uses AI to generate 3 different versions (A, B, C) of the variant's title and description.
    The original variant becomes version A, and two new variants are created for B and C.
    """
    with get_db() as conn:
        variant = conn.execute(
            "SELECT * FROM product_variants WHERE id = ?", (variant_id,)
        ).fetchone()
        if not variant:
            return {"success": False, "message": "Variant not found"}

        variant_dict = dict(variant)
        product_id = variant_dict["product_id"]
        platform = variant_dict["platform"]
        original_title = variant_dict["title"] or ""
        original_description = variant_dict["description"] or ""

        product = conn.execute(
            "SELECT name, brief FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_dict = dict(product)

    prompt = f"""You are an A/B testing expert for digital product listings.

Given this product listing, generate 2 alternative versions (B and C) of the title and description.
Each version should test a different approach:
- Version B: Try a different angle (e.g., benefit-focused, curiosity-driven, number-based)
- Version C: Try another approach (e.g., emotional appeal, urgency, social proof)

Product: {product_dict['name']}
Brief: {product_dict.get('brief', '')}
Platform: {platform}
Original Title (Version A): {original_title}
Original Description (Version A): {original_description}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "variant_b": {{
    "title": "...",
    "description": "...",
    "strategy": "brief description of the approach used"
  }},
  "variant_c": {{
    "title": "...",
    "description": "...",
    "strategy": "brief description of the approach used"
  }},
  "insights": "What patterns tend to work best for {platform}"
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {
            "success": False,
            "message": f"AI generation failed: {ai_result['message']}",
        }

    raw_text = ai_result["result"]
    # Strip markdown fences if present
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
        return {"success": False, "message": "Failed to parse AI response as JSON"}

    variant_b_data = data.get("variant_b", {})
    variant_c_data = data.get("variant_c", {})
    insights = data.get("insights", "")

    with get_db() as conn:
        # Mark original variant as A
        conn.execute(
            "UPDATE product_variants SET ab_variant = 'A' WHERE id = ?",
            (variant_id,),
        )

        # Create variant B
        cursor_b = conn.execute(
            """INSERT INTO product_variants
               (product_id, platform, language, title, description, tags, price,
                image_urls, ceo_score, ceo_feedback, ceo_status, ab_variant)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product_id,
                platform,
                variant_dict.get("language", "en"),
                variant_b_data.get("title", ""),
                variant_b_data.get("description", ""),
                variant_dict.get("tags", "[]"),
                variant_dict.get("price", ""),
                variant_dict.get("image_urls", "[]"),
                0,
                "",
                "pending",
                "B",
            ),
        )
        variant_b_id = cursor_b.lastrowid

        # Create variant C
        cursor_c = conn.execute(
            """INSERT INTO product_variants
               (product_id, platform, language, title, description, tags, price,
                image_urls, ceo_score, ceo_feedback, ceo_status, ab_variant)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                product_id,
                platform,
                variant_dict.get("language", "en"),
                variant_c_data.get("title", ""),
                variant_c_data.get("description", ""),
                variant_dict.get("tags", "[]"),
                variant_dict.get("price", ""),
                variant_dict.get("image_urls", "[]"),
                0,
                "",
                "pending",
                "C",
            ),
        )
        variant_c_id = cursor_c.lastrowid

        # Create the AB test record
        test_name = f"A/B Test: {original_title[:50]}"
        cursor_test = conn.execute(
            """INSERT INTO ab_tests
               (product_id, test_name, variant_a_id, variant_b_id, variant_c_id, status)
               VALUES (?, ?, ?, ?, ?, 'running')""",
            (product_id, test_name, variant_id, variant_b_id, variant_c_id),
        )
        test_id = cursor_test.lastrowid

    return {
        "success": True,
        "test_id": test_id,
        "variant_a_id": variant_id,
        "variant_b_id": variant_b_id,
        "variant_c_id": variant_c_id,
        "strategies": {
            "A": "Original version",
            "B": variant_b_data.get("strategy", ""),
            "C": variant_c_data.get("strategy", ""),
        },
        "insights": insights,
        "provider": ai_result.get("provider"),
        "message": f"A/B/C test created with 3 variants",
    }


def get_ab_tests(status: str | None = None) -> list[dict]:
    """Get all A/B tests with their variant data and sales metrics."""
    with get_db() as conn:
        query = "SELECT * FROM ab_tests"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY started_at DESC"
        tests = conn.execute(query, params).fetchall()

        result = []
        for test in tests:
            test_dict = dict(test)
            test_id = test_dict["id"]

            # Get variant data with sales
            variants_data = []
            for key in ("variant_a_id", "variant_b_id", "variant_c_id"):
                vid = test_dict.get(key)
                if not vid:
                    continue
                v = conn.execute(
                    "SELECT * FROM product_variants WHERE id = ?", (vid,)
                ).fetchone()
                if not v:
                    continue
                v_dict = dict(v)

                # Get sales data for this variant
                sales = conn.execute(
                    """SELECT COUNT(*) as count, COALESCE(SUM(revenue), 0) as total
                       FROM analytics
                       WHERE variant_id = ? AND event_type = 'sale'""",
                    (vid,),
                ).fetchone()
                views = conn.execute(
                    """SELECT COUNT(*) as count
                       FROM analytics
                       WHERE variant_id = ? AND event_type = 'view'""",
                    (vid,),
                ).fetchone()

                v_dict["sales_count"] = sales["count"] if sales else 0
                v_dict["sales_revenue"] = sales["total"] if sales else 0
                v_dict["views_count"] = views["count"] if views else 0
                v_dict["conversion_rate"] = (
                    round(v_dict["sales_count"] / v_dict["views_count"] * 100, 1)
                    if v_dict["views_count"] > 0
                    else 0
                )
                v_dict["tags"] = _parse_json(v_dict.get("tags", "[]"), [])
                v_dict["image_urls"] = _parse_json(v_dict.get("image_urls", "[]"), [])
                variants_data.append(v_dict)

            test_dict["variants"] = variants_data

            # Get product name
            product = conn.execute(
                "SELECT name FROM products WHERE id = ?",
                (test_dict["product_id"],),
            ).fetchone()
            test_dict["product_name"] = product["name"] if product else "Unknown"

            result.append(test_dict)

    return result


def record_ab_sale(
    test_id: int, variant_id: int, revenue: float
) -> dict:
    """Record a sale for a specific variant in an A/B test."""
    with get_db() as conn:
        test = conn.execute(
            "SELECT * FROM ab_tests WHERE id = ?", (test_id,)
        ).fetchone()
        if not test:
            return {"success": False, "message": "A/B test not found"}

        test_dict = dict(test)
        valid_ids = [
            test_dict.get("variant_a_id"),
            test_dict.get("variant_b_id"),
            test_dict.get("variant_c_id"),
        ]
        if variant_id not in valid_ids:
            return {"success": False, "message": "Variant not part of this test"}

        # Get product_id and platform from the variant
        variant = conn.execute(
            "SELECT product_id, platform FROM product_variants WHERE id = ?",
            (variant_id,),
        ).fetchone()
        if not variant:
            return {"success": False, "message": "Variant not found"}

        conn.execute(
            """INSERT INTO analytics
               (product_id, variant_id, platform, event_type, revenue, data, recorded_at)
               VALUES (?, ?, ?, 'sale', ?, ?, ?)""",
            (
                variant["product_id"],
                variant_id,
                variant["platform"],
                revenue,
                json.dumps({"source": "ab_test", "test_id": test_id}),
                datetime.utcnow().isoformat(),
            ),
        )

    # Check for winner after recording
    winner_result = detect_winner(test_id)

    return {
        "success": True,
        "message": "Sale recorded",
        "winner_detected": winner_result.get("winner_detected", False),
        "winner": winner_result.get("winner"),
    }


def detect_winner(test_id: int) -> dict:
    """Auto-detect a winner if enough data has been collected.

    Requires at least 10 total sales across all variants.
    Winner needs at least 30% more conversions or revenue than the second best.
    """
    with get_db() as conn:
        test = conn.execute(
            "SELECT * FROM ab_tests WHERE id = ?", (test_id,)
        ).fetchone()
        if not test:
            return {"winner_detected": False}

        test_dict = dict(test)
        if test_dict["status"] != "running":
            return {
                "winner_detected": test_dict["winner_id"] is not None,
                "winner": test_dict["winner_id"],
            }

        variant_ids = [
            test_dict.get("variant_a_id"),
            test_dict.get("variant_b_id"),
            test_dict.get("variant_c_id"),
        ]
        variant_ids = [v for v in variant_ids if v is not None]

        variant_metrics = []
        total_sales = 0
        for vid in variant_ids:
            sales = conn.execute(
                """SELECT COUNT(*) as count, COALESCE(SUM(revenue), 0) as total
                   FROM analytics
                   WHERE variant_id = ? AND event_type = 'sale'""",
                (vid,),
            ).fetchone()
            count = sales["count"] if sales else 0
            revenue = sales["total"] if sales else 0
            total_sales += count
            variant_metrics.append(
                {"variant_id": vid, "sales": count, "revenue": revenue}
            )

        # Need at least 10 sales to declare a winner
        if total_sales < 10:
            return {"winner_detected": False, "total_sales": total_sales, "needed": 10}

        # Sort by revenue descending
        variant_metrics.sort(key=lambda x: x["revenue"], reverse=True)
        best = variant_metrics[0]
        second = variant_metrics[1] if len(variant_metrics) > 1 else None

        # Winner needs 30% more revenue than second
        if second and second["revenue"] > 0:
            advantage = (best["revenue"] - second["revenue"]) / second["revenue"]
            if advantage < 0.3:
                return {"winner_detected": False, "advantage": round(advantage * 100, 1)}

        # Declare winner
        winner_id = best["variant_id"]
        conn.execute(
            """UPDATE ab_tests
               SET winner_id = ?, status = 'completed', ended_at = ?
               WHERE id = ?""",
            (winner_id, datetime.utcnow().isoformat(), test_id),
        )

    return {
        "winner_detected": True,
        "winner": winner_id,
        "metrics": variant_metrics,
    }


def get_ab_patterns() -> list[dict]:
    """Analyze completed A/B tests to learn patterns about what works."""
    patterns = []
    with get_db() as conn:
        completed = conn.execute(
            """SELECT t.*, p.name as product_name
               FROM ab_tests t
               JOIN products p ON t.product_id = p.id
               WHERE t.status = 'completed' AND t.winner_id IS NOT NULL"""
        ).fetchall()

        if not completed:
            return [
                {
                    "pattern": "Not enough data yet",
                    "detail": "Complete more A/B tests to discover patterns",
                    "confidence": 0,
                }
            ]

        # Analyze winning variant characteristics
        wins_with_numbers = 0
        wins_with_emoji = 0
        wins_with_short_title = 0
        total_completed = len(completed)

        for test in completed:
            test_dict = dict(test)
            winner_id = test_dict["winner_id"]
            winner = conn.execute(
                "SELECT * FROM product_variants WHERE id = ?", (winner_id,)
            ).fetchone()
            if not winner:
                continue
            winner_dict = dict(winner)
            title = winner_dict.get("title", "")

            if any(c.isdigit() for c in title):
                wins_with_numbers += 1
            if any(ord(c) > 127 for c in title):
                wins_with_emoji += 1
            if len(title) < 50:
                wins_with_short_title += 1

        if total_completed > 0:
            pct_numbers = round(wins_with_numbers / total_completed * 100)
            if pct_numbers > 50:
                patterns.append(
                    {
                        "pattern": f"Titles with numbers convert {pct_numbers}% of the time",
                        "detail": "Consider using numbers in your product titles",
                        "confidence": min(pct_numbers, 95),
                    }
                )

            pct_short = round(wins_with_short_title / total_completed * 100)
            if pct_short > 50:
                patterns.append(
                    {
                        "pattern": f"Shorter titles (< 50 chars) win {pct_short}% of tests",
                        "detail": "Keep titles concise and punchy",
                        "confidence": min(pct_short, 95),
                    }
                )

        # Platform-specific patterns
        platform_wins = conn.execute(
            """SELECT v.platform, COUNT(*) as wins
               FROM ab_tests t
               JOIN product_variants v ON t.winner_id = v.id
               WHERE t.status = 'completed'
               GROUP BY v.platform
               ORDER BY wins DESC"""
        ).fetchall()

        for pw in platform_wins:
            pw_dict = dict(pw)
            patterns.append(
                {
                    "pattern": f"{pw_dict['platform']}: {pw_dict['wins']} winning variants",
                    "detail": f"Most tested platform with successful optimizations",
                    "confidence": min(pw_dict["wins"] * 15, 90),
                }
            )

    if not patterns:
        patterns.append(
            {
                "pattern": "Keep testing!",
                "detail": "More A/B tests will reveal clearer patterns",
                "confidence": 0,
            }
        )

    return patterns


def _parse_json(value: str, default=None):
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
