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
from app.agents.content_repurposer import get_repurposed_content, repurpose_product
from app.agents.faq_bot import (
    add_faq,
    delete_faq,
    get_all_faqs,
    suggest_faq_answer,
    update_faq,
)
from app.agents.niche_finder import (
    create_product_from_niche,
    get_all_niches,
    run_niche_scan,
    update_niche_status,
)
from app.agents.pipeline import run_pipeline
from app.agents.remix_engine import get_remix_children, run_remix
from app.agents.trend_predictor import (
    create_product_from_trend,
    get_active_alerts,
    get_all_trends,
    run_trend_scan,
)
from app.agents.voiceover import generate_voiceover
from app.ab_testing import (
    create_ab_test,
    detect_winner,
    get_ab_patterns,
    get_ab_tests,
    record_ab_sale,
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
from app.email_marketing import generate_email_campaign, get_email_campaign
from app.brevo_integration import (
    get_brevo_status,
    send_campaign_email,
    schedule_campaign_sequence,
)
from app.persona_ai import generate_personas_from_data
from app.templates_bundles import (
    create_template,
    get_all_templates,
    get_template,
    update_template,
    delete_template,
    create_product_from_template,
    create_bundle,
    get_all_bundles,
    get_bundle,
    delete_bundle,
    generate_bundle_listing,
)
from app.agents.competitor_spy import (
    run_competitor_scan,
    get_competitors,
    get_competitor_alerts,
    dismiss_alert,
)
from app.cross_platform_arbitrage import analyze_arbitrage
from app.upsell_engine import get_recommendations, get_frequently_bought_together
from app.affiliate_system import (
    create_affiliate,
    get_all_affiliates,
    update_affiliate,
    delete_affiliate,
    generate_referral_link,
    get_referral_links,
    track_referral_click,
    track_referral_conversion,
    get_referral_stats,
    generate_affiliate_kit,
)
from app.piracy_protection import (
    generate_watermark_id,
    get_protection_status,
    record_scan_result,
    generate_dmca_template,
    get_dmca_requests,
    update_dmca_status,
    embed_invisible_watermark,
    extract_watermark,
    run_piracy_scan,
)
from app.white_label import (
    get_tiers,
    create_tenant,
    get_all_tenants,
    get_tenant,
    update_tenant,
    delete_tenant,
    check_tenant_limits,
    get_tenant_stats,
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
from app.database import get_db, init_db, seed_ai_status, seed_platform_settings, seed_preferences
from app.revenue_goals import create_goal, get_active_goal, get_goals, update_goal_progress
from app.smart_pricing import (
    calculate_bundle_pricing,
    calculate_launch_pricing,
    get_price_suggestions,
)

# Load environment variables
load_dotenv()

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

AUDIO_DIR = Path(__file__).parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True)


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


async def _competitor_cron_loop():
    """Background cron: run competitor scan daily at 7:00 AM UTC."""
    while True:
        now = datetime.utcnow()
        target = now.replace(hour=7, minute=0, second=0, microsecond=0)
        if now >= target:
            target = target.replace(day=target.day + 1)
        wait_seconds = (target - now).total_seconds()
        await asyncio.sleep(wait_seconds)
        try:
            await run_competitor_scan(niches="")
        except Exception as e:
            logging.getLogger(__name__).error("Competitor cron failed: %s", e)


async def _seasonal_template_cron_loop():
    """Background cron: activate seasonal templates at midnight UTC on the 1st."""
    while True:
        now = datetime.utcnow()
        # Run at midnight on the 1st of each month
        if now.day == 1 and now.hour == 0 and now.minute < 5:
            try:
                from app.templates_bundles import activate_seasonal_templates
                activate_seasonal_templates(now.month)
            except Exception as e:
                logging.getLogger(__name__).error("Seasonal template cron failed: %s", e)
        await asyncio.sleep(300)  # Check every 5 minutes


async def _email_drip_cron_loop():
    """Background cron: process scheduled email drip sequences every 5 minutes."""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        try:
            from app.brevo_integration import process_scheduled_emails
            await process_scheduled_emails()
        except Exception as e:
            logging.getLogger(__name__).error("Email drip cron failed: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed data on startup."""
    init_db()
    seed_platform_settings()
    seed_preferences()
    seed_ai_status()
    load_provider_statuses_from_db()
    # Start background tasks
    scheduler_task = asyncio.create_task(scheduler_loop())
    niche_cron_task = asyncio.create_task(_niche_cron_loop())
    trend_cron_task = asyncio.create_task(_trend_cron_loop())
    competitor_cron_task = asyncio.create_task(_competitor_cron_loop())
    seasonal_cron_task = asyncio.create_task(_seasonal_template_cron_loop())
    email_drip_task = asyncio.create_task(_email_drip_cron_loop())
    yield
    for task in (scheduler_task, niche_cron_task, trend_cron_task,
                 competitor_cron_task, seasonal_cron_task, email_drip_task):
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


class RemixRequest(BaseModel):
    remix_types: list[str] | None = None


class ABSaleRequest(BaseModel):
    variant_id: int
    revenue: float


class GoalCreateRequest(BaseModel):
    target_amount: float
    period: str = "monthly"


class LaunchPricingRequest(BaseModel):
    regular_price: float
    discount_percent: float = 40
    duration_hours: int = 48


class BundlePricingRequest(BaseModel):
    prices: list[float]
    discount_percent: float = 25


class FAQCreateRequest(BaseModel):
    question: str
    answer: str
    category: str = "general"


class FAQUpdateRequest(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None


class FAQSuggestRequest(BaseModel):
    question: str


# ── New Feature Pydantic Models ──────────────────────────────────────

class TemplateCreateRequest(BaseModel):
    name: str
    product_type: str = "digital"
    tone: str = ""
    keywords: list[str] | None = None
    price_min: float = 5.0
    price_max: float = 15.0
    platforms: list[str] | None = None
    languages: list[str] | None = None
    brief_template: str = ""
    seasonal_tag: str = ""
    auto_activate_month: int | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    product_type: str | None = None
    tone: str | None = None
    keywords: list[str] | None = None
    price_min: float | None = None
    price_max: float | None = None
    platforms: list[str] | None = None
    languages: list[str] | None = None
    brief_template: str | None = None
    seasonal_tag: str | None = None
    auto_activate_month: int | None = None


class TemplateProductRequest(BaseModel):
    product_name: str


class BundleCreateRequest(BaseModel):
    name: str
    product_ids: list[int]
    discount_percent: float = 25.0
    seasonal_tag: str = ""
    auto_activate_month: int | None = None


class CompetitorScanRequest(BaseModel):
    niches: str = ""


class EmailSendRequest(BaseModel):
    email_type: str
    to_email: str
    to_name: str = ""


class EmailScheduleRequest(BaseModel):
    to_email: str
    to_name: str = ""


class AffiliateCreateRequest(BaseModel):
    name: str
    email: str = ""
    commission_rate: float = 20.0
    notes: str = ""


class AffiliateUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    commission_rate: float | None = None
    notes: str | None = None
    status: str | None = None


class ReferralLinkRequest(BaseModel):
    affiliate_id: int
    product_id: int


class ReferralConversionRequest(BaseModel):
    ref_code: str
    revenue: float


class DMCARequest(BaseModel):
    infringer_url: str = ""
    infringer_name: str = ""


class DMCAStatusRequest(BaseModel):
    status: str


class ScanResultRequest(BaseModel):
    source: str = ""
    found_url: str = ""
    match_confidence: float = 0.0
    notes: str = ""


class TenantCreateRequest(BaseModel):
    name: str
    owner_email: str
    brand_name: str = ""
    brand_color: str = "#7c3aed"
    tier: str = "free"
    custom_domain: str = ""


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    owner_email: str | None = None
    brand_name: str | None = None
    brand_color: str | None = None
    tier: str | None = None
    custom_domain: str | None = None
    status: str | None = None


class PlatformSettingCreate(BaseModel):
    name: str
    type: str = "selling"
    tone: str = ""
    plan_mode: str = "A"
    max_title_length: int = 100
    max_description_length: int = 5000
    custom_instructions: str = ""
    enabled: bool = True


class PlatformSettingUpdate(BaseModel):
    tone: str | None = None
    plan_mode: str | None = None
    enabled: bool | None = None
    max_title_length: int | None = None
    max_description_length: int | None = None
    custom_instructions: str | None = None
    type: str | None = None


class PersonaCreate(BaseModel):
    name: str
    age_range: str = ""
    description: str = ""
    preferences: dict | None = None
    platforms: list[str] | None = None


class PersonaUpdate(BaseModel):
    name: str | None = None
    age_range: str | None = None
    description: str | None = None
    preferences: dict | None = None
    platforms: list[str] | None = None


class PreferenceUpdate(BaseModel):
    key: str
    value: str | int | float | bool | list | dict


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


@app.post("/api/settings/platforms", status_code=201)
async def create_platform_setting(body: PlatformSettingCreate):
    """Add a new platform."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM platform_settings WHERE platform = ?", (body.name,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail=f"Platform '{body.name}' already exists")

        cursor = conn.execute(
            """INSERT INTO platform_settings
               (platform, type, tone, plan_mode, enabled, max_title_length, max_description_length, custom_instructions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                body.name,
                body.type,
                body.tone,
                body.plan_mode,
                1 if body.enabled else 0,
                body.max_title_length,
                body.max_description_length,
                body.custom_instructions,
            ),
        )
        row = conn.execute(
            "SELECT * FROM platform_settings WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

    return row_to_dict(row)


@app.patch("/api/settings/platforms/{platform_id}")
async def update_platform_setting(platform_id: int, body: PlatformSettingUpdate):
    """Update a platform setting."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM platform_settings WHERE id = ?", (platform_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Platform setting not found")

        allowed_fields = {"tone", "plan_mode", "enabled", "max_title_length",
                          "max_description_length", "custom_instructions", "type"}
        fields = []
        values = []
        update_data = body.model_dump(exclude_none=True)
        for key, val in update_data.items():
            if key in allowed_fields:
                if key == "enabled":
                    fields.append(f"{key} = ?")
                    values.append(1 if val else 0)
                else:
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


@app.delete("/api/settings/platforms/{platform_id}")
async def delete_platform_setting(platform_id: int):
    """Remove a platform."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM platform_settings WHERE id = ?", (platform_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Platform setting not found")
        conn.execute("DELETE FROM platform_settings WHERE id = ?", (platform_id,))
    return {"message": "Platform deleted", "id": platform_id}


# ══════════════════════════════════════════════════════════════════════
# CUSTOMER PERSONAS
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/settings/personas")
async def list_personas():
    """Get all customer personas."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM customer_personas ORDER BY created_at DESC"
        ).fetchall()
    personas = []
    for r in rows:
        p = row_to_dict(r)
        p["preferences"] = parse_json_field(p.get("preferences"), {})
        p["platforms"] = parse_json_field(p.get("platforms"), [])
        personas.append(p)
    return {"personas": personas, "count": len(personas)}


@app.post("/api/settings/personas", status_code=201)
async def create_persona(body: PersonaCreate):
    """Create a new customer persona."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO customer_personas (name, age_range, description, preferences, platforms)
               VALUES (?, ?, ?, ?, ?)""",
            (
                body.name,
                body.age_range,
                body.description,
                json.dumps(body.preferences or {}),
                json.dumps(body.platforms or []),
            ),
        )
        row = conn.execute(
            "SELECT * FROM customer_personas WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    result = row_to_dict(row)
    result["preferences"] = parse_json_field(result.get("preferences"), {})
    result["platforms"] = parse_json_field(result.get("platforms"), [])
    return result


@app.patch("/api/settings/personas/{persona_id}")
async def update_persona(persona_id: int, body: PersonaUpdate):
    """Update a customer persona."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM customer_personas WHERE id = ?", (persona_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Persona not found")

        fields = []
        values = []
        if body.name is not None:
            fields.append("name = ?")
            values.append(body.name)
        if body.age_range is not None:
            fields.append("age_range = ?")
            values.append(body.age_range)
        if body.description is not None:
            fields.append("description = ?")
            values.append(body.description)
        if body.preferences is not None:
            fields.append("preferences = ?")
            values.append(json.dumps(body.preferences))
        if body.platforms is not None:
            fields.append("platforms = ?")
            values.append(json.dumps(body.platforms))

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(persona_id)
        conn.execute(
            f"UPDATE customer_personas SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM customer_personas WHERE id = ?", (persona_id,)
        ).fetchone()

    result = row_to_dict(row)
    result["preferences"] = parse_json_field(result.get("preferences"), {})
    result["platforms"] = parse_json_field(result.get("platforms"), [])
    return result


@app.delete("/api/settings/personas/{persona_id}")
async def delete_persona(persona_id: int):
    """Delete a customer persona."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM customer_personas WHERE id = ?", (persona_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Persona not found")
        conn.execute("DELETE FROM customer_personas WHERE id = ?", (persona_id,))
    return {"message": "Persona deleted", "id": persona_id}


# ══════════════════════════════════════════════════════════════════════
# SETTINGS PREFERENCES
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/settings/preferences")
async def get_preferences():
    """Get all settings preferences."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM settings_preferences ORDER BY key"
        ).fetchall()
    prefs = {}
    for r in rows:
        d = row_to_dict(r)
        prefs[d["key"]] = parse_json_field(d["value"], d["value"])
    return {"preferences": prefs}


@app.patch("/api/settings/preferences")
async def update_preference(body: PreferenceUpdate):
    """Update a single preference."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM settings_preferences WHERE key = ?", (body.key,)
        ).fetchone()
        value_str = json.dumps(body.value)
        if existing:
            conn.execute(
                "UPDATE settings_preferences SET value = ?, updated_at = ? WHERE key = ?",
                (value_str, datetime.utcnow().isoformat(), body.key),
            )
        else:
            conn.execute(
                "INSERT INTO settings_preferences (key, value) VALUES (?, ?)",
                (body.key, value_str),
            )
        row = conn.execute(
            "SELECT * FROM settings_preferences WHERE key = ?", (body.key,)
        ).fetchone()
    d = row_to_dict(row)
    return {"key": d["key"], "value": parse_json_field(d["value"], d["value"])}


# ══════════════════════════════════════════════════════════════════════
# API KEY STATUS
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/settings/api-keys")
async def get_api_key_status():
    """Show which API keys are configured (not actual keys)."""
    import os
    keys = {
        "GEMINI_API_KEY": {"name": "Google AI Studio (Gemini)", "priority": "MUST HAVE"},
        "GROQ_API_KEY": {"name": "Groq", "priority": "MUST HAVE"},
        "CLOUDFLARE_API_TOKEN": {"name": "Cloudflare Workers AI", "priority": "MUST HAVE"},
        "CLOUDFLARE_ACCOUNT_ID": {"name": "Cloudflare Account ID", "priority": "MUST HAVE"},
        "CEREBRAS_API_KEY": {"name": "Cerebras", "priority": "Nice to have"},
        "MISTRAL_API_KEY": {"name": "Mistral", "priority": "Nice to have"},
        "TUMBLR_API_KEY": {"name": "Tumblr API", "priority": "For auto-post"},
        "TUMBLR_API_SECRET": {"name": "Tumblr API Secret", "priority": "For auto-post"},
        "PINTEREST_ACCESS_TOKEN": {"name": "Pinterest API", "priority": "For auto-post"},
        "TELEGRAM_BOT_TOKEN": {"name": "Telegram Bot", "priority": "For auto-post"},
        "BREVO_API_KEY": {"name": "Brevo (Email)", "priority": "For email marketing"},
        "ELEVENLABS_API_KEY": {"name": "ElevenLabs (Voice)", "priority": "Nice to have"},
    }
    result = []
    for env_var, info in keys.items():
        val = os.environ.get(env_var, "")
        configured = bool(val and len(val) > 0)
        result.append({
            "env_var": env_var,
            "name": info["name"],
            "priority": info["priority"],
            "configured": configured,
            "masked_value": f"{val[:4]}...{val[-4:]}" if configured and len(val) > 8 else ("****" if configured else ""),
        })
    configured_count = sum(1 for r in result if r["configured"])
    return {"api_keys": result, "configured_count": configured_count, "total_count": len(result)}


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
# REMIX ENGINE (Agent 4)
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/products/{product_id}/remix")
async def remix_product(product_id: int, body: RemixRequest):
    """Remix a product into multiple variations."""
    result = await run_remix(product_id, remix_types=body.remix_types)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/products/{product_id}/children")
async def get_product_children(product_id: int):
    """Get all remix children of a product."""
    children = get_remix_children(product_id)
    return {"children": children, "count": len(children)}


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


# ══════════════════════════════════════════════════════════════════════
# A/B TESTING
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/variants/{variant_id}/ab-test")
async def create_variant_ab_test(variant_id: int):
    """Create an A/B/C test for a variant.

    AI generates 3 different versions of the title/description.
    """
    result = await create_ab_test(variant_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/ab-tests")
async def list_ab_tests(
    status: str | None = Query(None, description="Filter by status: running, completed"),
):
    """List all A/B tests with variant data and sales metrics."""
    tests = get_ab_tests(status=status)
    return {"tests": tests, "count": len(tests)}


@app.post("/api/ab-tests/{test_id}/sale")
async def log_ab_sale(test_id: int, body: ABSaleRequest):
    """Record a sale for a specific variant in an A/B test."""
    result = record_ab_sale(test_id, body.variant_id, body.revenue)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.post("/api/ab-tests/{test_id}/detect-winner")
async def ab_detect_winner(test_id: int):
    """Manually trigger winner detection for an A/B test."""
    result = detect_winner(test_id)
    return result


@app.get("/api/ab-tests/patterns")
async def ab_patterns():
    """Get learned patterns from completed A/B tests."""
    patterns = get_ab_patterns()
    return {"patterns": patterns, "count": len(patterns)}


# ══════════════════════════════════════════════════════════════════════
# SMART PRICING
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/products/{product_id}/pricing")
async def product_pricing(product_id: int):
    """Get AI-powered price suggestions for a product."""
    result = await get_price_suggestions(product_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.post("/api/pricing/launch")
async def launch_pricing(body: LaunchPricingRequest):
    """Calculate launch pricing (discount for limited time)."""
    result = calculate_launch_pricing(
        regular_price=body.regular_price,
        discount_percent=body.discount_percent,
        duration_hours=body.duration_hours,
    )
    return result


@app.post("/api/pricing/bundle")
async def bundle_pricing(body: BundlePricingRequest):
    """Calculate bundle pricing for multiple products."""
    if len(body.prices) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 prices for a bundle")
    result = calculate_bundle_pricing(
        individual_prices=body.prices,
        bundle_discount_percent=body.discount_percent,
    )
    return result


# ══════════════════════════════════════════════════════════════════════
# EMAIL MARKETING
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/products/{product_id}/email")
async def generate_email(product_id: int):
    """Generate an email marketing campaign for a product.

    Creates 3 subject line variations, promo email body,
    day 3 follow-up, and day 7 follow-up.
    """
    result = await generate_email_campaign(product_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/products/{product_id}/email")
async def get_email(product_id: int):
    """Get the email campaign for a product."""
    campaign = get_email_campaign(product_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="No email campaign found for this product")
    return campaign


# ══════════════════════════════════════════════════════════════════════
# REVENUE GOALS
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/goals")
async def create_revenue_goal(body: GoalCreateRequest):
    """Set a revenue target goal."""
    result = create_goal(body.target_amount, body.period)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/goals")
async def list_goals():
    """Get all revenue goals with current progress."""
    goals = get_goals()
    active = get_active_goal()
    return {"goals": goals, "active_goal": active, "count": len(goals)}


@app.post("/api/goals/refresh")
async def refresh_goals():
    """Recalculate progress for all active goals."""
    result = update_goal_progress()
    return result


# ══════════════════════════════════════════════════════════════════════
# CONTENT REPURPOSING ENGINE
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/products/{product_id}/repurpose")
async def repurpose_product_content(product_id: int):
    """Repurpose a product listing into 7 content formats.

    Generates: blog post, YouTube script, Twitter thread,
    Instagram carousel, newsletter, Quora answer, Pinterest pin.
    """
    with get_db() as conn:
        product = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    result = await repurpose_product(product_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.get("/api/products/{product_id}/repurpose")
async def get_product_repurposed_content(product_id: int):
    """Get all repurposed content for a product."""
    with get_db() as conn:
        product = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    content = get_repurposed_content(product_id)
    return {"content": content, "count": len(content)}


# ══════════════════════════════════════════════════════════════════════
# AI VOICE-OVER
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/products/{product_id}/voiceover")
async def product_voiceover(product_id: int):
    """Generate a 30-second voice-over script and audio for a product.

    AI writes the script, then TTS converts to audio (ElevenLabs or browser TTS fallback).
    """
    with get_db() as conn:
        product = conn.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    result = await generate_voiceover(product_id)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve a generated audio file."""
    file_path = AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/mpeg")


# ══════════════════════════════════════════════════════════════════════
# AUTO-REPLY FAQ BOT
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/faq")
async def create_faq(body: FAQCreateRequest):
    """Add a new FAQ entry (question + answer)."""
    result = add_faq(body.question, body.answer, body.category)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@app.get("/api/faq")
async def list_faqs(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in question/answer text"),
):
    """List all FAQ entries with optional filters."""
    faqs = get_all_faqs(category=category, search=search)
    return {"faqs": faqs, "count": len(faqs)}


@app.patch("/api/faq/{faq_id}")
async def update_faq_entry(faq_id: int, body: FAQUpdateRequest):
    """Update an existing FAQ entry."""
    result = update_faq(faq_id, question=body.question, answer=body.answer, category=body.category)
    if result is None:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    return result


@app.delete("/api/faq/{faq_id}")
async def delete_faq_entry(faq_id: int):
    """Delete an FAQ entry."""
    success = delete_faq(faq_id)
    if not success:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    return {"message": "FAQ entry deleted", "id": faq_id}


@app.post("/api/faq/suggest")
async def suggest_faq(body: FAQSuggestRequest):
    """AI drafts an answer for a new question based on existing FAQ knowledge."""
    result = await suggest_faq_answer(body.question)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result


# ══════════════════════════════════════════════════════════════════════
# PRODUCT TEMPLATES (Feature 16)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/templates")
async def list_templates():
    """Get all product templates."""
    templates = get_all_templates()
    return {"templates": templates, "count": len(templates)}


@app.post("/api/templates", status_code=201)
async def create_new_template(body: TemplateCreateRequest):
    """Create a reusable product template."""
    result = create_template(
        name=body.name,
        product_type=body.product_type,
        tone=body.tone,
        keywords=body.keywords,
        price_min=body.price_min,
        price_max=body.price_max,
        platforms=body.platforms,
        languages=body.languages,
        brief_template=body.brief_template,
        seasonal_tag=body.seasonal_tag,
        auto_activate_month=body.auto_activate_month,
    )
    return result


@app.get("/api/templates/{template_id}")
async def get_single_template(template_id: int):
    """Get a single template."""
    result = get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@app.patch("/api/templates/{template_id}")
async def update_existing_template(template_id: int, body: TemplateUpdateRequest):
    """Update a product template."""
    result = update_template(template_id, **body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@app.delete("/api/templates/{template_id}")
async def delete_existing_template(template_id: int):
    """Delete a product template."""
    success = delete_template(template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted", "id": template_id}


@app.post("/api/templates/{template_id}/create-product")
async def create_product_from_tmpl(template_id: int, body: TemplateProductRequest):
    """Create a new product from a template."""
    result = create_product_from_template(template_id, body.product_name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "Failed"))
    return result


# ══════════════════════════════════════════════════════════════════════
# PRODUCT BUNDLES (Feature 16)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/bundles")
async def list_bundles():
    """Get all product bundles."""
    bundles = get_all_bundles()
    return {"bundles": bundles, "count": len(bundles)}


@app.post("/api/bundles", status_code=201)
async def create_new_bundle(body: BundleCreateRequest):
    """Create a product bundle."""
    result = create_bundle(
        name=body.name,
        product_ids=body.product_ids,
        discount_percent=body.discount_percent,
        seasonal_tag=body.seasonal_tag,
        auto_activate_month=body.auto_activate_month,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/bundles/{bundle_id}")
async def get_single_bundle(bundle_id: int):
    """Get a single bundle with items."""
    result = get_bundle(bundle_id)
    if not result:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return result


@app.delete("/api/bundles/{bundle_id}")
async def delete_existing_bundle(bundle_id: int):
    """Delete a bundle."""
    success = delete_bundle(bundle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bundle not found")
    return {"message": "Bundle deleted", "id": bundle_id}


@app.post("/api/bundles/{bundle_id}/generate-listing")
async def generate_bundle_listing_endpoint(bundle_id: int):
    """AI generates a title, description, and marketing copy for a bundle."""
    result = await generate_bundle_listing(bundle_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


# ══════════════════════════════════════════════════════════════════════
# COMPETITOR SPY AGENT (Feature 8)
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/competitors/scan")
async def scan_competitors(body: CompetitorScanRequest):
    """Run AI competitor analysis scan."""
    result = await run_competitor_scan(niches=body.niches)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Scan failed"))
    return result


@app.get("/api/competitors")
async def list_competitors(
    platform: str | None = Query(None, description="Filter by platform"),
):
    """Get all tracked competitors."""
    competitors = get_competitors(platform=platform)
    return {"competitors": competitors, "count": len(competitors)}


@app.get("/api/competitors/alerts")
async def list_competitor_alerts(
    alert_type: str | None = Query(None, description="Filter: price_change, market_gap"),
):
    """Get active competitor alerts."""
    alerts = get_competitor_alerts(alert_type=alert_type)
    return {"alerts": alerts, "count": len(alerts)}


@app.post("/api/competitors/alerts/{alert_id}/dismiss")
async def dismiss_competitor_alert(alert_id: int):
    """Dismiss a competitor alert."""
    success = dismiss_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"message": "Alert dismissed", "id": alert_id}


# ══════════════════════════════════════════════════════════════════════
# CROSS-PLATFORM ARBITRAGE (Feature 13)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/arbitrage")
async def get_arbitrage_opportunities():
    """Analyze cross-platform pricing and performance differences."""
    result = await analyze_arbitrage()
    return result


# ══════════════════════════════════════════════════════════════════════
# UPSELL & CROSS-SELL ENGINE (Feature 21)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/products/{product_id}/recommendations")
async def product_recommendations(
    product_id: int,
    limit: int = Query(5, description="Max recommendations"),
):
    """Get AI-powered product recommendations for upsell/cross-sell."""
    result = await get_recommendations(product_id, limit=limit)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/products/{product_id}/frequently-bought")
async def product_frequently_bought(product_id: int):
    """Get products frequently bought together."""
    related = get_frequently_bought_together(product_id)
    return {"related_products": related, "count": len(related)}


# ══════════════════════════════════════════════════════════════════════
# EMAIL MARKETING - BREVO INTEGRATION (Feature 20 Enhancement)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/email/status")
async def email_integration_status():
    """Get Brevo email integration status."""
    return get_brevo_status()


@app.post("/api/email/campaigns/{campaign_id}/send")
async def send_campaign(campaign_id: int, body: EmailSendRequest):
    """Send a specific email from a campaign via Brevo."""
    result = await send_campaign_email(
        campaign_id=campaign_id,
        email_type=body.email_type,
        to_email=body.to_email,
        to_name=body.to_name,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.post("/api/email/campaigns/{campaign_id}/schedule")
async def schedule_campaign(campaign_id: int, body: EmailScheduleRequest):
    """Schedule the full email sequence (promo, Day 3, Day 7)."""
    result = await schedule_campaign_sequence(
        campaign_id=campaign_id,
        to_email=body.to_email,
        to_name=body.to_name,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


# ══════════════════════════════════════════════════════════════════════
# AI CUSTOMER PERSONAS (Feature 9 Enhancement)
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/personas/generate")
async def generate_ai_personas(
    count: int = Query(3, description="Number of personas to generate"),
):
    """AI generates customer personas from sales data analysis."""
    result = await generate_personas_from_data(count=count)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Failed"))
    return result


# ══════════════════════════════════════════════════════════════════════
# AFFILIATE & REFERRAL SYSTEM (Feature 23)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/affiliates")
async def list_affiliates(
    status: str | None = Query(None, description="Filter by status: active, inactive"),
):
    """Get all affiliates with stats."""
    affiliates = get_all_affiliates(status=status)
    return {"affiliates": affiliates, "count": len(affiliates)}


@app.post("/api/affiliates", status_code=201)
async def create_new_affiliate(body: AffiliateCreateRequest):
    """Register a new affiliate partner."""
    result = create_affiliate(
        name=body.name,
        email=body.email,
        commission_rate=body.commission_rate,
        notes=body.notes,
    )
    return result


@app.patch("/api/affiliates/{affiliate_id}")
async def update_existing_affiliate(affiliate_id: int, body: AffiliateUpdateRequest):
    """Update an affiliate."""
    result = update_affiliate(affiliate_id, **body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    return result


@app.delete("/api/affiliates/{affiliate_id}")
async def delete_existing_affiliate(affiliate_id: int):
    """Delete an affiliate."""
    success = delete_affiliate(affiliate_id)
    if not success:
        raise HTTPException(status_code=404, detail="Affiliate not found")
    return {"message": "Affiliate deleted", "id": affiliate_id}


@app.post("/api/affiliates/referral-link")
async def create_referral_link(body: ReferralLinkRequest):
    """Generate a referral link for an affiliate + product."""
    result = generate_referral_link(body.affiliate_id, body.product_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/affiliates/referral-links")
async def list_referral_links(
    affiliate_id: int | None = Query(None),
    product_id: int | None = Query(None),
):
    """Get referral links with optional filters."""
    links = get_referral_links(affiliate_id=affiliate_id, product_id=product_id)
    return {"links": links, "count": len(links)}


@app.post("/api/affiliates/track-click")
async def track_click(ref_code: str = Query(..., description="Referral code")):
    """Track a click on a referral link."""
    result = track_referral_click(ref_code)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.post("/api/affiliates/track-conversion")
async def track_conversion(body: ReferralConversionRequest):
    """Track a conversion (sale) from a referral."""
    result = track_referral_conversion(body.ref_code, body.revenue)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/affiliates/stats")
async def affiliate_stats(
    affiliate_id: int | None = Query(None),
):
    """Get referral statistics."""
    stats = get_referral_stats(affiliate_id=affiliate_id)
    return stats


@app.post("/api/affiliates/marketing-kit/{product_id}")
async def generate_marketing_kit(product_id: int):
    """AI generates a complete affiliate marketing kit for a product."""
    result = await generate_affiliate_kit(product_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/affiliates/track-conversion-pixel")
async def track_conversion_pixel(
    ref_code: str = Query(..., description="Referral code"),
    amount: float = Query(0.0, description="Sale amount"),
):
    """Webhook/pixel endpoint for automatic affiliate conversion tracking.

    Embeddable as an invisible pixel or webhook callback from payment platforms.
    Example: <img src="/api/affiliates/track-conversion-pixel?ref_code=ABC&amount=9.99" width="1" height="1" />
    """
    if not ref_code:
        raise HTTPException(status_code=400, detail="ref_code is required")
    result = track_referral_conversion(ref_code, amount)
    # Return a 1x1 transparent pixel for browser-based tracking
    return {"success": result.get("success", False), "tracked": True, "ref_code": ref_code}


# ══════════════════════════════════════════════════════════════════════
# PIRACY PROTECTION (Feature 24)
# ══════════════════════════════════════════════════════════════════════


@app.post("/api/products/{product_id}/watermark")
async def create_watermark(product_id: int):
    """Generate a unique watermark ID for a product."""
    result = generate_watermark_id(product_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/piracy/status")
async def piracy_status(
    product_id: int | None = Query(None, description="Filter by product ID"),
):
    """Get piracy protection status for products."""
    result = get_protection_status(product_id=product_id)
    return {"protections": result if isinstance(result, list) else [result], "count": 1 if isinstance(result, dict) else len(result)}


@app.post("/api/piracy/{product_id}/scan")
async def record_piracy_scan(product_id: int, body: ScanResultRequest):
    """Record a piracy scan result."""
    result = record_scan_result(product_id, body.model_dump())
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.post("/api/piracy/{product_id}/dmca")
async def create_dmca(product_id: int, body: DMCARequest):
    """AI generates a DMCA takedown template."""
    result = await generate_dmca_template(
        product_id=product_id,
        infringer_url=body.infringer_url,
        infringer_name=body.infringer_name,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/piracy/dmca")
async def list_dmca_requests(
    product_id: int | None = Query(None),
):
    """Get all DMCA requests."""
    requests = get_dmca_requests(product_id=product_id)
    return {"requests": requests, "count": len(requests)}


@app.patch("/api/piracy/dmca/{dmca_id}")
async def update_dmca(dmca_id: int, body: DMCAStatusRequest):
    """Update DMCA request status."""
    result = update_dmca_status(dmca_id, body.status)
    if not result:
        raise HTTPException(status_code=404, detail="DMCA request not found or invalid status")
    return result


@app.post("/api/products/{product_id}/watermark/embed")
async def embed_watermark(product_id: int, image_path: str = Query(..., description="Path to the image file")):
    """Embed an invisible watermark into a product image using LSB steganography."""
    # First ensure watermark ID exists
    wm_result = generate_watermark_id(product_id)
    if not wm_result.get("success"):
        raise HTTPException(status_code=400, detail=wm_result.get("message", "Failed"))
    result = embed_invisible_watermark(image_path, wm_result["watermark_id"])
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.post("/api/products/{product_id}/watermark/extract")
async def extract_product_watermark(product_id: int, image_path: str = Query(..., description="Path to the image file")):
    """Extract an invisible watermark from a watermarked image."""
    result = extract_watermark(image_path)
    return result


@app.post("/api/piracy/{product_id}/auto-scan")
async def auto_piracy_scan(product_id: int):
    """Run an automated piracy scan using reverse image search (placeholder)."""
    result = await run_piracy_scan(product_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


# ══════════════════════════════════════════════════════════════════════
# WHITE-LABEL RESELL (Feature 26)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/white-label/tiers")
async def list_tiers():
    """Get available subscription tiers."""
    tiers = get_tiers()
    return {"tiers": tiers, "count": len(tiers)}


@app.get("/api/white-label/tenants")
async def list_tenants(
    status: str | None = Query(None, description="Filter by status: active, suspended"),
):
    """Get all white-label tenants."""
    tenants = get_all_tenants(status=status)
    return {"tenants": tenants, "count": len(tenants)}


@app.post("/api/white-label/tenants", status_code=201)
async def create_new_tenant(body: TenantCreateRequest):
    """Create a new white-label tenant."""
    result = create_tenant(
        name=body.name,
        owner_email=body.owner_email,
        brand_name=body.brand_name,
        brand_color=body.brand_color,
        tier=body.tier,
        custom_domain=body.custom_domain,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/white-label/tenants/{tenant_id}")
async def get_single_tenant(tenant_id: int):
    """Get a single tenant."""
    result = get_tenant(tenant_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result


@app.patch("/api/white-label/tenants/{tenant_id}")
async def update_existing_tenant(tenant_id: int, body: TenantUpdateRequest):
    """Update a tenant."""
    result = update_tenant(tenant_id, **body.model_dump(exclude_none=True))
    if not result:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return result


@app.delete("/api/white-label/tenants/{tenant_id}")
async def delete_existing_tenant(tenant_id: int):
    """Delete a tenant."""
    success = delete_tenant(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"message": "Tenant deleted", "id": tenant_id}


@app.get("/api/white-label/tenants/{tenant_id}/limits")
async def tenant_limits(tenant_id: int):
    """Check a tenant's usage against their tier limits."""
    result = check_tenant_limits(tenant_id)
    if not result.get("tenant_id") and not result.get("within_limits"):
        raise HTTPException(status_code=404, detail=result.get("message", "Tenant not found"))
    return result


@app.get("/api/white-label/stats")
async def white_label_stats():
    """Get aggregate statistics across all tenants."""
    return get_tenant_stats()


@app.get("/api/white-label/tenants/{tenant_id}/branding")
async def get_tenant_branding(tenant_id: int):
    """Get tenant branding info for rendering branded dashboards."""
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "tenant_id": tenant_id,
        "brand_name": tenant.get("brand_name", ""),
        "brand_color": tenant.get("brand_color", "#7c3aed"),
        "custom_domain": tenant.get("custom_domain", ""),
        "tier": tenant.get("tier", "free"),
        "logo_url": tenant.get("logo_url", ""),
        "status": tenant.get("status", "active"),
    }


@app.get("/api/white-label/tenants/{tenant_id}/products")
async def get_tenant_products(tenant_id: int):
    """Get products scoped to a specific tenant (multi-tenant data isolation)."""
    tenant = get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE tenant_id = ? ORDER BY created_at DESC",
            (tenant_id,),
        ).fetchall()
    products = []
    for r in rows:
        p = row_to_dict(r)
        p["target_platforms"] = parse_json_field(p.get("target_platforms"))
        p["target_languages"] = parse_json_field(p.get("target_languages"), ["en"])
        products.append(p)
    return {"products": products, "count": len(products), "tenant_id": tenant_id}


# ══════════════════════════════════════════════════════════════════════
# STRIPE INTEGRATION STUB (Feature 26 Enhancement)
# ══════════════════════════════════════════════════════════════════════


@app.get("/api/billing/status")
async def billing_status():
    """Get current billing/Stripe integration status."""
    from app.stripe_integration import get_stripe_status
    return get_stripe_status()


@app.post("/api/billing/subscribe")
async def create_subscription(
    tenant_id: int = Query(..., description="Tenant ID"),
    tier: str = Query("pro", description="Subscription tier: free, pro, agency"),
):
    """Create or update a subscription for a tenant (Stripe stub)."""
    from app.stripe_integration import create_subscription as stripe_subscribe
    result = stripe_subscribe(tenant_id, tier)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.post("/api/billing/cancel")
async def cancel_subscription(
    tenant_id: int = Query(..., description="Tenant ID"),
):
    """Cancel a subscription for a tenant (Stripe stub)."""
    from app.stripe_integration import cancel_subscription as stripe_cancel
    result = stripe_cancel(tenant_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Failed"))
    return result


@app.get("/api/billing/invoices")
async def list_invoices(
    tenant_id: int = Query(..., description="Tenant ID"),
):
    """Get billing invoices for a tenant (Stripe stub)."""
    from app.stripe_integration import get_invoices
    return get_invoices(tenant_id)
