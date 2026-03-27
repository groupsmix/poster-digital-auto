"""Image Generator Agent.

Takes image prompts from the Creator agent, calls image AI with failover
(FLUX -> HuggingFace), saves images to disk, and returns URLs.
"""

import logging

from app.ai_failover import call_image_with_failover

logger = logging.getLogger(__name__)


async def generate_images(image_prompts: list[str]) -> dict:
    """Generate images from a list of prompts using AI with failover.

    Args:
        image_prompts: List of text prompts for image generation.

    Returns:
        dict with keys:
            success (bool), images (list of dicts), failed (list),
            message (str)
    """
    if not image_prompts:
        return {
            "success": True,
            "images": [],
            "failed": [],
            "message": "No image prompts provided",
        }

    images: list[dict] = []
    failed: list[dict] = []

    for i, prompt in enumerate(image_prompts):
        logger.info("Generating image %d/%d: %s...", i + 1, len(image_prompts), prompt[:50])

        result = await call_image_with_failover(prompt)

        if result["success"]:
            images.append({
                "prompt": prompt,
                "image_url": result["image_url"],
                "local_path": result.get("local_path", ""),
                "provider": result["provider"],
            })
        else:
            failed.append({
                "prompt": prompt,
                "error": result["message"],
            })
            logger.warning("Failed to generate image %d: %s", i + 1, result["message"])

    overall_success = len(images) > 0

    return {
        "success": overall_success,
        "images": images,
        "failed": failed,
        "message": f"Generated {len(images)}/{len(image_prompts)} images",
    }
