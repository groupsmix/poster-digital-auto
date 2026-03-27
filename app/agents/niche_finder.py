"""Niche Finder AI Agent (Agent 0).

Scans for digital product opportunities with proven demand.
Uses AI reasoning to analyze market gaps, trending topics, and consumer needs.
Returns ranked list of product ideas with demand scores, competition levels,
monthly searches, evidence, suggested prices, and best platforms.
"""

import json
import logging
import re
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)


def _build_niche_scan_prompt() -> str:
    """Build the prompt for niche scanning."""
    today = datetime.utcnow().strftime("%B %d, %Y")
    return f"""You are an expert digital product market analyst. Today is {today}.

Your task: Identify 5-8 digital product ideas that are currently in HIGH DEMAND but have LOW-to-MEDIUM competition.

Focus on these product categories:
- Digital planners & organizers (PDF, Notion templates, Google Sheets)
- Budget trackers & financial templates
- Social media templates (Instagram, TikTok, Pinterest)
- Educational worksheets & study guides
- Habit trackers & wellness journals
- Business templates (invoices, proposals, contracts)
- Creative assets (fonts, icons, mockups, presets)
- Printable wall art & home decor
- Recipe books & meal planners
- Fitness & workout planners

For each idea, analyze:
1. Current search demand and social media buzz
2. Competition level on Gumroad, Payhip, Etsy
3. Pricing sweet spots
4. Evidence of demand (common questions, Reddit threads, social posts)

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "ideas": [
        {{
            "product": "<specific product name>",
            "demand_score": <integer 1-10, how much demand exists>,
            "competition": "<low|medium|high>",
            "monthly_searches": <estimated monthly searches, integer>,
            "evidence": "<brief evidence of demand: mentions, posts, questions>",
            "suggested_price": "<price range like '$7-12'>",
            "best_platforms": ["<platform1>", "<platform2>"]
        }}
    ],
    "scan_summary": "<1-2 sentence summary of market conditions>"
}}

Be specific with product names (not generic). Include realistic search estimates.
Rank ideas by demand_score descending (highest first)."""


def _parse_json_response(text: str) -> dict:
    """Parse JSON from AI response with fallback strategies."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse JSON from niche finder response, using fallback")
    return {
        "ideas": [],
        "scan_summary": "Scan completed but could not parse results.",
    }


def _validate_idea(idea: dict) -> dict:
    """Ensure all required fields exist in an idea dict."""
    return {
        "product": idea.get("product", "Untitled Product Idea"),
        "demand_score": min(max(int(idea.get("demand_score", 5)), 1), 10),
        "competition": idea.get("competition", "medium"),
        "monthly_searches": int(idea.get("monthly_searches", 0)),
        "evidence": idea.get("evidence", ""),
        "suggested_price": idea.get("suggested_price", "$9-15"),
        "best_platforms": idea.get("best_platforms", ["Gumroad", "Payhip"]),
    }


async def run_niche_scan() -> dict:
    """Run the Niche Finder AI agent.

    Returns:
        dict with keys: success, ideas (list), scan_summary, provider, message
    """
    prompt = _build_niche_scan_prompt()

    result = await call_text_with_failover("niche_finding", prompt)

    if not result["success"]:
        return {
            "success": False,
            "ideas": [],
            "scan_summary": "",
            "provider": None,
            "message": result["message"],
        }

    raw_text = result["result"]
    parsed = _parse_json_response(raw_text)

    ideas = [_validate_idea(idea) for idea in parsed.get("ideas", [])]
    # Sort by demand_score descending
    ideas.sort(key=lambda x: x["demand_score"], reverse=True)

    # Store ideas in database
    stored_ids = []
    with get_db() as conn:
        for idea in ideas:
            # Check for duplicate product names (skip if exists and is still new)
            existing = conn.execute(
                "SELECT id FROM niche_ideas WHERE product_name = ? AND status = 'new'",
                (idea["product"],),
            ).fetchone()
            if existing:
                stored_ids.append(existing["id"])
                continue

            cursor = conn.execute(
                """INSERT INTO niche_ideas
                   (product_name, demand_score, competition, monthly_searches,
                    evidence, suggested_price, best_platforms, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'new')""",
                (
                    idea["product"],
                    idea["demand_score"],
                    idea["competition"],
                    idea["monthly_searches"],
                    idea["evidence"],
                    idea["suggested_price"],
                    json.dumps(idea["best_platforms"]),
                ),
            )
            stored_ids.append(cursor.lastrowid)

    # Log the scan
    with get_db() as conn:
        conn.execute(
            """INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message)
               VALUES (NULL, 'niche_finder', ?, 'success', ?)""",
            (result["provider"], f"Found {len(ideas)} niche ideas"),
        )

    return {
        "success": True,
        "ideas": ideas,
        "stored_ids": stored_ids,
        "scan_summary": parsed.get("scan_summary", ""),
        "provider": result["provider"],
        "message": f"Niche scan complete: {len(ideas)} ideas found via {result['provider']}",
    }


def get_all_niches(status: str | None = None, sort_by: str = "demand_score") -> list[dict]:
    """Get all niche ideas from database.

    Args:
        status: Filter by status (new, approved, rejected, archived, created)
        sort_by: Sort field (demand_score, created_at, monthly_searches)
    """
    with get_db() as conn:
        query = "SELECT * FROM niche_ideas"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)

        sort_map = {
            "demand_score": "demand_score DESC",
            "created_at": "created_at DESC",
            "monthly_searches": "monthly_searches DESC",
            "competition": "competition ASC",
        }
        order = sort_map.get(sort_by, "demand_score DESC")
        query += f" ORDER BY {order}"

        rows = conn.execute(query, params).fetchall()

    results = []
    for row in rows:
        d = dict(row)
        # Parse JSON fields
        try:
            d["best_platforms"] = json.loads(d.get("best_platforms", "[]"))
        except (json.JSONDecodeError, TypeError):
            d["best_platforms"] = []
        results.append(d)
    return results


def update_niche_status(niche_id: int, status: str) -> dict | None:
    """Update the status of a niche idea.

    Args:
        niche_id: ID of the niche idea
        status: New status (approved, rejected, archived, created)
    """
    valid_statuses = {"new", "approved", "rejected", "archived", "created"}
    if status not in valid_statuses:
        return None

    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM niche_ideas WHERE id = ?", (niche_id,)
        ).fetchone()
        if not existing:
            return None

        conn.execute(
            "UPDATE niche_ideas SET status = ? WHERE id = ?",
            (status, niche_id),
        )
        row = conn.execute(
            "SELECT * FROM niche_ideas WHERE id = ?", (niche_id,)
        ).fetchone()

    d = dict(row)
    try:
        d["best_platforms"] = json.loads(d.get("best_platforms", "[]"))
    except (json.JSONDecodeError, TypeError):
        d["best_platforms"] = []
    return d


async def create_product_from_niche(niche_id: int) -> dict:
    """Create a product from a niche idea and trigger the pipeline.

    Args:
        niche_id: ID of the niche idea to create from.

    Returns:
        dict with product_id and status info.
    """
    with get_db() as conn:
        niche = conn.execute(
            "SELECT * FROM niche_ideas WHERE id = ?", (niche_id,)
        ).fetchone()
        if not niche:
            return {"success": False, "message": "Niche idea not found"}

        niche_dict = dict(niche)

        try:
            platforms = json.loads(niche_dict.get("best_platforms", "[]"))
        except (json.JSONDecodeError, TypeError):
            platforms = ["Gumroad", "Payhip"]

        # Create the product
        cursor = conn.execute(
            """INSERT INTO products
               (name, product_type, brief, target_platforms, target_languages, status, plan_mode, niche_data)
               VALUES (?, 'digital', ?, ?, '["en"]', 'pending', 'A', ?)""",
            (
                niche_dict["product_name"],
                f"AI-discovered niche idea. Evidence: {niche_dict.get('evidence', '')}. "
                f"Suggested price: {niche_dict.get('suggested_price', '')}",
                json.dumps(platforms),
                json.dumps({
                    "niche_id": niche_id,
                    "demand_score": niche_dict.get("demand_score"),
                    "competition": niche_dict.get("competition"),
                    "monthly_searches": niche_dict.get("monthly_searches"),
                }),
            ),
        )
        product_id = cursor.lastrowid

        # Update niche status
        conn.execute(
            "UPDATE niche_ideas SET status = 'created', created_product_id = ? WHERE id = ?",
            (product_id, niche_id),
        )

    return {
        "success": True,
        "product_id": product_id,
        "message": f"Product '{niche_dict['product_name']}' created from niche idea #{niche_id}",
    }
