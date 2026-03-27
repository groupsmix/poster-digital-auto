"""Piracy Protection module for AI Product Factory.

Feature 24: Invisible watermarks on images, unique identifiers in product files,
auto-generated DMCA takedown templates.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)

TASK_CHAIN_KEY = "create"


def generate_watermark_id(product_id: int) -> dict:
    """Generate a unique watermark identifier for a product.

    Creates an invisible watermark ID that can be embedded in product files
    and images for tracking purposes.
    """
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        # Check if watermark already exists
        existing = conn.execute(
            "SELECT * FROM piracy_protection WHERE product_id = ?", (product_id,)
        ).fetchone()

        watermark_id = str(uuid.uuid4())
        fingerprint = hashlib.sha256(
            f"{product_id}-{product['name']}-{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]

        if existing:
            conn.execute(
                """UPDATE piracy_protection
                   SET watermark_id = ?, fingerprint = ?, updated_at = ?
                   WHERE product_id = ?""",
                (watermark_id, fingerprint, datetime.utcnow().isoformat(), product_id),
            )
        else:
            conn.execute(
                """INSERT INTO piracy_protection
                   (product_id, watermark_id, fingerprint, status)
                   VALUES (?, ?, ?, 'active')""",
                (product_id, watermark_id, fingerprint),
            )

        row = conn.execute(
            "SELECT * FROM piracy_protection WHERE product_id = ?", (product_id,)
        ).fetchone()

    return {
        "success": True,
        "product_id": product_id,
        "watermark_id": watermark_id,
        "fingerprint": fingerprint,
        "protection": dict(row),
        "embed_code": f"<!-- WM:{fingerprint} -->",
        "message": "Watermark ID generated. Embed in your product files.",
    }


def get_protection_status(product_id: int | None = None) -> list[dict] | dict:
    """Get piracy protection status for products."""
    with get_db() as conn:
        if product_id:
            row = conn.execute(
                """SELECT pp.*, p.name as product_name
                   FROM piracy_protection pp
                   JOIN products p ON pp.product_id = p.id
                   WHERE pp.product_id = ?""",
                (product_id,),
            ).fetchone()
            if not row:
                return {"product_id": product_id, "protected": False, "status": "unprotected"}
            d = dict(row)
            d["scan_results"] = _parse_json(d.get("scan_results"), [])
            return d
        else:
            rows = conn.execute(
                """SELECT pp.*, p.name as product_name
                   FROM piracy_protection pp
                   JOIN products p ON pp.product_id = p.id
                   ORDER BY pp.created_at DESC"""
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["scan_results"] = _parse_json(d.get("scan_results"), [])
                result.append(d)
            return result


def record_scan_result(product_id: int, scan_data: dict) -> dict:
    """Record a piracy scan result for a product."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM piracy_protection WHERE product_id = ?", (product_id,)
        ).fetchone()
        if not existing:
            return {"success": False, "message": "Product not protected. Generate a watermark first."}

        current_results = _parse_json(existing["scan_results"], [])
        scan_data["scanned_at"] = datetime.utcnow().isoformat()
        current_results.append(scan_data)

        # Keep last 50 scan results
        current_results = current_results[-50:]

        conn.execute(
            """UPDATE piracy_protection
               SET scan_results = ?, last_scan = ?, scan_count = scan_count + 1,
                   updated_at = ?
               WHERE product_id = ?""",
            (
                json.dumps(current_results),
                datetime.utcnow().isoformat(),
                datetime.utcnow().isoformat(),
                product_id,
            ),
        )

    return {"success": True, "message": "Scan result recorded"}


async def generate_dmca_template(product_id: int, infringer_url: str = "", infringer_name: str = "") -> dict:
    """AI generates a DMCA takedown request template."""
    with get_db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_dict = dict(product)

        protection = conn.execute(
            "SELECT * FROM piracy_protection WHERE product_id = ?", (product_id,)
        ).fetchone()

    watermark_id = dict(protection)["watermark_id"] if protection else "N/A"
    fingerprint = dict(protection)["fingerprint"] if protection else "N/A"

    prompt = f"""You are a legal expert specializing in digital content protection and DMCA takedown requests.

Generate a professional DMCA takedown request template for this situation:

Product Name: {product_dict['name']}
Product Type: {product_dict.get('product_type', 'digital')}
Watermark ID: {watermark_id}
Fingerprint: {fingerprint}
Infringer URL: {infringer_url or '[INFRINGER URL]'}
Infringer Name: {infringer_name or '[INFRINGER NAME/PLATFORM]'}

Return ONLY valid JSON (no markdown, no code fences):
{{
  "dmca_letter": "Complete DMCA takedown letter text with placeholders for personal info marked as [YOUR NAME], [YOUR EMAIL], etc.",
  "email_subject": "Subject line for the DMCA email",
  "platform_specific": {{
    "gumroad": "Specific instructions for filing DMCA on Gumroad",
    "etsy": "Specific instructions for filing DMCA on Etsy",
    "general": "General DMCA filing process"
  }},
  "evidence_checklist": [
    "Item 1 to prepare as evidence",
    "Item 2 to prepare as evidence"
  ],
  "follow_up_template": "Follow-up email if no response in 10 days"
}}"""

    ai_result = await call_text_with_failover(TASK_CHAIN_KEY, prompt)
    if not ai_result["success"]:
        return {"success": False, "message": f"DMCA generation failed: {ai_result['message']}"}

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
        return {"success": False, "message": "Failed to parse DMCA template response"}

    # Store DMCA request
    with get_db() as conn:
        conn.execute(
            """INSERT INTO dmca_requests
               (product_id, infringer_url, infringer_name, dmca_data, status)
               VALUES (?, ?, ?, ?, 'draft')""",
            (product_id, infringer_url, infringer_name, json.dumps(data)),
        )

    return {
        "success": True,
        "product_id": product_id,
        "product_name": product_dict["name"],
        "dmca": data,
        "provider": ai_result.get("provider"),
        "generated_at": datetime.utcnow().isoformat(),
        "message": "DMCA takedown template generated",
    }


def get_dmca_requests(product_id: int | None = None) -> list[dict]:
    """Get all DMCA requests."""
    with get_db() as conn:
        if product_id:
            rows = conn.execute(
                """SELECT dr.*, p.name as product_name
                   FROM dmca_requests dr
                   JOIN products p ON dr.product_id = p.id
                   WHERE dr.product_id = ?
                   ORDER BY dr.created_at DESC""",
                (product_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT dr.*, p.name as product_name
                   FROM dmca_requests dr
                   JOIN products p ON dr.product_id = p.id
                   ORDER BY dr.created_at DESC"""
            ).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["dmca_data"] = _parse_json(d.get("dmca_data"), {})
        result.append(d)
    return result


def update_dmca_status(dmca_id: int, status: str) -> dict | None:
    """Update DMCA request status (draft, sent, resolved, rejected)."""
    valid_statuses = {"draft", "sent", "resolved", "rejected"}
    if status not in valid_statuses:
        return None

    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM dmca_requests WHERE id = ?", (dmca_id,)
        ).fetchone()
        if not existing:
            return None

        conn.execute(
            "UPDATE dmca_requests SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), dmca_id),
        )
        row = conn.execute(
            "SELECT * FROM dmca_requests WHERE id = ?", (dmca_id,)
        ).fetchone()

    d = dict(row)
    d["dmca_data"] = _parse_json(d.get("dmca_data"), {})
    return d


def _parse_json(value, default=None):
    if default is None:
        default = []
    if not value:
        return default
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return default
