"""Revenue Goals module for AI Product Factory.

Provides goal setting, progress tracking, AI-powered calculations
of products/sales needed, and smart suggestions when behind target.
"""

import json
import logging
from datetime import datetime

from app.database import get_db

logger = logging.getLogger(__name__)


def create_goal(target_amount: float, period: str = "monthly") -> dict:
    """Create a revenue goal."""
    valid_periods = {"weekly", "monthly", "quarterly", "yearly"}
    if period not in valid_periods:
        return {"success": False, "message": f"Period must be one of: {', '.join(valid_periods)}"}

    with get_db() as conn:
        # Deactivate any existing active goals for the same period
        conn.execute(
            "UPDATE revenue_goals SET status = 'inactive' WHERE period = ? AND status = 'active'",
            (period,),
        )

        cursor = conn.execute(
            """INSERT INTO revenue_goals (target_amount, period, current_amount, status)
               VALUES (?, ?, 0, 'active')""",
            (target_amount, period),
        )
        goal_id = cursor.lastrowid
        goal = conn.execute(
            "SELECT * FROM revenue_goals WHERE id = ?", (goal_id,)
        ).fetchone()

    return {
        "success": True,
        "goal": dict(goal),
        "message": f"Revenue goal set: ${target_amount:.2f}/{period}",
    }


def get_goals() -> list[dict]:
    """Get all revenue goals with current progress."""
    with get_db() as conn:
        goals = conn.execute(
            "SELECT * FROM revenue_goals ORDER BY created_at DESC"
        ).fetchall()

        result = []
        for goal in goals:
            goal_dict = dict(goal)
            goal_dict = _enrich_goal(conn, goal_dict)
            result.append(goal_dict)

    return result


def get_active_goal() -> dict | None:
    """Get the current active revenue goal with full progress details."""
    with get_db() as conn:
        goal = conn.execute(
            "SELECT * FROM revenue_goals WHERE status = 'active' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        if not goal:
            return None

        goal_dict = dict(goal)
        goal_dict = _enrich_goal(conn, goal_dict)

    return goal_dict


def update_goal_progress() -> dict:
    """Recalculate progress for all active goals based on actual analytics."""
    with get_db() as conn:
        active_goals = conn.execute(
            "SELECT * FROM revenue_goals WHERE status = 'active'"
        ).fetchall()

        updated = []
        for goal in active_goals:
            goal_dict = dict(goal)
            period = goal_dict["period"]
            cutoff = _get_period_cutoff(period)

            current = conn.execute(
                """SELECT COALESCE(SUM(revenue), 0) as total
                   FROM analytics
                   WHERE event_type = 'sale' AND recorded_at >= ?""",
                (cutoff,),
            ).fetchone()
            current_amount = current["total"] if current else 0

            conn.execute(
                "UPDATE revenue_goals SET current_amount = ? WHERE id = ?",
                (current_amount, goal_dict["id"]),
            )

            goal_dict["current_amount"] = current_amount
            goal_dict = _enrich_goal(conn, goal_dict)
            updated.append(goal_dict)

    return {"updated": updated, "count": len(updated)}


def _enrich_goal(conn, goal_dict: dict) -> dict:
    """Add calculated fields to a goal dict."""
    target = goal_dict["target_amount"] or 0
    period = goal_dict["period"]
    cutoff = _get_period_cutoff(period)

    # Get actual current revenue for the period
    current_row = conn.execute(
        """SELECT COALESCE(SUM(revenue), 0) as total
           FROM analytics
           WHERE event_type = 'sale' AND recorded_at >= ?""",
        (cutoff,),
    ).fetchone()
    current_amount = current_row["total"] if current_row else 0
    goal_dict["current_amount"] = current_amount

    # Progress percentage
    progress = round((current_amount / target * 100) if target > 0 else 0, 1)
    goal_dict["progress_percent"] = min(progress, 100)

    # Remaining
    remaining = max(target - current_amount, 0)
    goal_dict["remaining"] = round(remaining, 2)

    # Average sale price
    avg_sale = conn.execute(
        """SELECT AVG(revenue) as avg_rev, COUNT(*) as cnt
           FROM analytics
           WHERE event_type = 'sale' AND revenue > 0 AND recorded_at >= ?""",
        (cutoff,),
    ).fetchone()
    avg_price = avg_sale["avg_rev"] if avg_sale and avg_sale["avg_rev"] else 0
    sales_count = avg_sale["cnt"] if avg_sale else 0

    goal_dict["avg_sale_price"] = round(avg_price, 2) if avg_price else 0
    goal_dict["sales_this_period"] = sales_count

    # Products/sales needed to hit goal
    if avg_price and avg_price > 0:
        sales_needed = max(0, int((remaining / avg_price) + 0.99))  # ceil
    else:
        sales_needed = 0
    goal_dict["sales_needed"] = sales_needed

    # Products count
    products_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM products"
    ).fetchone()["cnt"]
    goal_dict["total_products"] = products_count

    # Smart suggestions
    goal_dict["suggestions"] = _generate_suggestions(
        target, current_amount, progress, remaining, avg_price, sales_needed,
        products_count, period
    )

    # Status indicator
    if progress >= 100:
        goal_dict["status_label"] = "achieved"
    elif progress >= 75:
        goal_dict["status_label"] = "on_track"
    elif progress >= 50:
        goal_dict["status_label"] = "behind"
    else:
        goal_dict["status_label"] = "at_risk"

    return goal_dict


def _generate_suggestions(
    target: float, current: float, progress: float, remaining: float,
    avg_price: float, sales_needed: int, products_count: int, period: str
) -> list[dict]:
    """Generate smart suggestions based on goal progress."""
    suggestions = []

    if progress >= 100:
        suggestions.append({
            "type": "success",
            "icon": "trophy",
            "message": f"Congratulations! You've hit your ${target:.0f}/{period} goal!",
        })
        return suggestions

    if progress < 25:
        suggestions.append({
            "type": "action",
            "icon": "alert-triangle",
            "message": f"You're at {progress}% of your goal. Consider creating more products or running promotions.",
        })

    if sales_needed > 0 and avg_price > 0:
        suggestions.append({
            "type": "insight",
            "icon": "target",
            "message": f"You need {sales_needed} more sales at ${avg_price:.2f} avg to hit your goal.",
        })

    if products_count < 5:
        suggestions.append({
            "type": "action",
            "icon": "plus-circle",
            "message": f"You only have {products_count} products. Creating more products increases your chances.",
        })

    if remaining > 0 and avg_price > 0:
        price_to_hit = round(remaining / max(sales_needed, 1), 2)
        if price_to_hit > avg_price * 1.5:
            suggestions.append({
                "type": "pricing",
                "icon": "dollar-sign",
                "message": f"Consider raising prices. You'd need ${price_to_hit:.2f}/sale vs your ${avg_price:.2f} average.",
            })

    if progress >= 50 and progress < 100:
        suggestions.append({
            "type": "motivation",
            "icon": "trending-up",
            "message": f"You're {progress}% there! ${remaining:.2f} to go. Keep pushing!",
        })

    if not suggestions:
        suggestions.append({
            "type": "info",
            "icon": "info",
            "message": "Start recording sales to track your progress toward the goal.",
        })

    return suggestions


def _get_period_cutoff(period: str) -> str:
    """Get the start date for a period."""
    now = datetime.utcnow()
    if period == "weekly":
        from datetime import timedelta
        cutoff = now - timedelta(days=7)
    elif period == "monthly":
        cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "quarterly":
        quarter_month = ((now.month - 1) // 3) * 3 + 1
        cutoff = now.replace(month=quarter_month, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "yearly":
        cutoff = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        cutoff = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return cutoff.isoformat()
