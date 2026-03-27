"""Product Templates & Bundles module for AI Product Factory.

Feature 16: Save reusable product templates with pre-configured settings.
Bundle multiple products into a pack with auto-generated bundle listing.
Seasonal auto-activation support.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


# ── Templates ─────────────────────────────────────────────────────────


def create_template(
    name: str,
    product_type: str = "digital",
    tone: str = "",
    keywords: list[str] | None = None,
    price_min: float = 5.0,
    price_max: float = 15.0,
    platforms: list[str] | None = None,
    languages: list[str] | None = None,
    brief_template: str = "",
    seasonal_tag: str = "",
    auto_activate_month: int | None = None,
) -> dict:
    """Create a reusable product template."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO product_templates
               (name, product_type, tone, keywords, price_min, price_max,
                platforms, languages, brief_template, seasonal_tag, auto_activate_month)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                name,
                product_type,
                tone,
                json.dumps(keywords or []),
                price_min,
                price_max,
                json.dumps(platforms or []),
                json.dumps(languages or ["en"]),
                brief_template,
                seasonal_tag,
                auto_activate_month,
            ),
        )
        row = conn.execute(
            "SELECT * FROM product_templates WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return _enrich_template(dict(row))


def get_all_templates() -> list[dict]:
    """Get all product templates."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM product_templates ORDER BY created_at DESC"
        ).fetchall()
    return [_enrich_template(dict(r)) for r in rows]


def get_template(template_id: int) -> dict | None:
    """Get a single template by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM product_templates WHERE id = ?", (template_id,)
        ).fetchone()
    if not row:
        return None
    return _enrich_template(dict(row))


def update_template(template_id: int, **kwargs) -> dict | None:
    """Update a product template."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM product_templates WHERE id = ?", (template_id,)
        ).fetchone()
        if not existing:
            return None

        fields = []
        values = []
        json_fields = {"keywords", "platforms", "languages"}
        for key, val in kwargs.items():
            if val is not None:
                if key in json_fields:
                    fields.append(f"{key} = ?")
                    values.append(json.dumps(val))
                else:
                    fields.append(f"{key} = ?")
                    values.append(val)

        if not fields:
            return _enrich_template(dict(existing))

        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(template_id)

        conn.execute(
            f"UPDATE product_templates SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute(
            "SELECT * FROM product_templates WHERE id = ?", (template_id,)
        ).fetchone()
    return _enrich_template(dict(row))


def delete_template(template_id: int) -> bool:
    """Delete a product template."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM product_templates WHERE id = ?", (template_id,)
        ).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM product_templates WHERE id = ?", (template_id,))
    return True


def create_product_from_template(template_id: int, product_name: str) -> dict:
    """Create a new product using a template's pre-configured settings."""
    template = get_template(template_id)
    if not template:
        return {"success": False, "message": "Template not found"}

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO products
               (name, product_type, brief, target_platforms, target_languages, status, plan_mode)
               VALUES (?, ?, ?, ?, ?, 'pending', 'A')""",
            (
                product_name,
                template["product_type"],
                template["brief_template"],
                json.dumps(template["platforms"]),
                json.dumps(template["languages"]),
            ),
        )
        product_id = cursor.lastrowid

        # Update template usage count
        conn.execute(
            "UPDATE product_templates SET times_used = times_used + 1 WHERE id = ?",
            (template_id,),
        )

        row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

    product = dict(row)
    product["target_platforms"] = _parse_json(product.get("target_platforms"), [])
    product["target_languages"] = _parse_json(product.get("target_languages"), ["en"])
    product["research_data"] = _parse_json(product.get("research_data"), {})
    product["niche_data"] = _parse_json(product.get("niche_data"), {})
    product["trend_data"] = _parse_json(product.get("trend_data"), {})

    return {
        "success": True,
        "product_id": product_id,
        "product": product,
        "template_id": template_id,
        "message": f"Product created from template '{template['name']}'",
    }


# ── Bundles ───────────────────────────────────────────────────────────


def create_bundle(
    name: str,
    product_ids: list[int],
    discount_percent: float = 25.0,
    seasonal_tag: str = "",
    auto_activate_month: int | None = None,
) -> dict:
    """Create a product bundle from multiple products."""
    if len(product_ids) < 2:
        return {"success": False, "message": "A bundle needs at least 2 products"}

    with get_db() as conn:
        # Validate all products exist and collect prices
        products = []
        for pid in product_ids:
            product = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
            if not product:
                return {"success": False, "message": f"Product {pid} not found"}
            products.append(dict(product))

        # Calculate bundle pricing
        individual_prices = []
        for p in products:
            variants = conn.execute(
                "SELECT price FROM product_variants WHERE product_id = ? LIMIT 1",
                (p["id"],),
            ).fetchall()
            if variants and variants[0]["price"]:
                try:
                    price = float(variants[0]["price"].replace("$", "").strip())
                except (ValueError, AttributeError):
                    price = 9.0
            else:
                price = 9.0
            individual_prices.append(price)

        individual_total = sum(individual_prices)
        bundle_price = round(individual_total * (1 - discount_percent / 100), 2)

        cursor = conn.execute(
            """INSERT INTO product_bundles
               (name, discount_percent, individual_total, bundle_price,
                seasonal_tag, auto_activate_month, status)
               VALUES (?, ?, ?, ?, ?, ?, 'active')""",
            (name, discount_percent, individual_total, bundle_price,
             seasonal_tag, auto_activate_month),
        )
        bundle_id = cursor.lastrowid

        # Insert bundle items
        for i, pid in enumerate(product_ids):
            conn.execute(
                """INSERT INTO bundle_items (bundle_id, product_id, position, individual_price)
                   VALUES (?, ?, ?, ?)""",
                (bundle_id, pid, i, individual_prices[i]),
            )

        row = conn.execute(
            "SELECT * FROM product_bundles WHERE id = ?", (bundle_id,)
        ).fetchone()

    bundle = dict(row)
    bundle["product_ids"] = product_ids
    bundle["product_names"] = [p["name"] for p in products]
    bundle["individual_prices"] = individual_prices

    return {
        "success": True,
        "bundle": bundle,
        "message": f"Bundle '{name}' created with {len(product_ids)} products",
    }


def get_all_bundles() -> list[dict]:
    """Get all product bundles with their items."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM product_bundles ORDER BY created_at DESC"
        ).fetchall()
        bundles = []
        for r in rows:
            b = dict(r)
            items = conn.execute(
                """SELECT bi.*, p.name as product_name
                   FROM bundle_items bi
                   JOIN products p ON bi.product_id = p.id
                   WHERE bi.bundle_id = ?
                   ORDER BY bi.position""",
                (b["id"],),
            ).fetchall()
            b["items"] = [dict(it) for it in items]
            b["product_count"] = len(b["items"])
            bundles.append(b)
    return bundles


def get_bundle(bundle_id: int) -> dict | None:
    """Get a single bundle by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM product_bundles WHERE id = ?", (bundle_id,)
        ).fetchone()
        if not row:
            return None
        b = dict(row)
        items = conn.execute(
            """SELECT bi.*, p.name as product_name
               FROM bundle_items bi
               JOIN products p ON bi.product_id = p.id
               WHERE bi.bundle_id = ?
               ORDER BY bi.position""",
            (b["id"],),
        ).fetchall()
        b["items"] = [dict(it) for it in items]
        b["product_count"] = len(b["items"])
    return b


def delete_bundle(bundle_id: int) -> bool:
    """Delete a bundle and its items."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM product_bundles WHERE id = ?", (bundle_id,)
        ).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM bundle_items WHERE bundle_id = ?", (bundle_id,))
        conn.execute("DELETE FROM product_bundles WHERE id = ?", (bundle_id,))
    return True


async def generate_bundle_listing(bundle_id: int) -> dict:
    """AI generates a title, description, and marketing copy for a bundle."""
    bundle = get_bundle(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found"}

    product_names = [it["product_name"] for it in bundle["items"]]
    prompt = f"""You are a digital product marketing expert.

Create a compelling bundle listing for this product bundle:

Bundle Name: {bundle['name']}
Products included: {', '.join(product_names)}
Individual Total: ${bundle['individual_total']:.2f}
Bundle Price: ${bundle['bundle_price']:.2f}
Savings: {bundle['discount_percent']}%

Return ONLY valid JSON (no markdown, no code fences):
{{
  "bundle_title": "Catchy bundle title that sells",
  "bundle_description": "150-200 word compelling description of the bundle value proposition",
  "tagline": "Short one-liner tagline for marketing",
  "target_audience": "Who this bundle is perfect for",
  "key_benefits": ["benefit 1", "benefit 2", "benefit 3"],
  "marketing_copy": "Short social media promotional text for the bundle"
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {"success": False, "message": f"AI bundle generation failed: {ai_result['message']}"}

    raw_text = ai_result["result"]
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"success": False, "message": "Failed to parse AI bundle response"}

    # Save listing data to the bundle
    with get_db() as conn:
        conn.execute(
            """UPDATE product_bundles
               SET listing_data = ?, updated_at = ?
               WHERE id = ?""",
            (json.dumps(data), datetime.utcnow().isoformat(), bundle_id),
        )

    return {
        "success": True,
        "bundle_id": bundle_id,
        "listing": data,
        "provider": ai_result.get("provider"),
        "message": "Bundle listing generated",
    }


# ── Helpers ───────────────────────────────────────────────────────────


def _enrich_template(t: dict) -> dict:
    """Parse JSON fields in a template dict."""
    t["keywords"] = _parse_json(t.get("keywords"), [])
    t["platforms"] = _parse_json(t.get("platforms"), [])
    t["languages"] = _parse_json(t.get("languages"), ["en"])
    return t


def _parse_json(value, default=None):
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return default
