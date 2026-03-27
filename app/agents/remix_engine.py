"""Product Remix Engine AI Agent.

Takes a successful product and generates 5-10 variations:
- Audience variations (Student, Business, Family, Freelancer)
- Style variations (Dark Mode, Pastel, Minimalist, Colorful)
- Language variations (English, Arabic, French, Spanish)
- Niche variations (Budget, Health, Fitness, Travel)
- Bundle suggestions (combine with other products)

Each variation goes through the FULL pipeline (Research -> Create -> CEO -> Save).
remix_parent_id links variations to the original product.
"""

import json
import logging
import re

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

REMIX_TYPES = {
    "audience": ["Student", "Business Professional", "Family", "Freelancer", "Beginner"],
    "style": ["Dark Mode", "Pastel", "Minimalist", "Colorful", "Retro"],
    "language": ["English", "Arabic", "French", "Spanish", "German"],
    "niche": ["Budget", "Health & Wellness", "Fitness", "Travel", "Productivity"],
    "bundle": [],
}


def _build_remix_prompt(
    product_name: str,
    product_type: str,
    research_data: dict,
    remix_types: list[str],
) -> str:
    """Build the remix generation prompt."""
    type_instructions = []
    for rt in remix_types:
        options = REMIX_TYPES.get(rt, [])
        if rt == "audience":
            type_instructions.append(
                f"- AUDIENCE variations: adapt for these audiences: {', '.join(options)}. "
                "Change the product name, description, features, and pricing to match each audience."
            )
        elif rt == "style":
            type_instructions.append(
                f"- STYLE variations: create visual/design variants: {', '.join(options)}. "
                "Change the aesthetic, color scheme, and design approach."
            )
        elif rt == "language":
            type_instructions.append(
                f"- LANGUAGE variations: culturally adapt (not just translate) for: {', '.join(options)}. "
                "Include language-specific SEO keywords, culturally relevant descriptions, "
                "and localized pricing suggestions."
            )
        elif rt == "niche":
            type_instructions.append(
                f"- NICHE variations: adapt for these niches: {', '.join(options)}. "
                "Change the product angle, features, and target audience for each niche."
            )
        elif rt == "bundle":
            type_instructions.append(
                "- BUNDLE suggestions: suggest 2-3 bundle combinations with complementary products. "
                "For each bundle, suggest a bundle name, included products, and bundle price."
            )

    keywords = ", ".join(research_data.get("keywords", []))
    price_range = research_data.get("price_range", {})
    min_price = price_range.get("min", 9.99)
    max_price = price_range.get("max", 49.99)

    return f"""You are a product remix strategist and digital product expert.

Take this successful product and create compelling variations:

Original Product: {product_name}
Product Type: {product_type}
Target Audience: {research_data.get("target_audience", "General audience")}
Keywords: {keywords}
Original Price Range: ${min_price:.2f} - ${max_price:.2f}

Create variations for these remix types:
{"".join(type_instructions)}

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "variations": [
        {{
            "remix_type": "<audience|style|language|niche|bundle>",
            "variation_name": "<specific variation, e.g. 'Student Edition'>",
            "product_name": "<new product name incorporating the variation>",
            "product_type": "{product_type}",
            "brief": "<brief description of this variation, 2-3 sentences>",
            "target_audience": "<who this variation is for>",
            "suggested_price": "<price as string, e.g. 14.99>",
            "language": "<language code: en, ar, fr, es, de>",
            "key_differences": "<what makes this different from the original>"
        }}
    ]
}}

Generate 5-10 total variations spread across the requested remix types.
Each variation must be meaningfully different from the original and from each other.
For language variations, the product_name and brief should be in the target language."""


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

    logger.warning("Could not parse Remix Engine AI JSON response")
    return {"variations": []}


def _validate_variation(var: dict) -> dict:
    """Ensure all required fields exist with defaults."""
    return {
        "remix_type": var.get("remix_type", "audience"),
        "variation_name": var.get("variation_name", "Variation"),
        "product_name": var.get("product_name", "Untitled Remix"),
        "product_type": var.get("product_type", "digital"),
        "brief": var.get("brief", ""),
        "target_audience": var.get("target_audience", "General"),
        "suggested_price": str(var.get("suggested_price", "19.99")),
        "language": var.get("language", "en"),
        "key_differences": var.get("key_differences", ""),
    }


async def run_remix(
    product_id: int,
    remix_types: list[str] | None = None,
) -> dict:
    """Run the Product Remix Engine.

    Args:
        product_id: Database ID of the original product.
        remix_types: List of remix types to generate (audience, style, language, niche, bundle).
                    Defaults to all types if not specified.

    Returns:
        dict with keys:
            success (bool), variations (list), children_ids (list),
            provider (str), message (str)
    """
    if not remix_types:
        remix_types = ["audience", "style", "language", "niche", "bundle"]

    # Validate remix types
    valid_types = list(REMIX_TYPES.keys())
    remix_types = [t for t in remix_types if t in valid_types]
    if not remix_types:
        return {
            "success": False,
            "variations": [],
            "children_ids": [],
            "provider": None,
            "message": "No valid remix types specified",
        }

    # Load the original product
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return {
                "success": False,
                "variations": [],
                "children_ids": [],
                "provider": None,
                "message": "Product not found",
            }
        product = dict(product)

    product_name = product["name"]
    product_type = product.get("product_type", "digital")

    try:
        research_data = json.loads(product.get("research_data", "{}"))
    except (json.JSONDecodeError, TypeError):
        research_data = {}

    try:
        platforms = json.loads(product.get("target_platforms", "[]"))
    except (json.JSONDecodeError, TypeError):
        platforms = []
    if not platforms:
        platforms = ["Gumroad", "Payhip"]

    # Generate remix variations via AI
    prompt = _build_remix_prompt(product_name, product_type, research_data, remix_types)
    result = await call_text_with_failover("remix", prompt)

    if not result["success"]:
        return {
            "success": False,
            "variations": [],
            "children_ids": [],
            "provider": None,
            "message": f"AI remix generation failed: {result['message']}",
        }

    parsed = _parse_json_response(result["result"])
    raw_variations = parsed.get("variations", [])

    if not isinstance(raw_variations, list):
        raw_variations = []

    variations = [_validate_variation(v) for v in raw_variations]

    # Create child products for each variation
    children_ids = []
    with get_db() as conn:
        for var in variations:
            cursor = conn.execute(
                """INSERT INTO products
                   (name, product_type, brief, target_platforms, target_languages,
                    status, plan_mode, remix_parent_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    var["product_name"],
                    var["product_type"],
                    var["brief"],
                    json.dumps(platforms),
                    json.dumps([var["language"]]),
                    "pending",
                    product.get("plan_mode", "A"),
                    product_id,
                ),
            )
            child_id = cursor.lastrowid
            children_ids.append(child_id)
            var["child_product_id"] = child_id

    return {
        "success": True,
        "variations": variations,
        "children_ids": children_ids,
        "provider": result["provider"],
        "message": f"Generated {len(variations)} remix variations, {len(children_ids)} child products created",
    }


def get_remix_children(parent_id: int) -> list[dict]:
    """Get all remix children of a product."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE remix_parent_id = ? ORDER BY created_at DESC",
            (parent_id,),
        ).fetchall()

    children = []
    for row in rows:
        child = dict(row)
        try:
            child["target_platforms"] = json.loads(child.get("target_platforms", "[]"))
        except (json.JSONDecodeError, TypeError):
            child["target_platforms"] = []
        try:
            child["target_languages"] = json.loads(child.get("target_languages", '["en"]'))
        except (json.JSONDecodeError, TypeError):
            child["target_languages"] = ["en"]
        children.append(child)

    return children
