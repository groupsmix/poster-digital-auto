"""AI Product Factory - Backend API.

FastAPI backend with SQLite database, full CRUD for products,
AI failover system, and platform settings management.
"""

import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.agents.caption_generator import generate_captions
from app.agents.pipeline import run_pipeline
from app.ai_failover import (
    get_all_provider_statuses,
    load_provider_statuses_from_db,
    reset_all_daily_limits,
)
from app.database import get_db, init_db, seed_ai_status, seed_platform_settings

# Load environment variables
load_dotenv()

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)


# ── Lifespan ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed data on startup."""
    init_db()
    seed_platform_settings()
    seed_ai_status()
    load_provider_statuses_from_db()
    yield


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
