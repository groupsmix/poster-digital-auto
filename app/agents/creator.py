"""Product Creator AI Agent.

Takes a product name, research data, and list of platforms.
Calls text AI with failover (chain: create) to generate platform-specific
product variants with unique titles, descriptions, tags, prices,
and image prompts for thumbnail generation.
"""

import json
import logging
import re

from app.ai_failover import call_text_with_failover

logger = logging.getLogger(__name__)

PLATFORM_TONES: dict[str, str] = {
    "Gumroad": "casual, creator-friendly, direct",
    "Payhip": "professional, clean, value-focused",
    "Lemon Squeezy": "modern, tech-savvy, concise",
}


def _build_creator_prompt(
    product_name: str,
    research_data: dict,
    platforms: list[str],
    ceo_feedback: str = "",
) -> str:
    """Build the product creation prompt."""
    platform_instructions = ""
    for platform in platforms:
        tone = PLATFORM_TONES.get(platform, "professional")
        platform_instructions += f"  - {platform}: tone should be {tone}\n"

    feedback_section = ""
    if ceo_feedback:
        feedback_section = f"""
IMPORTANT - CEO Feedback from previous review (incorporate this feedback):
{ceo_feedback}
"""

    keywords = ", ".join(research_data.get("keywords", []))
    price_range = research_data.get("price_range", {})
    min_price = price_range.get("min", 9.99)
    max_price = price_range.get("max", 49.99)

    return f"""You are a digital product creator and copywriter.

Create compelling product listings for the following product:

Product Name: {product_name}
Target Audience: {research_data.get("target_audience", "General audience")}
Unique Angle: {research_data.get("unique_angle", "")}
Keywords: {keywords}
Price Range: ${min_price:.2f} - ${max_price:.2f}
{feedback_section}
Create a variant for EACH of these platforms:
{platform_instructions}

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "variants": [
        {{
            "platform": "<platform name>",
            "title": "<unique, compelling title for this platform>",
            "description": "<platform-appropriate description, 100-300 words>",
            "tags": [<list of 5-10 relevant tags as strings>],
            "price": "<price as string, e.g. 19.99>"
        }}
    ],
    "image_prompts": [
        "<detailed prompt for thumbnail image 1>",
        "<detailed prompt for thumbnail image 2>",
        "<detailed prompt for thumbnail image 3>"
    ]
}}

Each platform variant must have a DIFFERENT title and description style.
Image prompts should describe professional, eye-catching product thumbnails."""


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

    logger.warning("Could not parse Creator AI JSON response")
    return {"variants": [], "image_prompts": []}


async def run_creator(
    product_name: str,
    research_data: dict,
    platforms: list[str],
    ceo_feedback: str = "",
) -> dict:
    """Run the Product Creator AI agent.

    Args:
        product_name: Name of the product.
        research_data: Research data from the Researcher agent.
        platforms: List of platform names to create variants for.
        ceo_feedback: Optional CEO feedback for revision rounds.

    Returns:
        dict with keys:
            success (bool), variants (list), image_prompts (list),
            provider (str), message (str)
    """
    if not platforms:
        platforms = ["Gumroad", "Payhip"]

    prompt = _build_creator_prompt(product_name, research_data, platforms, ceo_feedback)
    result = await call_text_with_failover("create", prompt)

    if not result["success"]:
        return {
            "success": False,
            "variants": [],
            "image_prompts": [],
            "provider": None,
            "message": result["message"],
        }

    raw_text = result["result"]
    parsed = _parse_json_response(raw_text)

    variants = parsed.get("variants", [])
    image_prompts = parsed.get("image_prompts", [])

    # Ensure we have at least empty lists
    if not isinstance(variants, list):
        variants = []
    if not isinstance(image_prompts, list):
        image_prompts = []

    return {
        "success": True,
        "variants": variants,
        "image_prompts": image_prompts,
        "provider": result["provider"],
        "message": f"Created {len(variants)} variants via {result['provider']}",
    }
