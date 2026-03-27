"""Auto-Reply FAQ Bot for AI Product Factory.

Manages a growing FAQ database. AI can suggest answers for new questions
based on existing Q&A patterns and product knowledge.
"""

import json
import logging
from datetime import datetime

from app.ai_failover import call_text_with_failover, TASK_CHAINS
from app.database import get_db

logger = logging.getLogger(__name__)

# Register faq task chain
TASK_CHAINS["faq"] = ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen", "mistral_large"]


def add_faq(question: str, answer: str, category: str = "general") -> dict:
    """Add a new FAQ entry to the database.

    Args:
        question: The question text.
        answer: The answer text.
        category: Category for organizing FAQs.

    Returns:
        dict with success status and the created FAQ entry.
    """
    with get_db() as conn:
        # Check for duplicate question
        existing = conn.execute(
            "SELECT id FROM faq_entries WHERE LOWER(question) = LOWER(?)", (question,)
        ).fetchone()
        if existing:
            return {"success": False, "message": "A similar FAQ already exists", "id": existing["id"]}

        cursor = conn.execute(
            """INSERT INTO faq_entries (question, answer, category, times_used)
               VALUES (?, ?, ?, 0)""",
            (question, answer, category),
        )
        faq_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM faq_entries WHERE id = ?", (faq_id,)).fetchone()

    return {
        "success": True,
        "faq": dict(row),
        "message": "FAQ entry added successfully",
    }


def get_all_faqs(category: str | None = None, search: str | None = None) -> list[dict]:
    """Get all FAQ entries, optionally filtered.

    Args:
        category: Filter by category.
        search: Search in question and answer text.

    Returns:
        List of FAQ entry dicts.
    """
    with get_db() as conn:
        query = "SELECT * FROM faq_entries WHERE 1=1"
        params: list = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if search:
            query += " AND (LOWER(question) LIKE ? OR LOWER(answer) LIKE ?)"
            search_term = f"%{search.lower()}%"
            params.append(search_term)
            params.append(search_term)

        query += " ORDER BY times_used DESC, created_at DESC"
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def update_faq(faq_id: int, question: str | None = None, answer: str | None = None,
               category: str | None = None) -> dict | None:
    """Update an existing FAQ entry.

    Args:
        faq_id: The FAQ entry ID.
        question: New question text (optional).
        answer: New answer text (optional).
        category: New category (optional).

    Returns:
        Updated FAQ entry dict or None if not found.
    """
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM faq_entries WHERE id = ?", (faq_id,)).fetchone()
        if not existing:
            return None

        fields = []
        values: list = []

        if question is not None:
            fields.append("question = ?")
            values.append(question)
        if answer is not None:
            fields.append("answer = ?")
            values.append(answer)
        if category is not None:
            fields.append("category = ?")
            values.append(category)

        if not fields:
            return dict(existing)

        fields.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(faq_id)

        conn.execute(
            f"UPDATE faq_entries SET {', '.join(fields)} WHERE id = ?", values
        )
        row = conn.execute("SELECT * FROM faq_entries WHERE id = ?", (faq_id,)).fetchone()

    return dict(row)


def delete_faq(faq_id: int) -> bool:
    """Delete an FAQ entry.

    Args:
        faq_id: The FAQ entry ID.

    Returns:
        True if deleted, False if not found.
    """
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM faq_entries WHERE id = ?", (faq_id,)).fetchone()
        if not existing:
            return False
        conn.execute("DELETE FROM faq_entries WHERE id = ?", (faq_id,))
    return True


def increment_faq_usage(faq_id: int) -> None:
    """Increment the usage counter for an FAQ entry."""
    with get_db() as conn:
        conn.execute(
            "UPDATE faq_entries SET times_used = times_used + 1 WHERE id = ?", (faq_id,)
        )


async def suggest_faq_answer(question: str) -> dict:
    """Use AI to suggest an answer for a new FAQ question.

    The AI considers existing FAQs and product knowledge to draft a helpful answer.

    Args:
        question: The new question to generate an answer for.

    Returns:
        dict with success status, suggested answer, and metadata.
    """
    # Fetch existing FAQs for context
    existing_faqs = get_all_faqs()
    faq_context = ""
    if existing_faqs:
        faq_samples = existing_faqs[:10]  # Use top 10 most-used FAQs as context
        faq_context = "\n".join(
            f"Q: {faq['question']}\nA: {faq['answer']}"
            for faq in faq_samples
        )

    # Fetch recent products for context
    with get_db() as conn:
        products = conn.execute(
            "SELECT name, brief, product_type FROM products ORDER BY created_at DESC LIMIT 5"
        ).fetchall()

    product_context = ""
    if products:
        product_context = "\n".join(
            f"- {p['name']} ({p['product_type']}): {p['brief'] or 'No description'}"
            for p in products
        )

    prompt = f"""You are a helpful customer support AI for a digital product store. 
Draft a clear, helpful answer to this customer question.

Customer Question: {question}

{"Existing FAQ entries for context:" + chr(10) + faq_context if faq_context else "No existing FAQs yet."}

{"Recent products in the store:" + chr(10) + product_context if product_context else ""}

Requirements:
- Be helpful, friendly, and professional
- Keep the answer concise but thorough (2-4 sentences)
- If the question relates to a specific product, reference it
- Include a follow-up suggestion if appropriate

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "answer": "Your suggested answer here",
  "confidence": 85,
  "category": "general",
  "related_faqs": []
}}"""

    ai_result = await call_text_with_failover("faq", prompt)

    if not ai_result["success"]:
        return {"success": False, "message": ai_result["message"]}

    # Parse AI response
    raw_text = ai_result["result"]
    if "```json" in raw_text:
        raw_text = raw_text.split("```json", 1)[1]
        if "```" in raw_text:
            raw_text = raw_text.split("```", 1)[0]
    elif "```" in raw_text:
        raw_text = raw_text.split("```", 1)[1]
        if "```" in raw_text:
            raw_text = raw_text.split("```", 1)[0]

    try:
        suggestion = json.loads(raw_text.strip())
    except json.JSONDecodeError:
        suggestion = {
            "answer": raw_text.strip(),
            "confidence": 50,
            "category": "general",
            "related_faqs": [],
        }

    return {
        "success": True,
        "question": question,
        "suggested_answer": suggestion.get("answer", ""),
        "confidence": suggestion.get("confidence", 50),
        "category": suggestion.get("category", "general"),
        "related_faqs": suggestion.get("related_faqs", []),
        "provider": ai_result.get("provider"),
        "message": "AI-generated answer suggestion ready for review",
    }
