"""Full Product Generation Pipeline.

Orchestrates the complete product generation flow:
Research -> Create -> Images -> CEO Review -> (Revision if needed) -> Save

Updates product status through: pending -> processing -> ready/needs_review/error
Logs each step to the pipeline_logs table.
"""

import json
import logging
from datetime import datetime

from app.agents.researcher import run_research
from app.agents.creator import run_creator
from app.agents.image_generator import generate_images
from app.agents.ceo_reviewer import run_ceo_review
from app.database import get_db

logger = logging.getLogger(__name__)

MAX_REVISION_ROUNDS = 2


def _log_step(product_id: int, agent: str, status: str, message: str, provider: str = ""):
    """Log a pipeline step to the database."""
    with get_db() as conn:
        conn.execute(
            """INSERT INTO pipeline_logs (product_id, agent, status, message, ai_provider, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (product_id, agent, status, message, provider, datetime.utcnow().isoformat()),
        )


def _update_product_status(product_id: int, status: str):
    """Update the product status."""
    with get_db() as conn:
        conn.execute(
            "UPDATE products SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), product_id),
        )


async def run_pipeline(product_id: int) -> dict:
    """Run the full product generation pipeline.

    Args:
        product_id: Database ID of the product.

    Returns:
        dict with keys:
            success (bool), product_id (int), status (str),
            research_data (dict), variants (list), images (list),
            reviews (list), message (str)
    """
    # Load the product from DB
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return {
                "success": False,
                "product_id": product_id,
                "status": "error",
                "message": "Product not found",
            }
        product = dict(product)

    product_name = product["name"]
    product_type = product.get("product_type", "digital")

    # Parse target_platforms
    try:
        platforms = json.loads(product.get("target_platforms", "[]"))
    except (json.JSONDecodeError, TypeError):
        platforms = []
    if not platforms:
        platforms = ["Gumroad", "Payhip"]

    # Set status to processing
    _update_product_status(product_id, "processing")
    _log_step(product_id, "pipeline", "running", "Pipeline started")

    # -- Step 1: Research --
    _log_step(product_id, "researcher", "running", "Starting market research")
    research_result = await run_research(product_name, product_type)

    if not research_result["success"]:
        _log_step(product_id, "researcher", "error", research_result["message"])
        _update_product_status(product_id, "error")
        return {
            "success": False,
            "product_id": product_id,
            "status": "error",
            "message": f"Research failed: {research_result['message']}",
        }

    research_data = research_result["research_data"]
    _log_step(
        product_id, "researcher", "completed",
        f"Research completed (trending: {research_data.get('trending_score', 'N/A')})",
        research_result.get("provider", ""),
    )

    # Save research data to product
    with get_db() as conn:
        conn.execute(
            "UPDATE products SET research_data = ?, updated_at = ? WHERE id = ?",
            (json.dumps(research_data), datetime.utcnow().isoformat(), product_id),
        )

    # Use platform recommendations from research if available
    recommended = research_data.get("platforms_recommendation", [])
    if recommended:
        platforms = recommended

    # -- Step 2: Create Product Variants --
    _log_step(product_id, "creator", "running", f"Creating variants for {', '.join(platforms)}")
    creator_result = await run_creator(product_name, research_data, platforms)

    if not creator_result["success"]:
        _log_step(product_id, "creator", "error", creator_result["message"])
        _update_product_status(product_id, "error")
        return {
            "success": False,
            "product_id": product_id,
            "status": "error",
            "message": f"Creation failed: {creator_result['message']}",
        }

    variants = creator_result["variants"]
    image_prompts = creator_result["image_prompts"]
    _log_step(
        product_id, "creator", "completed",
        f"Created {len(variants)} variants, {len(image_prompts)} image prompts",
        creator_result.get("provider", ""),
    )

    # -- Step 3: Generate Images --
    _log_step(product_id, "image_generator", "running", f"Generating {len(image_prompts)} images")
    image_result = await generate_images(image_prompts)

    image_urls = [img["image_url"] for img in image_result.get("images", [])]
    if image_result["success"]:
        _log_step(
            product_id, "image_generator", "completed",
            image_result["message"],
        )
    else:
        _log_step(
            product_id, "image_generator", "warning",
            f"Some images failed: {image_result['message']}",
        )

    # -- Step 4: CEO Review (with revision loop) --
    current_variants = variants
    final_reviews: list[dict] = []
    revision_round = 0

    while revision_round <= MAX_REVISION_ROUNDS:
        _log_step(
            product_id, "ceo_reviewer", "running",
            f"CEO review round {revision_round + 1}",
        )

        review_result = await run_ceo_review(product_name, current_variants, research_data)

        if not review_result["success"]:
            _log_step(product_id, "ceo_reviewer", "error", review_result["message"])
            break

        final_reviews = review_result["reviews"]
        _log_step(
            product_id, "ceo_reviewer", "completed",
            f"Review round {revision_round + 1}: "
            f"{'all approved' if review_result['all_approved'] else 'some rejected'}",
            review_result.get("provider", ""),
        )

        if review_result["all_approved"]:
            break

        revision_round += 1
        if revision_round > MAX_REVISION_ROUNDS:
            _log_step(
                product_id, "ceo_reviewer", "warning",
                f"Max revision rounds ({MAX_REVISION_ROUNDS}) reached, flagging for human review",
            )
            break

        # Collect feedback from rejected variants
        feedback_parts = []
        for review in final_reviews:
            if review.get("status") == "rejected":
                platform = review.get("platform", "Unknown")
                fb = review.get("feedback", "")
                feedback_parts.append(f"{platform}: {fb}")

        ceo_feedback = "\n".join(feedback_parts)

        # Re-run creator with CEO feedback
        _log_step(
            product_id, "creator", "running",
            f"Revision round {revision_round}: re-creating with CEO feedback",
        )
        revision_result = await run_creator(
            product_name, research_data, platforms, ceo_feedback=ceo_feedback,
        )

        if revision_result["success"]:
            current_variants = revision_result["variants"]
            _log_step(
                product_id, "creator", "completed",
                f"Revision {revision_round} created {len(current_variants)} variants",
                revision_result.get("provider", ""),
            )
        else:
            _log_step(product_id, "creator", "error", revision_result["message"])
            break

    # -- Step 5: Save Variants to Database --
    all_approved = all(r.get("status") == "approved" for r in final_reviews) if final_reviews else False

    saved_variants = []
    with get_db() as conn:
        for i, variant in enumerate(current_variants):
            review = final_reviews[i] if i < len(final_reviews) else {}
            scores = review.get("scores", {})
            ceo_score = scores.get("overall", 0)
            ceo_status = review.get("status", "pending")
            ceo_feedback_text = review.get("feedback", "")

            tags = variant.get("tags", [])
            if isinstance(tags, list):
                tags_json = json.dumps(tags)
            else:
                tags_json = json.dumps([])

            cursor = conn.execute(
                """INSERT INTO product_variants
                   (product_id, platform, title, description, tags, price,
                    image_urls, ceo_score, ceo_feedback, ceo_status, revision_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    product_id,
                    variant.get("platform", ""),
                    variant.get("title", ""),
                    variant.get("description", ""),
                    tags_json,
                    str(variant.get("price", "0")),
                    json.dumps(image_urls),
                    ceo_score,
                    ceo_feedback_text,
                    ceo_status,
                    revision_round,
                ),
            )
            saved_variants.append({
                "id": cursor.lastrowid,
                "platform": variant.get("platform", ""),
                "title": variant.get("title", ""),
                "ceo_score": ceo_score,
                "ceo_status": ceo_status,
            })

    # Determine final status
    if all_approved:
        final_status = "ready"
    elif revision_round > MAX_REVISION_ROUNDS:
        final_status = "needs_review"
    else:
        final_status = "ready"

    _update_product_status(product_id, final_status)
    _log_step(product_id, "pipeline", "completed", f"Pipeline finished: {final_status}")

    return {
        "success": True,
        "product_id": product_id,
        "status": final_status,
        "research_data": research_data,
        "variants": saved_variants,
        "images": image_urls,
        "reviews": final_reviews,
        "message": f"Pipeline completed: {len(saved_variants)} variants, status={final_status}",
    }
