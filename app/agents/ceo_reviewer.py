"""CEO AI Reviewer Agent.

Takes product name, variants, and research data.
Scores each variant 1-10 on: title, description, tags, price, overall.
Status: "approved" if overall >= 7, "rejected" if < 7.
Returns specific feedback for rejected items.
"""

import json
import logging
import re

from app.ai_failover import call_text_with_failover

logger = logging.getLogger(__name__)

APPROVAL_THRESHOLD = 7


def _build_review_prompt(
    product_name: str,
    variants: list[dict],
    research_data: dict,
) -> str:
    """Build the CEO review prompt."""
    variants_text = ""
    for i, v in enumerate(variants):
        tags = v.get("tags", [])
        if isinstance(tags, list):
            tags_str = ", ".join(tags)
        else:
            tags_str = str(tags)
        variants_text += f"""
--- Variant {i + 1} ({v.get('platform', 'Unknown')}) ---
Title: {v.get('title', '')}
Description: {v.get('description', '')}
Tags: {tags_str}
Price: ${v.get('price', '0')}
"""

    return f"""You are a CEO reviewing product listings before they go live.
Your job is to ensure quality, marketability, and brand consistency.

Product: {product_name}
Target Audience: {research_data.get("target_audience", "General")}
Unique Angle: {research_data.get("unique_angle", "")}
Recommended Price: ${research_data.get("price_range", {}).get("recommended", 19.99)}

Here are the product variants to review:
{variants_text}

Score EACH variant on a scale of 1-10 for each category.
A variant is "approved" if overall score >= {APPROVAL_THRESHOLD}, otherwise "rejected".

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "reviews": [
        {{
            "platform": "<platform name>",
            "scores": {{
                "title": <int 1-10>,
                "description": <int 1-10>,
                "tags": <int 1-10>,
                "price": <int 1-10>,
                "overall": <int 1-10>
            }},
            "status": "<approved or rejected>",
            "feedback": "<specific feedback, especially if rejected>"
        }}
    ]
}}

Be fair but demanding. Only approve truly market-ready listings."""


def _parse_json_response(text: str) -> dict:
    """Parse JSON from AI response with fallback strategies."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{[\s\S]*\}", text)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse CEO review JSON response")
    return {"reviews": []}


async def run_ceo_review(
    product_name: str,
    variants: list[dict],
    research_data: dict,
) -> dict:
    """Run the CEO AI Reviewer agent.

    Args:
        product_name: Name of the product.
        variants: List of product variant dicts from the Creator agent.
        research_data: Research data from the Researcher agent.

    Returns:
        dict with keys:
            success (bool), reviews (list), all_approved (bool),
            provider (str), message (str)
    """
    if not variants:
        return {
            "success": False,
            "reviews": [],
            "all_approved": False,
            "provider": None,
            "message": "No variants to review",
        }

    prompt = _build_review_prompt(product_name, variants, research_data)
    result = await call_text_with_failover("ceo_review", prompt)

    if not result["success"]:
        return {
            "success": False,
            "reviews": [],
            "all_approved": False,
            "provider": None,
            "message": result["message"],
        }

    raw_text = result["result"]
    parsed = _parse_json_response(raw_text)
    reviews = parsed.get("reviews", [])

    if not isinstance(reviews, list):
        reviews = []

    # Enforce approval threshold
    for review in reviews:
        scores = review.get("scores", {})
        overall = scores.get("overall", 0)
        if overall >= APPROVAL_THRESHOLD:
            review["status"] = "approved"
        else:
            review["status"] = "rejected"

    all_approved = all(r.get("status") == "approved" for r in reviews) if reviews else False

    return {
        "success": True,
        "reviews": reviews,
        "all_approved": all_approved,
        "provider": result["provider"],
        "message": f"Reviewed {len(reviews)} variants via {result['provider']}",
    }
