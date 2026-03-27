"""Caption Generator AI Agent.

Generates unique social media captions for multiple platforms:
Reddit, Tumblr, Twitter, Pinterest, Telegram, Instagram, TikTok,
Facebook, Quora, LinkedIn, Threads.
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
    "Instagram", "TikTok", "Facebook", "Quora", "LinkedIn", "Threads",
]


def _build_caption_prompt(
    product_name: str,
    product_description: str,
    product_url: str,
) -> str:
    """Build the caption generation prompt for all platforms."""
    return f"""You are a social media marketing expert specializing in digital product promotion.

Generate unique, platform-optimized captions for promoting this digital product:

Product: {product_name}
Description: {product_description}
Product URL: {product_url or "(will be added later)"}

Generate a caption for EACH of these 11 platforms, following the specific style guidelines:

- Reddit: Helpful, community-focused, NO hard selling. Value-first approach. Suggest 2-3 relevant subreddits in the caption (e.g. "Perfect for r/productivity, r/digitalnomad"). Be genuine and provide value before mentioning the product.
- Tumblr: Creative, aesthetic, hashtag-heavy, visual language. Use dreamy/artistic tone. Include 5-8 relevant hashtags at the end. Use line breaks for visual flow.
- Twitter: Short, punchy, max 280 chars total. Hook in first line. Include 1-2 relevant hashtags. Add urgency or curiosity.
- Pinterest: SEO-heavy, keyword-rich for discovery. Pin description style with clear benefits. Include relevant keywords naturally. 2-3 sentences focused on searchability.
- Telegram: Direct, informative, well-structured with emojis as bullet points. Include CTA and link placeholder at end. Use clear formatting with line breaks.
- Instagram: Engaging opening hook + value proposition + relevant hashtags (8-12) + clear CTA. Use line breaks and emojis strategically. 3-4 paragraphs.
- TikTok: Trendy, casual, hook in first 3 words. Gen-Z friendly language. Include 3-5 trending-style hashtags. Keep it short and punchy with personality.
- Facebook: Conversational, value-focused, community-building tone. Ask a question to drive engagement. Include a clear CTA. 2-3 short paragraphs.
- Quora: Answer-style format — start with a relevant question, then provide an educational answer that naturally leads to the product. Establish authority. 3-4 paragraphs.
- LinkedIn: Professional, thought-leadership style. Lead with an insight or statistic. Business value proposition. Include a professional CTA. Use line breaks between paragraphs.
- Threads: Casual, conversational, like talking to a friend. Short and punchy. No hashtags needed. Authentic voice, 2-3 short sentences max.

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "captions": [
        {{
            "platform": "<platform name exactly as listed above>",
            "caption": "<the full caption text>",
            "suggested_hashtags": ["<hashtag1>", "<hashtag2>"],
            "suggested_subreddits": ["<subreddit1>"]
        }}
    ]
}}

IMPORTANT:
- Each caption MUST be unique and optimized for its specific platform's culture and format
- suggested_hashtags should only be populated for platforms that use them (Instagram, TikTok, Tumblr, Twitter)
- suggested_subreddits should only be populated for Reddit
- For other platforms, set these arrays to empty []
- Ensure the captions feel native to each platform, not like copy-pasted marketing"""


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

            hashtags = cap.get("suggested_hashtags", [])
            subreddits = cap.get("suggested_subreddits", [])

            metadata = json.dumps({
                "hashtags": hashtags if isinstance(hashtags, list) else [],
                "subreddits": subreddits if isinstance(subreddits, list) else [],
            })

            cursor = conn.execute(
                """INSERT INTO social_posts (product_id, platform, caption, post_status, voice_url)
                   VALUES (?, ?, ?, 'draft', ?)""",
                (product_id, platform, caption_text, metadata),
            )
            saved_captions.append({
                "id": cursor.lastrowid,
                "platform": platform,
                "caption": caption_text,
                "post_status": "draft",
                "hashtags": hashtags if isinstance(hashtags, list) else [],
                "subreddits": subreddits if isinstance(subreddits, list) else [],
            })

    return {
        "success": True,
        "captions": saved_captions,
        "provider": result["provider"],
        "message": f"Generated {len(saved_captions)} captions via {result['provider']}",
    }
