"""Auto-Posting Agent.

Handles automated posting to supported platforms:
- Tumblr API: auto-post text + image
- Pinterest API: auto-create pin with image + SEO description
- Telegram Bot API: auto-send message to channel

Each platform requires API key configuration in .env.
"""

import logging
import os
from datetime import datetime

import httpx

from app.database import get_db

logger = logging.getLogger(__name__)

# Supported auto-posting platforms
AUTO_POST_PLATFORMS = ["Tumblr", "Pinterest", "Telegram"]


def _get_env(key: str) -> str:
    """Get environment variable or empty string."""
    return os.environ.get(key, "")


async def post_to_telegram(
    caption: str,
    image_path: str = "",
    channel_id: str = "",
) -> dict:
    """Post a message to a Telegram channel via Bot API.

    Requires:
        TELEGRAM_BOT_TOKEN: Bot token from @BotFather
        TELEGRAM_CHANNEL_ID: Channel ID (e.g., @mychannel or -100xxxx)
    """
    bot_token = _get_env("TELEGRAM_BOT_TOKEN")
    if not channel_id:
        channel_id = _get_env("TELEGRAM_CHANNEL_ID")

    if not bot_token:
        return {"success": False, "message": "TELEGRAM_BOT_TOKEN not configured", "post_url": ""}
    if not channel_id:
        return {"success": False, "message": "TELEGRAM_CHANNEL_ID not configured", "post_url": ""}

    base_url = f"https://api.telegram.org/bot{bot_token}"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            if image_path and os.path.isfile(image_path):
                # Send photo with caption
                with open(image_path, "rb") as photo:
                    response = await client.post(
                        f"{base_url}/sendPhoto",
                        data={"chat_id": channel_id, "caption": caption, "parse_mode": "HTML"},
                        files={"photo": ("image.png", photo, "image/png")},
                    )
            else:
                # Send text message
                response = await client.post(
                    f"{base_url}/sendMessage",
                    json={
                        "chat_id": channel_id,
                        "text": caption,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": False,
                    },
                )

            data = response.json()
            if data.get("ok"):
                message_id = data["result"]["message_id"]
                # Build post URL
                clean_channel = channel_id.lstrip("@")
                if clean_channel.startswith("-100"):
                    post_url = f"https://t.me/c/{clean_channel[4:]}/{message_id}"
                else:
                    post_url = f"https://t.me/{clean_channel}/{message_id}"

                return {
                    "success": True,
                    "message": "Posted to Telegram successfully",
                    "post_url": post_url,
                    "message_id": message_id,
                }
            else:
                error_desc = data.get("description", "Unknown error")
                return {"success": False, "message": f"Telegram API error: {error_desc}", "post_url": ""}

        except httpx.HTTPError as e:
            logger.error("Telegram posting error: %s", str(e))
            return {"success": False, "message": f"HTTP error: {str(e)}", "post_url": ""}


async def post_to_tumblr(
    caption: str,
    image_path: str = "",
    blog_name: str = "",
    tags: list[str] | None = None,
) -> dict:
    """Post to Tumblr via the Tumblr API v2.

    Requires:
        TUMBLR_API_KEY: OAuth consumer key
        TUMBLR_API_SECRET: OAuth consumer secret
        TUMBLR_ACCESS_TOKEN: OAuth access token
        TUMBLR_ACCESS_SECRET: OAuth access token secret
        TUMBLR_BLOG_NAME: Blog identifier (e.g., myblog.tumblr.com)
    """
    api_key = _get_env("TUMBLR_API_KEY")
    access_token = _get_env("TUMBLR_ACCESS_TOKEN")
    if not blog_name:
        blog_name = _get_env("TUMBLR_BLOG_NAME")

    if not api_key or not access_token:
        return {"success": False, "message": "Tumblr API credentials not configured", "post_url": ""}
    if not blog_name:
        return {"success": False, "message": "TUMBLR_BLOG_NAME not configured", "post_url": ""}

    base_url = f"https://api.tumblr.com/v2/blog/{blog_name}/post"

    tag_str = ",".join(tags) if tags else ""

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            headers = {"Authorization": f"Bearer {access_token}"}

            if image_path and os.path.isfile(image_path):
                # Photo post with caption
                with open(image_path, "rb") as photo:
                    response = await client.post(
                        base_url,
                        headers=headers,
                        data={
                            "type": "photo",
                            "caption": caption,
                            "tags": tag_str,
                        },
                        files={"data[0]": ("image.png", photo, "image/png")},
                    )
            else:
                # Text post
                response = await client.post(
                    base_url,
                    headers=headers,
                    json={
                        "type": "text",
                        "title": "",
                        "body": caption,
                        "tags": tag_str,
                    },
                )

            if response.status_code in (200, 201):
                data = response.json()
                post_id = data.get("response", {}).get("id", "")
                clean_blog = blog_name.replace(".tumblr.com", "")
                post_url = f"https://{clean_blog}.tumblr.com/post/{post_id}" if post_id else ""
                return {
                    "success": True,
                    "message": "Posted to Tumblr successfully",
                    "post_url": post_url,
                }
            else:
                error_msg = response.text[:200]
                return {"success": False, "message": f"Tumblr API error ({response.status_code}): {error_msg}", "post_url": ""}

        except httpx.HTTPError as e:
            logger.error("Tumblr posting error: %s", str(e))
            return {"success": False, "message": f"HTTP error: {str(e)}", "post_url": ""}


async def post_to_pinterest(
    caption: str,
    image_url: str = "",
    board_id: str = "",
    link: str = "",
    title: str = "",
) -> dict:
    """Create a pin on Pinterest via the Pinterest API v5.

    Requires:
        PINTEREST_ACCESS_TOKEN: OAuth access token
        PINTEREST_BOARD_ID: Board ID to pin to
    """
    access_token = _get_env("PINTEREST_ACCESS_TOKEN")
    if not board_id:
        board_id = _get_env("PINTEREST_BOARD_ID")

    if not access_token:
        return {"success": False, "message": "PINTEREST_ACCESS_TOKEN not configured", "post_url": ""}
    if not board_id:
        return {"success": False, "message": "PINTEREST_BOARD_ID not configured", "post_url": ""}

    base_url = "https://api.pinterest.com/v5/pins"

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            pin_data: dict = {
                "board_id": board_id,
                "description": caption,
            }

            if title:
                pin_data["title"] = title

            if link:
                pin_data["link"] = link

            if image_url:
                pin_data["media_source"] = {
                    "source_type": "image_url",
                    "url": image_url,
                }

            response = await client.post(base_url, headers=headers, json=pin_data)

            if response.status_code in (200, 201):
                data = response.json()
                pin_id = data.get("id", "")
                post_url = f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else ""
                return {
                    "success": True,
                    "message": "Pinned to Pinterest successfully",
                    "post_url": post_url,
                }
            else:
                error_msg = response.text[:200]
                return {
                    "success": False,
                    "message": f"Pinterest API error ({response.status_code}): {error_msg}",
                    "post_url": "",
                }

        except httpx.HTTPError as e:
            logger.error("Pinterest posting error: %s", str(e))
            return {"success": False, "message": f"HTTP error: {str(e)}", "post_url": ""}


async def auto_post(
    post_id: int,
    image_path: str = "",
    image_url: str = "",
) -> dict:
    """Auto-post a social post to its platform.

    Reads the social_posts record, determines the platform,
    and dispatches to the appropriate posting function.

    Args:
        post_id: ID of the social_posts record.
        image_path: Local path to image file (for Telegram, Tumblr).
        image_url: Public URL of image (for Pinterest).

    Returns:
        dict with success, message, post_url, platform.
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return {"success": False, "message": "Social post not found", "post_url": "", "platform": ""}

    post = dict(row)
    platform = post["platform"]
    caption = post["caption"] or ""

    if platform not in AUTO_POST_PLATFORMS:
        return {
            "success": False,
            "message": f"Auto-posting not supported for {platform}. Use Copy Center to copy and post manually.",
            "post_url": "",
            "platform": platform,
        }

    result: dict = {"success": False, "message": "", "post_url": "", "platform": platform}

    if platform == "Telegram":
        result = await post_to_telegram(caption=caption, image_path=image_path)
        result["platform"] = platform
    elif platform == "Tumblr":
        result = await post_to_tumblr(caption=caption, image_path=image_path)
        result["platform"] = platform
    elif platform == "Pinterest":
        result = await post_to_pinterest(caption=caption, image_url=image_url, title=post.get("product_name", ""))
        result["platform"] = platform

    # Update post status in database
    now = datetime.utcnow().isoformat()
    with get_db() as conn:
        if result.get("success"):
            conn.execute(
                "UPDATE social_posts SET post_status = 'posted', post_url = ?, posted_at = ? WHERE id = ?",
                (result.get("post_url", ""), now, post_id),
            )
        else:
            conn.execute(
                "UPDATE social_posts SET post_status = 'error' WHERE id = ?",
                (post_id,),
            )

    return result


def get_auto_post_config() -> dict:
    """Get configuration status of auto-posting platforms."""
    return {
        "telegram": {
            "configured": bool(_get_env("TELEGRAM_BOT_TOKEN") and _get_env("TELEGRAM_CHANNEL_ID")),
            "bot_token_set": bool(_get_env("TELEGRAM_BOT_TOKEN")),
            "channel_id_set": bool(_get_env("TELEGRAM_CHANNEL_ID")),
        },
        "tumblr": {
            "configured": bool(_get_env("TUMBLR_API_KEY") and _get_env("TUMBLR_ACCESS_TOKEN") and _get_env("TUMBLR_BLOG_NAME")),
            "api_key_set": bool(_get_env("TUMBLR_API_KEY")),
            "access_token_set": bool(_get_env("TUMBLR_ACCESS_TOKEN")),
            "blog_name_set": bool(_get_env("TUMBLR_BLOG_NAME")),
        },
        "pinterest": {
            "configured": bool(_get_env("PINTEREST_ACCESS_TOKEN") and _get_env("PINTEREST_BOARD_ID")),
            "access_token_set": bool(_get_env("PINTEREST_ACCESS_TOKEN")),
            "board_id_set": bool(_get_env("PINTEREST_BOARD_ID")),
        },
    }
