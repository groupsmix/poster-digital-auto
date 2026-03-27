"""AI Product Factory - Backend API.

FastAPI backend with SQLite database, full CRUD for products,
AI failover system, and platform settings management.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.agents.auto_poster import auto_post, get_auto_post_config
from app.agents.caption_generator import generate_captions
from app.agents.niche_finder import (
    create_product_from_niche,
    get_all_niches,
    run_niche_scan,
    update_niche_status,
)
from app.agents.pipeline import run_pipeline
from app.agents.trend_predictor import (
    create_product_from_trend,
    get_active_alerts,
    get_all_trends,
    run_trend_scan,
)
from app.ai_failover import (
    get_all_provider_statuses,
    load_provider_statuses_from_db,
    reset_all_daily_limits,
)
from app.analytics import (
    generate_insights,
    get_ai_provider_usage,
    get_ceo_score_trend,
    get_overview,
    get_platform_performance,
    get_product_analytics,
    get_revenue_over_time,
    get_top_products,
    import_sales_csv,
    record_event,
)
from app.calendar_scheduler import (
    auto_schedule_posts,
    batch_schedule_products,
    get_ai_schedule_suggestions,
    get_calendar_posts,
    get_platform_colors,
    reschedule_post,
    schedule_post,
    scheduler_loop,
    unschedule_post,
)
from app.database import get_db, init_db, seed_ai_status, seed_platform_settings

# Load environment variables
load_dotenv()

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)


# ── Lifespan ───────────────────────────────────────────────────────────

async def _niche_cron_loop():
    """Background cron: run niche scan daily at 6:00 AM UTC."""
    while True:
        now = datetime.utcnow()
        # Calculate seconds until next 6:00 AM UTC
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now >= target:
            # Already past 6 AM today, schedule for tomorrow
            target = target.replace(day=target.day + 1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            await run_niche_scan()
        except Exception as e:
            logging.getLogger(__name__).error("Niche cron failed: %s", e)


async def _trend_cron_loop():
    """Background cron: run trend scan daily at 6:30 AM UTC."""
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=6, minute=30, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=target.day + 1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            await run_trend_scan()
        except Exception as e:
            logging.getLogger(__name__).error("Trend cron failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed data on startup."""
    init_db()
    seed_platform_settings()
    seed_ai_status()
    load_provider_statuses_from_db()
    # Start background tasks
    scheduler_task = asyncio.create_task(scheduler_loop())
    niche_cron_task = asyncio.create_task(_niche_cron_loop())
    trend_cron_task = asyncio.create_task(_trend_cron_loop())
    yield
    for task in (scheduler_task, niche_cron_task, trend_cron_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="AI Product Factory", version="1.0.0", lifespan=lifespan)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# ── Pydantic Models ───────────────────────────────────────────────────

class ProductCreate(BaseModel):
    name: str
    product_type: str = "digital"
    brief: str = ""
    target_platforms: list[str] = []
    target_languages: list[str] = ["en"]
    status: str = "pending"
    plan_mode: str = "A"


class ProductUpdate(BaseModel):
    name: str | None = None
    product_type: str | None = None
    brief: str | None = None
    target_platforms: list[str] | None = None
    target_languages: list[str] | None = None
    status: str | None = None
    plan_mode: str | None = None
    research_data: dict | None = None
    niche_data: dict | None = None
    trend_data: dict | None = None
    remix_parent_id: int | None = None


class VariantUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    price: str | None = None


class SocialPostUpdate(BaseModel):
    caption: str | None = None
    post_status: str | None = None


class AnalyticsEventRequest(BaseModel):
    product_id: int | None = None
    variant_id: int | None = None
    platform: str
    event_type: str
    revenue: float = 0.0
    data: dict | None = None


class ManualSaleRequest(BaseModel):
    product_id: int
    platform: str
    revenue: float
    date: str | None = None


class SchedulePostRequest(BaseModel):
    post_id: int
    scheduled_at: str


class RescheduleRequest(BaseModel):
    scheduled_at: str


class AutoScheduleRequest(BaseModel):
    post_ids: list[int] | None = None
    start_date: str | None = None
    days_span: int = 30
    posts_per_day: int = 1


class BatchScheduleRequest(BaseModel):
    product_ids: list[int]
    start_date: str | None = None
    days_span: int = 30
    posts_per_day: int = 1


# ── Helper Functions ──────────────────────────────────────────────────

def row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to a dict."""
    if row is None:
        return {}
    return dict(row)


def parse_json_field(value: str, default=None):
    """Safely parse a JSON string field."""
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def enrich_product(product: dict) -> dict:
    """Parse JSON fields in a product dict."""
    product["target_platforms"] = parse_json_field(product.get("target_platforms"), [])
    product["target_languages"] = parse_json_field(product.get("target_languages"), ["en"])
    product["research_data"] = parse_json_field(product.get("research_data"), {})
    product["niche_data"] = parse_json_field(product.get("niche_data"), {})
    product["trend_data"] = parse_json_field(product.get("trend_data"), {})
    return product


# ── Health Check ──────────────────────────────────────────────────────

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "ai-product-factory", "timestamp": datetime.utcnow().isoformat()}


# ══════════════════════════════════════════════════════════════════════
# PRODUCTS CRUD
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/products")
async def list_products(status: str | None = Query(None, description="Filter by status")):
    """List all products, optionally filtered by status."""
    with get_db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM products WHERE status = ? ORDER BY created_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM products ORDER BY created_at DESC").fetchall()

    products = [enrich_product(row_to_dict(r)) for r in rows]
    return {"products": products, "count": len(products)}


@app.get("/api/products/{product_id}")
async def get_product(product_id: int):
    """Get product detail with variants, posts, and logs."""
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        variants = conn.execute(
            "SELECT * FROM product_variants WHERE product_id = ? ORDER BY created_at DESC",
            (product_id,),
        ).fetchall()

        posts = conn.execute(
            "SELECT * FROM social_posts WHERE product_id = ? ORDER BY created_at DESC",
            (product_id,),
        ).fetchall()

        logs = conn.execute(
            "SELECT * FROM pipeline_logs WHERE product_id = ? ORDER BY created_at DESC",
            (product_id,),
        ).fetchall()

    product_dict = enrich_product(row_to_dict(product))

    variant_list = []
    for v in variants:
        vd = row_to_dict(v)
        vd["tags"] = parse_json_field(vd.get("tags"), [])
        vd["image_urls"] = parse_json_field(vd.get("image_urls"), [])
        variant_list.append(vd)

    product_dict["variants"] = variant_list
    product_dict["social_posts"] = [row_to_dict(p) for p in posts]
    product_dict["pipeline_logs"] = [row_to_dict(lg) for lg in logs]

    return product_dict


@app.post("/api/products", status_code=201)
async def create_product(product: ProductCreate):
    """Create a new product."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO products (name, product_type, brief, target_platforms, target_languages, status, plan_mode)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                product.name,
                product.product_type,
                product.brief,
                json.dumps(product.target_platforms),
                json.dumps(product.target_languages),
                product.status,
                product.plan_mode,
            ),
        )
        product_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    return enrich_product(row_to_dict(row))


@app.patch("/api/products/{product_id}")
async def update_product(product_id: int, update: ProductUpdate):
    """Update a product."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Product not found")

        fields = []
        values = []

        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.product_type is not None:
            fields.append("product_type = ?")
            values.append(update.product_type)
        if update.brief is not None:
            fields.append("brief = ?")
            values.append(update.brief)
        if update.target_platforms is not None:
            fields.append("target_platforms = ?")
            values.append(json.dumps(update.target_platforms))
        if update.target_languages is not None:
            fields.append("target_languages = ?")
            values.append(json.dumps(update.target_languages))
        if update.status is not None:
            fields.append("status = ?")
            values.append(update.status)
        if update.plan_mode is not None:
            fields.append("plan_mode = ?")
            values.append(update.plan_mode)
        if update.research_data is not None:
            fields.append("research_data = ?")
            values.append(json.dumps(update.research_data))
        if update.niche_data is not None:
            fields.append("niche_data = ?")
            values.append(json.dumps(update.niche_data))
        if update.trend_data is not None:
            fields.append("trend_data = ?")
            values.append(json.dumps(update.trend_data))
        if update.remix_parent_id is not None:
            fields.append("remix_parent_id = ?")
            values.append(update.remix_parent_id)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(product_id)

        conn.execute(
            f"UPDATE products SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    return enrich_product(row_to_dict(row))


@app.delete("/api/products/{product_id}")
async def delete_product(product_id: int):
    """Delete a product and cascade delete variants, posts, and logs."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Product not found")

        # Cascade delete related records
        conn.execute("DELETE FROM product_variants WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM social_posts WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM pipeline_logs WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM repurposed_content WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM analytics WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM email_campaigns WHERE product_id = ?", (product_id,))
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

    return {"message": "Product deleted", "id": product_id}


# ══════════════════════════════════════════════════════════════════════
# VARIANTS
# ══════════════════════════════════════════════════════════════════════

@app.patch("/api/variants/{variant_id}")
async def update_variant(variant_id: int, update: VariantUpdate):
    """Update a product variant (title, description, tags, price)."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM product_variants WHERE id = ?", (variant_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Variant not found")

        fields = []
        values = []

        if update.title is not None:
            fields.append("title = ?")
            values.append(update.title)
        if update.description is not None:
            fields.append("description = ?")
            values.append(update.description)
        if update.tags is not None:
            fields.append("tags = ?")
            values.append(json.dumps(update.tags))
        if update.price is not None:
            fields.append("price = ?")
            values.append(update.price)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(variant_id)
        conn.execute(
            f"UPDATE product_variants SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM product_variants WHERE id = ?", (variant_id,)
        ).fetchone()

    result = row_to_dict(row)
    result["tags"] = parse_json_field(result.get("tags"), [])
    result["image_urls"] = parse_json_field(result.get("image_urls"), [])
    return result


# ══════════════════════════════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/stats")
async def get_stats():
    """Dashboard overview statistics."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        draft = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'draft'").fetchone()[0]
        research = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'researching'").fetchone()[0]
        creating = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'creating'").fetchone()[0]
        review = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'review'").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'approved'").fetchone()[0]
        published = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'published'").fetchone()[0]
        rejected = conn.execute("SELECT COUNT(*) FROM products WHERE status = 'rejected'").fetchone()[0]

        total_variants = conn.execute("SELECT COUNT(*) FROM product_variants").fetchone()[0]
        total_posts = conn.execute("SELECT COUNT(*) FROM social_posts").fetchone()[0]
        total_niche_ideas = conn.execute("SELECT COUNT(*) FROM niche_ideas").fetchone()[0]
        total_ab_tests = conn.execute("SELECT COUNT(*) FROM ab_tests").fetchone()[0]

    return {
        "products": {
            "total": total,
            "by_status": {
                "draft": draft,
                "researching": research,
                "creating": creating,
                "review": review,
                "approved": approved,
                "published": published,
                "rejected": rejected,
            },
        },
        "variants": {"total": total_variants},
        "social_posts": {"total": total_posts},
        "niche_ideas": {"total": total_niche_ideas},
        "ab_tests": {"total": total_ab_tests},
    }


# ══════════════════════════════════════════════════════════════════════
# AI STATUS & FAILOVER
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/ai-status")
async def get_ai_status():
    """Get status of all AI providers."""
    providers = get_all_provider_statuses()
    return {"providers": providers, "count": len(providers)}


@app.post("/api/ai-status/reset")
async def reset_ai_status():
    """Reset daily limits for all AI providers."""
    reset_all_daily_limits()
    return {"message": "All daily limits reset", "timestamp": datetime.utcnow().isoformat()}


# ══════════════════════════════════════════════════════════════════════
# IMAGE SERVING
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/images/{filename}")
async def serve_image(filename: str):
    """Serve a generated image file."""
    file_path = IMAGES_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)


# ══════════════════════════════════════════════════════════════════════
# PIPELINE & CAPTIONS
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/products/{product_id}/generate")
async def generate_product(product_id: int):
    """Run the full AI product generation pipeline.

    Steps: Research -> Create -> Images -> CEO Review -> (Revision) -> Save
    """
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    result = await run_pipeline(product_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.post("/api/products/{product_id}/captions")
async def generate_product_captions(product_id: int):
    """Generate social media captions for a product."""
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        product_dict = row_to_dict(product)

    product_name = product_dict["name"]
    product_description = product_dict.get("brief", "")

    # Try to get a description from variants if brief is empty
    if not product_description:
        with get_db() as conn:
            variant = conn.execute(
                "SELECT description FROM product_variants WHERE product_id = ? LIMIT 1",
                (product_id,),
            ).fetchone()
            if variant:
                product_description = variant["description"]

    result = await generate_captions(
        product_id=product_id,
        product_name=product_name,
        product_description=product_description,
        product_url="",
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# ══════════════════════════════════════════════════════════════════════
# SOCIAL POSTS MANAGEMENT
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/social-posts")
async def list_social_posts(
    product_id: int | None = Query(None, description="Filter by product ID"),
    platform: str | None = Query(None, description="Filter by platform"),
    post_status: str | None = Query(None, description="Filter by status"),
):
    """List all social posts with optional filters."""
    with get_db() as conn:
        query = "SELECT * FROM social_posts WHERE 1=1"
        params: list = []

        if product_id is not None:
            query += " AND product_id = ?"
            params.append(product_id)
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if post_status:
            query += " AND post_status = ?"
            params.append(post_status)

        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()

    posts = []
    for r in rows:
        post = row_to_dict(r)
        # Parse metadata from voice_url field
        metadata = parse_json_field(post.get("voice_url"), {})
        if isinstance(metadata, dict):
            post["hashtags"] = metadata.get("hashtags", [])
            post["subreddits"] = metadata.get("subreddits", [])
        else:
            post["hashtags"] = []
            post["subreddits"] = []
        posts.append(post)

    return {"posts": posts, "count": len(posts)}


@app.get("/api/social-posts/{post_id}")
async def get_social_post(post_id: int):
    """Get a single social post by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Social post not found")

    post = row_to_dict(row)
    metadata = parse_json_field(post.get("voice_url"), {})
    if isinstance(metadata, dict):
        post["hashtags"] = metadata.get("hashtags", [])
        post["subreddits"] = metadata.get("subreddits", [])
    else:
        post["hashtags"] = []
        post["subreddits"] = []
    return post


@app.patch("/api/social-posts/{post_id}")
async def update_social_post(post_id: int, update: SocialPostUpdate):
    """Edit a social post caption or status."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Social post not found")

        fields = []
        values: list = []

        if update.caption is not None:
            fields.append("caption = ?")
            values.append(update.caption)
        if update.post_status is not None:
            fields.append("post_status = ?")
            values.append(update.post_status)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(post_id)
        conn.execute(
            f"UPDATE social_posts SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()

    post = row_to_dict(row)
    metadata = parse_json_field(post.get("voice_url"), {})
    if isinstance(metadata, dict):
        post["hashtags"] = metadata.get("hashtags", [])
        post["subreddits"] = metadata.get("subreddits", [])
    else:
        post["hashtags"] = []
        post["subreddits"] = []
    return post


@app.post("/api/social-posts/{post_id}/post")
async def trigger_auto_post(post_id: int):
    """Trigger auto-posting for a social post.

    Supported platforms: Telegram, Tumblr, Pinterest.
    Requires API keys configured in .env.
    """
    with get_db() as conn:
        row = conn.execute("SELECT * FROM social_posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Social post not found")

        post = row_to_dict(row)

        # Try to find an image for the post
        image_path = ""
        image_url = ""
        variant = conn.execute(
            "SELECT image_urls FROM product_variants WHERE product_id = ? AND platform = ? LIMIT 1",
            (post["product_id"], post["platform"]),
        ).fetchone()
        if not variant:
            # Try any variant for this product
            variant = conn.execute(
                "SELECT image_urls FROM product_variants WHERE product_id = ? LIMIT 1",
                (post["product_id"],),
            ).fetchone()

        if variant:
            urls = parse_json_field(variant["image_urls"], [])
            if urls:
                first_url = urls[0]
                if first_url.startswith("/api/images/"):
                    filename = first_url.replace("/api/images/", "")
                    candidate = IMAGES_DIR / filename
                    if candidate.exists():
                        image_path = str(candidate)
                elif first_url.startswith("http"):
                    image_url = first_url

    result = await auto_post(post_id=post_id, image_path=image_path, image_url=image_url)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Auto-posting failed"))

    return result


@app.get("/api/auto-post/config")
async def get_auto_post_status():
    """Get configuration status of auto-posting platforms."""
    return get_auto_post_config()


# ══════════════════════════════════════════════════════════════════════
# PLATFORM SETTINGS
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/settings/platforms")
async def list_platform_settings():
    """Get all platform settings."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM platform_settings ORDER BY id"
        ).fetchall()
    return {"platforms": [row_to_dict(r) for r in rows]}


@app.patch("/api/settings/platforms/{platform_id}")
async def update_platform_setting(platform_id: int, body: dict):
    """Update a platform setting."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM platform_settings WHERE id = ?", (platform_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Platform setting not found")

        allowed_fields = {"tone", "plan_mode", "enabled", "max_title_length",
                          "max_description_length", "custom_instructions"}
        fields = []
        values = []
        for key, val in body.items():
            if key in allowed_fields:
                fields.append(f"{key} = ?")
                values.append(val)

        if not fields:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        values.append(platform_id)
        conn.execute(
            f"UPDATE platform_settings SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM platform_settings WHERE id = ?", (platform_id,)
        ).fetchone()

    return row_to_dict(row)


# ══════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/analytics/event")
async def create_analytics_event(body: AnalyticsEventRequest):
    """Record an analytics event (view, click, sale, refund)."""
    valid_types = {"view", "click", "sale", "refund"}
    if body.event_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"event_type must be one of: {', '.join(valid_types)}")
    result = record_event(
        product_id=body.product_id,
        variant_id=body.variant_id,
        platform=body.platform,
        event_type=body.event_type,
        revenue=body.revenue,
        data=body.data,
    )
    return result


@app.get("/api/analytics/overview")
async def analytics_overview():
    """Dashboard summary: total revenue, products, best platform, avg CEO score."""
    return get_overview()


@app.get("/api/analytics/revenue")
async def analytics_revenue(
    period: str = Query("30d", description="Period: 7d, 30d, 90d, all"),
):
    """Revenue over time for charting."""
    return get_revenue_over_time(period)


@app.get("/api/analytics/platforms")
async def analytics_platforms():
    """Per-platform performance comparison."""
    return get_platform_performance()


@app.get("/api/analytics/products/{product_id}")
async def analytics_product(product_id: int):
    """Single product deep-dive analytics."""
    result = get_product_analytics(product_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/analytics/top-products")
async def analytics_top_products(
    limit: int = Query(10, description="Max products to return"),
):
    """Top products sorted by revenue."""
    return {"products": get_top_products(limit)}


@app.get("/api/analytics/ceo-trend")
async def analytics_ceo_trend():
    """CEO approval rate trend over time."""
    return {"trend": get_ceo_score_trend()}


@app.get("/api/analytics/ai-usage")
async def analytics_ai_usage():
    """AI provider usage breakdown."""
    return {"providers": get_ai_provider_usage()}


@app.get("/api/analytics/insights")
async def analytics_insights():
    """AI-generated insights about product performance."""
    return {"insights": generate_insights()}


@app.post("/api/analytics/manual-sale")
async def log_manual_sale(body: ManualSaleRequest):
    """Manually log a sale (for Gumroad/Payhip without real-time APIs)."""
    with get_db() as conn:
        product = conn.execute("SELECT id FROM products WHERE id = ?", (body.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
    result = record_event(
        product_id=body.product_id,
        variant_id=None,
        platform=body.platform,
        event_type="sale",
        revenue=body.revenue,
        data={"source": "manual", "date": body.date or datetime.utcnow().isoformat()},
    )
    return result


@app.post("/api/analytics/import-csv")
async def import_csv(file: UploadFile = File(...)):
    """Import sales data from CSV file."""
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    content = await file.read()
    csv_text = content.decode("utf-8")
    result = import_sales_csv(csv_text)
    return result


# ══════════════════════════════════════════════════════════════════════
# CONTENT CALENDAR & SCHEDULER
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/calendar")
async def get_calendar(
    start: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end: str = Query(..., description="End date (YYYY-MM-DD)"),
):
    """Get scheduled posts within a date range."""
    posts = get_calendar_posts(start, end)
    return {"posts": posts, "count": len(posts)}


@app.post("/api/calendar/schedule")
async def schedule_calendar_post(body: SchedulePostRequest):
    """Schedule a social post for a specific date/time."""
    result = schedule_post(body.post_id, body.scheduled_at)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.patch("/api/calendar/{post_id}")
async def reschedule_calendar_post(post_id: int, body: RescheduleRequest):
    """Reschedule a post to a new date/time."""
    result = reschedule_post(post_id, body.scheduled_at)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.delete("/api/calendar/{post_id}")
async def unschedule_calendar_post(post_id: int):
    """Remove a post from the schedule."""
    result = unschedule_post(post_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/api/calendar/suggestions")
async def get_schedule_suggestions(
    platform: str | None = Query(None, description="Filter by platform"),
):
    """Get AI-powered optimal posting time suggestions."""
    suggestions = get_ai_schedule_suggestions(platform)
    return {"suggestions": suggestions, "count": len(suggestions)}


@app.post("/api/calendar/auto-schedule")
async def auto_schedule(body: AutoScheduleRequest):
    """AI auto-schedules posts optimally across a date range."""
    scheduled = auto_schedule_posts(
        post_ids=body.post_ids,
        start_date=body.start_date,
        days_span=body.days_span,
        posts_per_day=body.posts_per_day,
    )
    return {
        "scheduled": scheduled,
        "count": len(scheduled),
        "message": f"Auto-scheduled {len(scheduled)} posts",
    }


@app.post("/api/calendar/batch-schedule")
async def batch_schedule(body: BatchScheduleRequest):
    """Schedule posts for multiple products across days."""
    result = batch_schedule_products(
        product_ids=body.product_ids,
        start_date=body.start_date,
        days_span=body.days_span,
        posts_per_day=body.posts_per_day,
    )
    return result


@app.get("/api/calendar/platform-colors")
async def platform_colors():
    """Get platform color mapping for calendar UI."""
    return get_platform_colors()


# ══════════════════════════════════════════════════════════════════════
# NICHE FINDER (Agent 0)
# ══════════════════════════════════════════════════════════════════════


class NicheUpdateRequest(BaseModel):
    status: str


@app.post("/api/niches/scan")
async def scan_niches():
    """Run the Niche Finder AI agent to discover product ideas."""
    result = await run_niche_scan()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.get("/api/niches")
async def list_niches(
    status: str | None = Query(None, description="Filter by status: new, approved, rejected, archived, created"),
    sort_by: str = Query("demand_score", description="Sort by: demand_score, created_at, monthly_searches, competition"),
):
    """List all discovered niche ideas."""
    ideas = get_all_niches(status=status, sort_by=sort_by)
    return {"ideas": ideas, "count": len(ideas)}


@app.post("/api/niches/{niche_id}/create")
async def create_from_niche(niche_id: int):
    """Create a product from a niche idea and trigger the pipeline."""
    result = await create_product_from_niche(niche_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@app.patch("/api/niches/{niche_id}")
async def update_niche(niche_id: int, body: NicheUpdateRequest):
    """Update a niche idea status (approve/reject/archive)."""
    result = update_niche_status(niche_id, body.status)
    if result is None:
        raise HTTPException(status_code=404, detail="Niche idea not found or invalid status")
    return result


# ══════════════════════════════════════════════════════════════════════
# TREND PREDICTOR (Agent 1)
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/trends/scan")
async def scan_trends():
    """Run the Trend Predictor AI agent to find upcoming trends."""
    result = await run_trend_scan()
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.get("/api/trends")
async def list_trends(
    status: str | None = Query(None, description="Filter by status: active, expired, created"),
):
    """List all trend predictions."""
    predictions = get_all_trends(status=status)
    return {"predictions": predictions, "count": len(predictions)}


@app.get("/api/trends/alerts")
async def trend_alerts():
    """Get high-confidence active trend alerts for dashboard banner."""
    alerts = get_active_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/api/trends/{trend_id}/create")
async def create_from_trend(trend_id: int):
    """Create a product from a trend prediction."""
    result = await create_product_from_trend(trend_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result
