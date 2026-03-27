"""Content Calendar & Scheduler module.

Provides:
- Calendar API logic (get posts in date range, schedule, reschedule, unschedule)
- AI-powered optimal posting time suggestions per platform
- Batch scheduling (schedule multiple products across days)
- Background task to check and publish scheduled posts
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from app.agents.auto_poster import auto_post
from app.database import get_db

logger = logging.getLogger(__name__)

# ── Platform optimal posting times (AI-suggested defaults) ──────────────

PLATFORM_OPTIMAL_TIMES = {
    "Reddit": {
        "best_days": ["Tuesday", "Thursday"],
        "best_hours": [9, 10, 13],  # EST
        "timezone": "EST",
        "tip": "Reddit: best engagement Tue/Thu 9-10am EST. Avoid weekends.",
    },
    "Instagram": {
        "best_days": ["Monday", "Wednesday", "Friday"],
        "best_hours": [18, 19, 12],  # EST
        "timezone": "EST",
        "tip": "Instagram: best engagement Mon/Wed/Fri 6-7pm EST. Lunch posts also do well.",
    },
    "Twitter": {
        "best_days": ["Monday", "Tuesday", "Wednesday", "Thursday"],
        "best_hours": [9, 12, 17],  # EST
        "timezone": "EST",
        "tip": "Twitter: best engagement weekdays 9am, 12pm, 5pm EST.",
    },
    "TikTok": {
        "best_days": ["Tuesday", "Thursday", "Friday"],
        "best_hours": [10, 19, 21],  # EST
        "timezone": "EST",
        "tip": "TikTok: best engagement Tue/Thu/Fri 10am or 7-9pm EST.",
    },
    "Facebook": {
        "best_days": ["Wednesday", "Thursday", "Friday"],
        "best_hours": [9, 13, 16],  # EST
        "timezone": "EST",
        "tip": "Facebook: best engagement Wed-Fri 9am, 1pm, 4pm EST.",
    },
    "Pinterest": {
        "best_days": ["Saturday", "Sunday", "Friday"],
        "best_hours": [20, 21, 14],  # EST
        "timezone": "EST",
        "tip": "Pinterest: best engagement weekends 8-9pm EST. Fri afternoons too.",
    },
    "Telegram": {
        "best_days": ["Monday", "Wednesday", "Friday"],
        "best_hours": [10, 15, 19],  # EST
        "timezone": "EST",
        "tip": "Telegram: best engagement Mon/Wed/Fri 10am, 3pm, 7pm EST.",
    },
    "Tumblr": {
        "best_days": ["Tuesday", "Wednesday"],
        "best_hours": [19, 20, 22],  # EST
        "timezone": "EST",
        "tip": "Tumblr: best engagement Tue/Wed evenings 7-10pm EST.",
    },
    "LinkedIn": {
        "best_days": ["Tuesday", "Wednesday", "Thursday"],
        "best_hours": [8, 10, 12],  # EST
        "timezone": "EST",
        "tip": "LinkedIn: best engagement Tue-Thu 8am, 10am, 12pm EST.",
    },
    "Quora": {
        "best_days": ["Monday", "Tuesday", "Wednesday"],
        "best_hours": [10, 14, 16],  # EST
        "timezone": "EST",
        "tip": "Quora: best engagement Mon-Wed 10am, 2pm, 4pm EST.",
    },
    "Threads": {
        "best_days": ["Monday", "Wednesday", "Friday"],
        "best_hours": [12, 17, 19],  # EST
        "timezone": "EST",
        "tip": "Threads: best engagement Mon/Wed/Fri 12pm, 5pm, 7pm EST.",
    },
}

DAY_NAME_TO_NUM = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}

# Platform colors for frontend reference
PLATFORM_COLORS = {
    "Reddit": "#FF4500",
    "Instagram": "#E1306C",
    "Twitter": "#1DA1F2",
    "TikTok": "#000000",
    "Facebook": "#1877F2",
    "Pinterest": "#E60023",
    "Telegram": "#0088CC",
    "Tumblr": "#35465C",
    "LinkedIn": "#0A66C2",
    "Quora": "#B92B27",
    "Threads": "#000000",
    "Gumroad": "#FF90E8",
    "Payhip": "#00B4D8",
    "Lemon Squeezy": "#FFC233",
}


# ── Calendar Queries ────────────────────────────────────────────────────

def get_calendar_posts(start: str, end: str) -> list[dict]:
    """Get all scheduled posts within a date range.

    Args:
        start: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS).
        end: End date in ISO format.

    Returns:
        List of social post dicts with product info.
    """
    with get_db() as conn:
        rows = conn.execute(
            """SELECT sp.*, p.name as product_name
               FROM social_posts sp
               LEFT JOIN products p ON sp.product_id = p.id
               WHERE sp.scheduled_at IS NOT NULL
                 AND sp.scheduled_at >= ?
                 AND sp.scheduled_at <= ?
               ORDER BY sp.scheduled_at ASC""",
            (start, end),
        ).fetchall()

    posts = []
    for r in rows:
        post = dict(r)
        # Parse metadata from voice_url field
        metadata = {}
        voice_url = post.get("voice_url", "")
        if voice_url:
            try:
                metadata = json.loads(voice_url)
            except (json.JSONDecodeError, TypeError):
                pass
        if isinstance(metadata, dict):
            post["hashtags"] = metadata.get("hashtags", [])
        else:
            post["hashtags"] = []
        posts.append(post)

    return posts


def schedule_post(post_id: int, scheduled_at: str) -> dict:
    """Schedule a social post for a specific time.

    Args:
        post_id: ID of the social_posts record.
        scheduled_at: ISO datetime string for when to publish.

    Returns:
        Updated post dict.
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return {"error": "Social post not found"}

        conn.execute(
            "UPDATE social_posts SET scheduled_at = ?, post_status = 'scheduled' WHERE id = ?",
            (scheduled_at, post_id),
        )
        updated = conn.execute(
            """SELECT sp.*, p.name as product_name
               FROM social_posts sp
               LEFT JOIN products p ON sp.product_id = p.id
               WHERE sp.id = ?""",
            (post_id,),
        ).fetchone()

    return dict(updated) if updated else {}


def reschedule_post(post_id: int, scheduled_at: str) -> dict:
    """Reschedule an existing scheduled post.

    Args:
        post_id: ID of the social_posts record.
        scheduled_at: New ISO datetime string.

    Returns:
        Updated post dict.
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return {"error": "Social post not found"}

        conn.execute(
            "UPDATE social_posts SET scheduled_at = ? WHERE id = ?",
            (scheduled_at, post_id),
        )
        updated = conn.execute(
            """SELECT sp.*, p.name as product_name
               FROM social_posts sp
               LEFT JOIN products p ON sp.product_id = p.id
               WHERE sp.id = ?""",
            (post_id,),
        ).fetchone()

    return dict(updated) if updated else {}


def unschedule_post(post_id: int) -> dict:
    """Remove a post from the schedule.

    Args:
        post_id: ID of the social_posts record.

    Returns:
        Result dict.
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            return {"error": "Social post not found"}

        # Reset schedule and status
        conn.execute(
            "UPDATE social_posts SET scheduled_at = NULL, post_status = 'pending' WHERE id = ? AND post_status = 'scheduled'",
            (post_id,),
        )

    return {"message": "Post unscheduled", "id": post_id}


# ── AI Scheduling Suggestions ──────────────────────────────────────────

def get_ai_schedule_suggestions(platform: str | None = None) -> list[dict]:
    """Get AI-powered optimal posting time suggestions.

    Args:
        platform: Optional platform filter.

    Returns:
        List of suggestion dicts with platform, days, hours, and tips.
    """
    suggestions = []

    platforms = [platform] if platform else list(PLATFORM_OPTIMAL_TIMES.keys())

    for p in platforms:
        info = PLATFORM_OPTIMAL_TIMES.get(p)
        if info:
            suggestions.append({
                "platform": p,
                "best_days": info["best_days"],
                "best_hours": info["best_hours"],
                "timezone": info["timezone"],
                "tip": info["tip"],
                "color": PLATFORM_COLORS.get(p, "#6B7280"),
            })

    return suggestions


def auto_schedule_posts(
    post_ids: list[int] | None = None,
    start_date: str | None = None,
    days_span: int = 30,
    posts_per_day: int = 1,
) -> list[dict]:
    """AI auto-schedules posts optimally across a date range.

    Spreads posts throughout the time range, placing each post at the optimal
    day/time for its platform. Avoids scheduling multiple posts at the same time.

    Args:
        post_ids: Optional list of specific post IDs to schedule.
                  If None, schedules all unscheduled pending posts.
        start_date: Start date (YYYY-MM-DD). Defaults to tomorrow.
        days_span: Number of days to spread posts across.
        posts_per_day: Max posts per day.

    Returns:
        List of scheduled post dicts.
    """
    if not start_date:
        start_date = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    start_dt = datetime.strptime(start_date, "%Y-%m-%d")

    # Get posts to schedule
    with get_db() as conn:
        if post_ids:
            placeholders = ",".join("?" * len(post_ids))
            rows = conn.execute(
                f"""SELECT sp.*, p.name as product_name
                    FROM social_posts sp
                    LEFT JOIN products p ON sp.product_id = p.id
                    WHERE sp.id IN ({placeholders})
                      AND sp.post_status IN ('pending', 'draft')
                    ORDER BY sp.id ASC""",
                post_ids,
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT sp.*, p.name as product_name
                   FROM social_posts sp
                   LEFT JOIN products p ON sp.product_id = p.id
                   WHERE sp.post_status IN ('pending', 'draft')
                     AND sp.scheduled_at IS NULL
                   ORDER BY sp.created_at ASC""",
            ).fetchall()

    posts = [dict(r) for r in rows]
    if not posts:
        return []

    # Build schedule
    scheduled = []
    day_counts: dict[str, int] = {}
    current_day_offset = 0

    for post in posts:
        platform = post["platform"]
        platform_info = PLATFORM_OPTIMAL_TIMES.get(platform, {})
        best_days = platform_info.get("best_days", ["Monday", "Wednesday", "Friday"])
        best_hours = platform_info.get("best_hours", [10, 14, 18])

        # Find the next available day that matches a best day for this platform
        placed = False
        for attempt in range(days_span * 2):
            candidate_date = start_dt + timedelta(days=current_day_offset + attempt)
            day_name = candidate_date.strftime("%A")
            date_key = candidate_date.strftime("%Y-%m-%d")

            # Check if this day is a good day for the platform
            is_good_day = day_name in best_days

            # Check day capacity
            day_count = day_counts.get(date_key, 0)
            if day_count >= posts_per_day:
                continue

            # Prefer good days, but fall back to any day if needed
            if is_good_day or attempt >= len(best_days) * 2:
                # Pick the best hour, offset by how many posts are already on this day
                hour_index = min(day_count, len(best_hours) - 1)
                hour = best_hours[hour_index]

                scheduled_at = candidate_date.replace(hour=hour, minute=0, second=0)
                scheduled_at_str = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S")

                # Update DB
                with get_db() as conn:
                    conn.execute(
                        "UPDATE social_posts SET scheduled_at = ?, post_status = 'scheduled' WHERE id = ?",
                        (scheduled_at_str, post["id"]),
                    )

                post["scheduled_at"] = scheduled_at_str
                post["post_status"] = "scheduled"
                scheduled.append(post)

                day_counts[date_key] = day_count + 1
                current_day_offset += attempt  # Move forward
                placed = True
                break

        if not placed:
            # Fallback: just schedule on next available day
            candidate_date = start_dt + timedelta(days=current_day_offset)
            scheduled_at = candidate_date.replace(hour=10, minute=0, second=0)
            scheduled_at_str = scheduled_at.strftime("%Y-%m-%dT%H:%M:%S")

            with get_db() as conn:
                conn.execute(
                    "UPDATE social_posts SET scheduled_at = ?, post_status = 'scheduled' WHERE id = ?",
                    (scheduled_at_str, post["id"]),
                )

            post["scheduled_at"] = scheduled_at_str
            post["post_status"] = "scheduled"
            scheduled.append(post)
            current_day_offset += 1

    return scheduled


# ── Batch Scheduling ────────────────────────────────────────────────────

def batch_schedule_products(
    product_ids: list[int],
    start_date: str | None = None,
    days_span: int = 30,
    posts_per_day: int = 1,
) -> dict:
    """Schedule all posts for multiple products across a date range.

    Selects all unscheduled social posts for the given products
    and AI-optimally schedules them.

    Args:
        product_ids: List of product IDs to schedule.
        start_date: Start date (YYYY-MM-DD). Defaults to tomorrow.
        days_span: Number of days to spread across.
        posts_per_day: Max posts per day.

    Returns:
        Dict with scheduled posts and summary.
    """
    # Get all unscheduled posts for these products
    with get_db() as conn:
        placeholders = ",".join("?" * len(product_ids))
        rows = conn.execute(
            f"""SELECT id FROM social_posts
                WHERE product_id IN ({placeholders})
                  AND post_status IN ('pending', 'draft')
                  AND scheduled_at IS NULL
                ORDER BY product_id, created_at""",
            product_ids,
        ).fetchall()

    post_ids = [r["id"] for r in rows]
    if not post_ids:
        return {"scheduled": [], "count": 0, "message": "No unscheduled posts found for selected products"}

    scheduled = auto_schedule_posts(
        post_ids=post_ids,
        start_date=start_date,
        days_span=days_span,
        posts_per_day=posts_per_day,
    )

    return {
        "scheduled": scheduled,
        "count": len(scheduled),
        "message": f"Scheduled {len(scheduled)} posts across {days_span} days",
    }


# ── Background Task: Check & Publish Scheduled Posts ────────────────────

async def check_and_publish_scheduled_posts():
    """Check for posts that are due and trigger auto-posting.

    This should run every minute via the background scheduler.
    Posts with scheduled_at <= now and status = 'scheduled' are published.
    """
    now = datetime.utcnow().isoformat()

    with get_db() as conn:
        due_posts = conn.execute(
            """SELECT sp.*, p.name as product_name
               FROM social_posts sp
               LEFT JOIN products p ON sp.product_id = p.id
               WHERE sp.post_status = 'scheduled'
                 AND sp.scheduled_at IS NOT NULL
                 AND sp.scheduled_at <= ?
               ORDER BY sp.scheduled_at ASC""",
            (now,),
        ).fetchall()

    if not due_posts:
        return

    logger.info("Found %d scheduled posts due for publishing", len(due_posts))

    for row in due_posts:
        post = dict(row)
        post_id = post["id"]
        platform = post["platform"]

        logger.info("Publishing scheduled post #%d to %s", post_id, platform)

        # For auto-post platforms, try auto-posting
        auto_post_platforms = ["Telegram", "Tumblr", "Pinterest"]
        if platform in auto_post_platforms:
            # Find image for the post
            image_path = ""
            image_url = ""
            with get_db() as conn:
                variant = conn.execute(
                    "SELECT image_urls FROM product_variants WHERE product_id = ? AND platform = ? LIMIT 1",
                    (post["product_id"], platform),
                ).fetchone()
                if not variant:
                    variant = conn.execute(
                        "SELECT image_urls FROM product_variants WHERE product_id = ? LIMIT 1",
                        (post["product_id"],),
                    ).fetchone()

            if variant:
                try:
                    urls = json.loads(variant["image_urls"]) if variant["image_urls"] else []
                except (json.JSONDecodeError, TypeError):
                    urls = []
                if urls:
                    first_url = urls[0]
                    if first_url.startswith("http"):
                        image_url = first_url

            try:
                result = await auto_post(post_id=post_id, image_path=image_path, image_url=image_url)
                if result.get("success"):
                    logger.info("Successfully posted #%d to %s", post_id, platform)
                else:
                    logger.warning("Failed to post #%d to %s: %s", post_id, platform, result.get("message"))
            except Exception as e:
                logger.error("Error posting #%d: %s", post_id, str(e))
                with get_db() as conn:
                    conn.execute(
                        "UPDATE social_posts SET post_status = 'error' WHERE id = ?",
                        (post_id,),
                    )
        else:
            # For non-auto-post platforms, mark as "ready" (user needs to copy-paste)
            with get_db() as conn:
                conn.execute(
                    "UPDATE social_posts SET post_status = 'ready', posted_at = ? WHERE id = ?",
                    (now, post_id),
                )
            logger.info("Post #%d for %s marked as ready (manual platform)", post_id, platform)


async def scheduler_loop():
    """Background loop that checks for scheduled posts every 60 seconds."""
    while True:
        try:
            await check_and_publish_scheduled_posts()
        except Exception as e:
            logger.error("Scheduler error: %s", str(e))
        await asyncio.sleep(60)


def get_platform_colors() -> dict:
    """Return platform color mapping for frontend."""
    return PLATFORM_COLORS
