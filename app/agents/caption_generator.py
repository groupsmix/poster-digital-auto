"""Caption Generator AI Agent.

Generates unique social media captions for multiple platforms:
Reddit, Tumblr, Twitter, Pinterest, Telegram, Instagram, TikTok,
Facebook, Quora, LinkedIn.
Saves generated captions to the social_posts table.
"""

import json
import logging
import re

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

SOCIAL_PLATFORMS = [
    "Reddit", "Tumblr", "Twitter", "Pinterest", "Telegram",
    "Instagram", "TikTok", "Facebook", "Quora", "LinkedIn",
]


def _build_caption_prompt(
    product_name: str,
    product_description: str,
    product_url: str,
) -> str:
    """Build the caption generation prompt for all platforms."""
    return f"""You are a social media marketing expert.

Generate unique, platform-optimized captions for promoting this digital product:

Product: {product_name}
Description: {product_description}
Product URL: {product_url}

Generate a caption for EACH of these platforms:
- Reddit: Helpful, community-focused, NO hard selling. Value-first approach.
- Tumblr: Creative, aesthetic, hashtag-heavy, visual language.
- Twitter: Short, punchy, max 280 chars. Hook in first line.
- Pinterest: SEO-heavy, keyword-rich for discovery. Pin description style.
- Telegram: Direct, informative, include CTA.
- Instagram: Engaging caption + relevant hashtags + CTA.
- TikTok: Trendy, casual, hook in first line. Gen-Z friendly.
- Facebook: Conversational, value-focused, community-building.
- Quora: Answer-style, educational, establish authority.
- LinkedIn: Professional, value-proposition focused, thought-leadership.

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "captions": [
        {{
            "platform": "<platform name>",
            "caption": "<the full caption text>"
        }}
    ]
}}

Each caption must be unique and optimized for its specific platform's culture and format."""


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

    logger.warning("Could not parse caption JSON response")
    return {"captions": []}


async def generate_captions(
    product_id: int,
    product_name: str,
    product_description: str = "",
    product_url: str = "",
) -> dict:
    """Generate social media captions and save to database.

    Args:
        product_id: Database ID of the product.
        product_name: Name of the product.
        product_description: Brief description (from first variant or brief).
        product_url: URL to the product page.

    Returns:
        dict with keys:
            success (bool), captions (list), provider (str), message (str)
    """
    prompt = _build_caption_prompt(product_name, product_description, product_url)
    result = await call_text_with_failover("captions", prompt)

    if not result["success"]:
        return {
            "success": False,
            "captions": [],
            "provider": None,
            "message": result["message"],
        }

    raw_text = result["result"]
    parsed = _parse_json_response(raw_text)
    captions = parsed.get("captions", [])

    if not isinstance(captions, list):
        captions = []

    # Save captions to social_posts table
    saved_captions: list[dict] = []
    with get_db() as conn:
        for cap in captions:
            platform = cap.get("platform", "")
            caption_text = cap.get("caption", "")
            if not platform or not caption_text:
                continue

            cursor = conn.execute(
                """INSERT INTO social_posts (product_id, platform, caption, post_status)
                   VALUES (?, ?, ?, 'draft')""",
                (product_id, platform, caption_text),
            )
            saved_captions.append({
                "id": cursor.lastrowid,
                "platform": platform,
                "caption": caption_text,
                "post_status": "draft",
            })

    return {
        "success": True,
        "captions": saved_captions,
        "provider": result["provider"],
        "message": f"Generated {len(saved_captions)} captions via {result['provider']}",
    }
