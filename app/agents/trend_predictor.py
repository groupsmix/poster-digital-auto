"""Trend Predictor AI Agent (Agent 1).

Predicts what digital products will trend in 2-4 weeks.
Analyzes seasonal patterns, upcoming events, historical data,
and social media buzz velocity.
Returns trend predictions with peak dates, confidence scores, and actions.
"""

import json
import logging
import re
from datetime import datetime

from app.ai_failover import call_text_with_failover
from app.database import get_db

logger = logging.getLogger(__name__)


def _build_trend_scan_prompt() -> str:
    """Build the prompt for trend prediction scanning."""
    today = datetime.utcnow().strftime("%B %d, %Y")
    return f"""You are an expert trend forecaster specializing in digital products. Today is {today}.

Your task: Predict 5-8 digital product trends that will PEAK in the next 2-4 weeks.

Consider these factors:
1. SEASONAL PATTERNS:
   - Upcoming holidays and events (Valentine's, Easter, Mother's Day, Back-to-school, etc.)
   - Seasonal needs (New Year resolutions, summer planning, tax season, etc.)
   - Academic calendar (semester start/end, exam periods)

2. SOCIAL MEDIA VELOCITY:
   - Topics gaining traction on TikTok, Instagram, Pinterest
   - Rising search terms and hashtags
   - Viral content themes

3. MARKET TIMING:
   - Products need to be CREATED NOW to catch the peak
   - Account for 1-2 week creation + publishing lead time
   - Historical patterns of when interest spikes

4. DIGITAL PRODUCT TYPES:
   - Templates, planners, trackers, worksheets
   - Design assets, social media kits
   - Educational content, study guides
   - Business tools, financial templates

Respond with ONLY a valid JSON object (no markdown, no code fences):
{{
    "predictions": [
        {{
            "trend": "<specific trend name>",
            "predicted_peak": "<YYYY-MM-DD format>",
            "current_phase": "<early_rise|rising|approaching_peak|at_peak>",
            "confidence": <integer 1-100>,
            "action": "<what to do now, be specific>",
            "time_remaining": "<e.g. '18 days', '2 weeks'>",
            "category": "<seasonal|social|evergreen|event>",
            "evidence": "<why you predict this trend>"
        }}
    ],
    "scan_summary": "<1-2 sentence summary of the trend landscape>"
}}

Be specific and realistic. Sort by confidence descending (highest first).
Focus on actionable predictions where creating products NOW would catch the peak."""


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

    logger.warning("Could not parse JSON from trend predictor response, using fallback")
    return {
        "predictions": [],
        "scan_summary": "Scan completed but could not parse results.",
    }


def _validate_prediction(pred: dict) -> dict:
    """Ensure all required fields exist in a prediction dict."""
    return {
        "trend": pred.get("trend", "Unnamed Trend"),
        "predicted_peak": pred.get("predicted_peak", ""),
        "current_phase": pred.get("current_phase", "early_rise"),
        "confidence": min(max(int(pred.get("confidence", 50)), 1), 100),
        "action": pred.get("action", "Monitor and prepare"),
        "time_remaining": pred.get("time_remaining", "unknown"),
        "category": pred.get("category", ""),
        "evidence": pred.get("evidence", ""),
    }


async def run_trend_scan() -> dict:
    """Run the Trend Predictor AI agent.

    Returns:
        dict with keys: success, predictions (list), scan_summary, provider, message
    """
    prompt = _build_trend_scan_prompt()

    result = await call_text_with_failover("trend_prediction", prompt)

    if not result["success"]:
        return {
            "success": False,
            "predictions": [],
            "scan_summary": "",
            "provider": None,
            "message": result["message"],
        }

    raw_text = result["result"]
    parsed = _parse_json_response(raw_text)

    predictions = [_validate_prediction(p) for p in parsed.get("predictions", [])]
    # Sort by confidence descending
    predictions.sort(key=lambda x: x["confidence"], reverse=True)

    # Store predictions in database
    stored_ids = []
    with get_db() as conn:
        for pred in predictions:
            # Check for duplicate trend names that are still active
            existing = conn.execute(
                "SELECT id FROM trend_predictions WHERE trend_name = ? AND status = 'active'",
                (pred["trend"],),
            ).fetchone()
            if existing:
                # Update existing prediction with fresh data
                conn.execute(
                    """UPDATE trend_predictions
                       SET predicted_peak = ?, current_phase = ?, confidence = ?,
                           action = ?, time_remaining = ?, category = ?, evidence = ?
                       WHERE id = ?""",
                    (
                        pred["predicted_peak"],
                        pred["current_phase"],
                        pred["confidence"],
                        pred["action"],
                        pred["time_remaining"],
                        pred["category"],
                        pred["evidence"],
                        existing["id"],
                    ),
                )
                stored_ids.append(existing["id"])
                continue

            cursor = conn.execute(
                """INSERT INTO trend_predictions
                   (trend_name, predicted_peak, current_phase, confidence,
                    action, time_remaining, category, evidence, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')""",
                (
                    pred["trend"],
                    pred["predicted_peak"],
                    pred["current_phase"],
                    pred["confidence"],
                    pred["action"],
                    pred["time_remaining"],
                    pred["category"],
                    pred["evidence"],
                ),
            )
            stored_ids.append(cursor.lastrowid)

    # Log the scan
    with get_db() as conn:
        conn.execute(
            """INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message)
               VALUES (NULL, 'trend_predictor', ?, 'success', ?)""",
            (result["provider"], f"Found {len(predictions)} trend predictions"),
        )

    return {
        "success": True,
        "predictions": predictions,
        "stored_ids": stored_ids,
        "scan_summary": parsed.get("scan_summary", ""),
        "provider": result["provider"],
        "message": f"Trend scan complete: {len(predictions)} predictions via {result['provider']}",
    }


def get_all_trends(status: str | None = None) -> list[dict]:
    """Get all trend predictions from database.

    Args:
        status: Filter by status (active, expired, created)
    """
    with get_db() as conn:
        query = "SELECT * FROM trend_predictions"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY confidence DESC, created_at DESC"
        rows = conn.execute(query, params).fetchall()

    return [dict(row) for row in rows]


def get_active_alerts() -> list[dict]:
    """Get high-confidence active trends for dashboard alerts.

    Returns trends with confidence >= 70 that are still active.
    """
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM trend_predictions
               WHERE status = 'active' AND confidence >= 70
               ORDER BY confidence DESC
               LIMIT 5""",
        ).fetchall()

    return [dict(row) for row in rows]


async def create_product_from_trend(trend_id: int) -> dict:
    """Create a product from a trend prediction.

    Args:
        trend_id: ID of the trend prediction.

    Returns:
        dict with product_id and status info.
    """
    with get_db() as conn:
        trend = conn.execute(
            "SELECT * FROM trend_predictions WHERE id = ?", (trend_id,)
        ).fetchone()
        if not trend:
            return {"success": False, "message": "Trend prediction not found"}

        trend_dict = dict(trend)

        # Create the product
        cursor = conn.execute(
            """INSERT INTO products
               (name, product_type, brief, target_platforms, target_languages, status, plan_mode, trend_data)
               VALUES (?, 'digital', ?, '["Gumroad","Payhip"]', '["en"]', 'pending', 'A', ?)""",
            (
                trend_dict["trend_name"],
                f"Trend-based product. {trend_dict.get('action', '')}. "
                f"Predicted peak: {trend_dict.get('predicted_peak', '')}. "
                f"Evidence: {trend_dict.get('evidence', '')}",
                json.dumps({
                    "trend_id": trend_id,
                    "predicted_peak": trend_dict.get("predicted_peak"),
                    "confidence": trend_dict.get("confidence"),
                    "current_phase": trend_dict.get("current_phase"),
                    "time_remaining": trend_dict.get("time_remaining"),
                }),
            ),
        )
        product_id = cursor.lastrowid

        # Update trend status
        conn.execute(
            "UPDATE trend_predictions SET status = 'created', created_product_id = ? WHERE id = ?",
            (product_id, trend_id),
        )

    return {
        "success": True,
        "product_id": product_id,
        "message": f"Product '{trend_dict['trend_name']}' created from trend prediction #{trend_id}",
    }
