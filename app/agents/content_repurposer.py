"""Content Repurposing Engine for AI Product Factory.

From 1 product listing, AI generates content for multiple formats:
- Blog post (SEO)
- YouTube script (60-second video)
- Twitter/X thread (5-7 tweets)
- Instagram carousel (5-7 slide descriptions)
- Newsletter issue
- Quora answer template
- Pinterest pin description

All generated content is saved to the repurposed_content table.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover, TASK_CHAINS
from app.database import get_db

logger = logging.getLogger(__name__)

# Register repurpose task chain
TASK_CHAINS["repurpose"] = ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen", "mistral_large"]

CONTENT_TYPES = [
    "blog_post",
    "youtube_script",
    "twitter_thread",
    "instagram_carousel",
    "newsletter",
    "quora_answer",
    "pinterest_pin",
]

CONTENT_TYPE_LABELS = {
    "blog_post": "Blog Post (SEO)",
    "youtube_script": "YouTube Script (60s)",
    "twitter_thread": "Twitter/X Thread",
    "instagram_carousel": "Instagram Carousel",
    "newsletter": "Newsletter Issue",
    "quora_answer": "Quora Answer",
    "pinterest_pin": "Pinterest Pin",
}


def _build_repurpose_prompt(product_name: str, product_description: str, product_type: str) -> str:
    """Build the AI prompt for content repurposing."""
    return f"""You are an expert content marketer. Given a product listing, generate repurposed content for 7 different formats.

Product Name: {product_name}
Product Type: {product_type}
Product Description: {product_description}

Generate content for ALL 7 formats below. Return ONLY valid JSON (no markdown, no code blocks, no extra text).

Return this exact JSON structure:
{{
  "blog_post": "A full SEO-optimized blog post (800-1200 words) with title, introduction, body sections with H2 headings, and conclusion. Include relevant keywords naturally.",
  "youtube_script": "A 60-second video script with [INTRO], [HOOK], [MAIN POINTS], [CTA] sections. Include visual cues in brackets.",
  "twitter_thread": "A thread of 5-7 tweets. Each tweet on a new line, numbered 1/ 2/ 3/ etc. First tweet is the hook. Last tweet is a CTA. Each tweet under 280 chars.",
  "instagram_carousel": "5-7 slide descriptions for an Instagram carousel. Format: Slide 1: [title] - [description]. Each slide should tell part of the story.",
  "newsletter": "A complete newsletter issue with subject line, preview text, greeting, body with sections, and sign-off. Engaging and personal tone.",
  "quora_answer": "An authoritative Quora-style answer (300-500 words) to the question 'What is the best [product type] for [use case]?' Naturally mentions the product as a recommendation.",
  "pinterest_pin": "A Pinterest pin description (150-300 chars) with relevant keywords for Pinterest SEO. Include 3-5 hashtags."
}}"""


async def repurpose_product(product_id: int) -> dict:
    """Generate repurposed content for a product across 7 formats.

    Args:
        product_id: The product ID to repurpose content for.

    Returns:
        dict with success status, generated content, and metadata.
    """
    # Fetch product details
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_name = product["name"]
        product_type = product["product_type"] or "digital"
        product_description = product["brief"] or ""

        # Try to get richer description from variants
        if not product_description:
            variant = conn.execute(
                "SELECT description FROM product_variants WHERE product_id = ? LIMIT 1",
                (product_id,),
            ).fetchone()
            if variant:
                product_description = variant["description"] or ""

    if not product_description:
        product_description = f"A {product_type} product called {product_name}"

    # Build prompt and call AI
    prompt = _build_repurpose_prompt(product_name, product_description, product_type)

    # Log pipeline start
    with get_db() as conn:
        conn.execute(
            "INSERT INTO pipeline_logs (product_id, agent, status, message) VALUES (?, ?, ?, ?)",
            (product_id, "content_repurposer", "running", "Generating repurposed content for 7 formats..."),
        )

    ai_result = await call_text_with_failover("repurpose", prompt)

    if not ai_result["success"]:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message) VALUES (?, ?, ?, ?, ?)",
                (product_id, "content_repurposer", ai_result.get("provider"), "error", ai_result["message"]),
            )
        return {"success": False, "message": ai_result["message"]}

    # Parse AI response
    raw_text = ai_result["result"]
    # Strip markdown code blocks if present
    if "```json" in raw_text:
        raw_text = raw_text.split("```json", 1)[1]
        if "```" in raw_text:
            raw_text = raw_text.split("```", 1)[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1]
        if "```" in raw_text:
            raw_text = raw_text.split("```", 1)[0]

    try:
        content_data = json.loads(raw_text.strip())
    except json.JSONDecodeError:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message) VALUES (?, ?, ?, ?, ?)",
                (product_id, "content_repurposer", ai_result.get("provider"), "error", "Failed to parse AI response as JSON"),
            )
        return {"success": False, "message": "Failed to parse AI response"}

    # Save to repurposed_content table
    saved_content = []
    with get_db() as conn:
        # Clear existing repurposed content for this product
        conn.execute("DELETE FROM repurposed_content WHERE product_id = ?", (product_id,))

        for content_type in CONTENT_TYPES:
            content_text = content_data.get(content_type, "")
            if not content_text:
                continue

            platform_map = {
                "blog_post": "Blog",
                "youtube_script": "YouTube",
                "twitter_thread": "Twitter",
                "instagram_carousel": "Instagram",
                "newsletter": "Email",
                "quora_answer": "Quora",
                "pinterest_pin": "Pinterest",
            }

            conn.execute(
                """INSERT INTO repurposed_content (product_id, content_type, content, platform, post_status)
                   VALUES (?, ?, ?, ?, ?)""",
                (product_id, content_type, content_text, platform_map.get(content_type, ""), "draft"),
            )

            saved_content.append({
                "content_type": content_type,
                "label": CONTENT_TYPE_LABELS.get(content_type, content_type),
                "content": content_text,
                "platform": platform_map.get(content_type, ""),
                "post_status": "draft",
            })

        # Log success
        conn.execute(
            "INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message) VALUES (?, ?, ?, ?, ?)",
            (product_id, "content_repurposer", ai_result.get("provider"), "success",
             f"Generated {len(saved_content)} content formats"),
        )

    return {
        "success": True,
        "product_id": product_id,
        "content": saved_content,
        "count": len(saved_content),
        "provider": ai_result.get("provider"),
        "message": f"Generated {len(saved_content)} repurposed content formats",
    }


def get_repurposed_content(product_id: int) -> list[dict]:
    """Fetch all repurposed content for a product.

    Args:
        product_id: The product ID.

    Returns:
        List of repurposed content dicts.
    """
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM repurposed_content WHERE product_id = ? ORDER BY id",
            (product_id,),
        ).fetchall()

    result = []
    for row in rows:
        item = dict(row)
        item["label"] = CONTENT_TYPE_LABELS.get(item["content_type"], item["content_type"])
        result.append(item)

    return result
