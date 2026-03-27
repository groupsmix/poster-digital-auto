"""Researcher AI Agent.

Takes a product name + type, calls text AI with failover (chain: research),
and returns structured market research data including trending score,
keywords, competitor analysis, price range, target audience, unique angle,
and platform recommendations.
"""

import json
import logging
import re

from app.ai_failover import call_text_with_failover

logger = logging.getLogger(__name__)


def _build_research_prompt(product_name: str, product_type: str) -> str:
    """Build the research prompt asking for JSON output."""
    return f"""You are a market research analyst specializing in digital products.

Research the following product idea and provide detailed market analysis:

Product Name: {product_name}
Product Type: {product_type}

Respond with ONLY a valid JSON object (no markdown, no code fences) with these exact keys:
{{
    "trending_score": <integer 1-100, how trending/in-demand this product idea is>,
    "keywords": [<list of 8-12 relevant SEO keywords as strings>],
    "competitor_analysis": "<brief analysis of existing competitors and market gaps>",
    "price_range": {{
        "min": <float, suggested minimum price in USD>,
        "max": <float, suggested maximum price in USD>,
        "recommended": <float, recommended price point in USD>
    }},
    "target_audience": "<description of the ideal target audience>",
    "unique_angle": "<suggested unique selling proposition or angle>",
    "platforms_recommendation": [<list of best selling platforms from: Gumroad, Payhip, Lemon Squeezy>]
}}

Be specific, data-driven, and realistic in your analysis."""


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

    # Return a fallback structure
    logger.warning("Could not parse JSON from AI response, using fallback")
    return {
        "trending_score": 50,
        "keywords": [product_name_from_text(text)],
        "competitor_analysis": text[:500] if text else "Analysis unavailable",
        "price_range": {"min": 9.99, "max": 49.99, "recommended": 19.99},
        "target_audience": "General digital product buyers",
        "unique_angle": "Unique approach to the topic",
        "platforms_recommendation": ["Gumroad", "Payhip"],
    }


def product_name_from_text(text: str) -> str:
    """Extract a keyword from raw text as fallback."""
    words = text.split()[:5]
    return " ".join(words) if words else "digital product"


async def run_research(product_name: str, product_type: str) -> dict:
    """Run the Researcher AI agent.

    Args:
        product_name: Name of the product to research.
        product_type: Type of product (e.g., "digital", "ebook", "course").

    Returns:
        dict with keys:
            success (bool), research_data (dict), provider (str), message (str)
    """
    prompt = _build_research_prompt(product_name, product_type)

    result = await call_text_with_failover("research", prompt)

    if not result["success"]:
        return {
            "success": False,
            "research_data": None,
            "provider": None,
            "message": result["message"],
        }

    raw_text = result["result"]
    research_data = _parse_json_response(raw_text)

    # Validate required fields exist
    required_keys = [
        "trending_score", "keywords", "competitor_analysis",
        "price_range", "target_audience", "unique_angle",
        "platforms_recommendation",
    ]
    for key in required_keys:
        if key not in research_data:
            if key == "trending_score":
                research_data[key] = 50
            elif key == "keywords":
                research_data[key] = [product_name]
            elif key == "price_range":
                research_data[key] = {"min": 9.99, "max": 49.99, "recommended": 19.99}
            elif key == "platforms_recommendation":
                research_data[key] = ["Gumroad", "Payhip"]
            else:
                research_data[key] = ""

    return {
        "success": True,
        "research_data": research_data,
        "provider": result["provider"],
        "message": f"Research completed via {result['provider']}",
    }
