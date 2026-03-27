"""Analytics module for AI Product Factory.

Provides event tracking, revenue analytics, platform comparison,
product deep-dive, AI-generated insights, and CSV import.
"""

import csv
import io
import json
import logging
from datetime import datetime, timedelta

from app.database import get_db

logger = logging.getLogger(__name__)


def record_event(
    product_id: int | None,
    variant_id: int | None,
    platform: str,
    event_type: str,
    revenue: float = 0.0,
    data: dict | None = None,
) -> dict:
    """Record an analytics event (view, click, sale, refund)."""
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO analytics (product_id, variant_id, platform, event_type, revenue, data, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                product_id,
                variant_id,
                platform,
                event_type,
                revenue,
                json.dumps(data or {}),
                datetime.utcnow().isoformat(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM analytics WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return dict(row)


def get_overview() -> dict:
    """Dashboard overview: total revenue, products created, best platform, avg CEO score."""
    with get_db() as conn:
        # Total revenue
        total_revenue_row = conn.execute(
            "SELECT COALESCE(SUM(revenue), 0) as total FROM analytics WHERE event_type = 'sale'"
        ).fetchone()
        total_revenue = total_revenue_row["total"]

        # Total refunds
        total_refunds_row = conn.execute(
            "SELECT COALESCE(SUM(ABS(revenue)), 0) as total FROM analytics WHERE event_type = 'refund'"
        ).fetchone()
        total_refunds = total_refunds_row["total"]

        # Net revenue
        net_revenue = total_revenue - total_refunds

        # Products created
        products_count = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()["cnt"]

        # Total sales count
        sales_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM analytics WHERE event_type = 'sale'"
        ).fetchone()["cnt"]

        # Total views
        views_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM analytics WHERE event_type = 'view'"
        ).fetchone()["cnt"]

        # Total clicks
        clicks_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM analytics WHERE event_type = 'click'"
        ).fetchone()["cnt"]

        # Best platform by revenue
        best_platform_row = conn.execute(
            """SELECT platform, SUM(revenue) as total
               FROM analytics WHERE event_type = 'sale'
               GROUP BY platform ORDER BY total DESC LIMIT 1"""
        ).fetchone()
        best_platform = best_platform_row["platform"] if best_platform_row else "N/A"
        best_platform_revenue = best_platform_row["total"] if best_platform_row else 0

        # Average CEO score
        avg_ceo_row = conn.execute(
            "SELECT COALESCE(AVG(ceo_score), 0) as avg_score FROM product_variants WHERE ceo_score > 0"
        ).fetchone()
        avg_ceo_score = round(avg_ceo_row["avg_score"], 1)

        # Products approved vs total reviewed
        approved_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM product_variants WHERE ceo_status = 'approved'"
        ).fetchone()["cnt"]
        reviewed_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM product_variants WHERE ceo_status IN ('approved', 'rejected')"
        ).fetchone()["cnt"]
        approval_rate = round((approved_count / reviewed_count * 100) if reviewed_count > 0 else 0, 1)

    return {
        "total_revenue": total_revenue,
        "total_refunds": total_refunds,
        "net_revenue": net_revenue,
        "products_created": products_count,
        "total_sales": sales_count,
        "total_views": views_count,
        "total_clicks": clicks_count,
        "best_platform": best_platform,
        "best_platform_revenue": best_platform_revenue,
        "avg_ceo_score": avg_ceo_score,
        "approval_rate": approval_rate,
    }


def get_revenue_over_time(period: str = "30d") -> dict:
    """Revenue over time for charting. Periods: 7d, 30d, 90d, all."""
    days_map = {"7d": 7, "30d": 30, "90d": 90, "all": 3650}
    days = days_map.get(period, 30)

    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    with get_db() as conn:
        rows = conn.execute(
            """SELECT DATE(recorded_at) as date,
                      SUM(CASE WHEN event_type = 'sale' THEN revenue ELSE 0 END) as sales,
                      SUM(CASE WHEN event_type = 'refund' THEN ABS(revenue) ELSE 0 END) as refunds,
                      COUNT(CASE WHEN event_type = 'sale' THEN 1 END) as sale_count,
                      COUNT(CASE WHEN event_type = 'view' THEN 1 END) as view_count,
                      COUNT(CASE WHEN event_type = 'click' THEN 1 END) as click_count
               FROM analytics
               WHERE recorded_at >= ?
               GROUP BY DATE(recorded_at)
               ORDER BY date ASC""",
            (cutoff,),
        ).fetchall()

    data_points = []
    for row in rows:
        data_points.append({
            "date": row["date"],
            "revenue": row["sales"] - row["refunds"],
            "sales": row["sales"],
            "refunds": row["refunds"],
            "sale_count": row["sale_count"],
            "views": row["view_count"],
            "clicks": row["click_count"],
        })

    return {"period": period, "data": data_points, "count": len(data_points)}


def get_platform_performance() -> dict:
    """Per-platform performance comparison."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT platform,
                      SUM(CASE WHEN event_type = 'sale' THEN revenue ELSE 0 END) as revenue,
                      SUM(CASE WHEN event_type = 'refund' THEN ABS(revenue) ELSE 0 END) as refunds,
                      COUNT(CASE WHEN event_type = 'sale' THEN 1 END) as sales,
                      COUNT(CASE WHEN event_type = 'view' THEN 1 END) as views,
                      COUNT(CASE WHEN event_type = 'click' THEN 1 END) as clicks,
                      COUNT(*) as total_events
               FROM analytics
               GROUP BY platform
               ORDER BY revenue DESC"""
        ).fetchall()

        # Also get social post counts per platform
        post_counts = conn.execute(
            """SELECT platform, COUNT(*) as cnt FROM social_posts GROUP BY platform"""
        ).fetchall()
        post_map = {r["platform"]: r["cnt"] for r in post_counts}

    platforms = []
    for row in rows:
        net_revenue = row["revenue"] - row["refunds"]
        conversion = round((row["sales"] / row["views"] * 100) if row["views"] > 0 else 0, 1)
        platforms.append({
            "platform": row["platform"],
            "revenue": net_revenue,
            "gross_revenue": row["revenue"],
            "refunds": row["refunds"],
            "sales": row["sales"],
            "views": row["views"],
            "clicks": row["clicks"],
            "conversion_rate": conversion,
            "posts": post_map.get(row["platform"], 0),
        })

    return {"platforms": platforms, "count": len(platforms)}


def get_product_analytics(product_id: int) -> dict:
    """Single product deep-dive analytics."""
    with get_db() as conn:
        # Product info
        product = conn.execute(
            "SELECT id, name, status, created_at FROM products WHERE id = ?", (product_id,)
        ).fetchone()
        if not product:
            return {"error": "Product not found"}

        # Revenue & events
        events = conn.execute(
            """SELECT platform, event_type,
                      SUM(revenue) as total_revenue,
                      COUNT(*) as count
               FROM analytics WHERE product_id = ?
               GROUP BY platform, event_type""",
            (product_id,),
        ).fetchall()

        # Revenue over time
        timeline = conn.execute(
            """SELECT DATE(recorded_at) as date,
                      SUM(CASE WHEN event_type = 'sale' THEN revenue ELSE 0 END) as revenue,
                      COUNT(CASE WHEN event_type = 'sale' THEN 1 END) as sales
               FROM analytics WHERE product_id = ?
               GROUP BY DATE(recorded_at)
               ORDER BY date ASC""",
            (product_id,),
        ).fetchall()

        # CEO scores for this product
        variants = conn.execute(
            """SELECT platform, ceo_score, ceo_status, revision_count
               FROM product_variants WHERE product_id = ?""",
            (product_id,),
        ).fetchall()

    # Aggregate by platform
    platform_breakdown = {}
    for ev in events:
        plat = ev["platform"]
        if plat not in platform_breakdown:
            platform_breakdown[plat] = {"revenue": 0, "sales": 0, "views": 0, "clicks": 0, "refunds": 0}
        etype = ev["event_type"]
        if etype == "sale":
            platform_breakdown[plat]["revenue"] += ev["total_revenue"]
            platform_breakdown[plat]["sales"] += ev["count"]
        elif etype == "view":
            platform_breakdown[plat]["views"] += ev["count"]
        elif etype == "click":
            platform_breakdown[plat]["clicks"] += ev["count"]
        elif etype == "refund":
            platform_breakdown[plat]["refunds"] += abs(ev["total_revenue"])

    return {
        "product": dict(product),
        "platform_breakdown": platform_breakdown,
        "timeline": [dict(r) for r in timeline],
        "variants": [dict(v) for v in variants],
    }


def get_top_products(limit: int = 10) -> list[dict]:
    """Get top products sorted by revenue."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT a.product_id, p.name, p.status, p.created_at,
                      SUM(CASE WHEN a.event_type = 'sale' THEN a.revenue ELSE 0 END) as revenue,
                      SUM(CASE WHEN a.event_type = 'refund' THEN ABS(a.revenue) ELSE 0 END) as refunds,
                      COUNT(CASE WHEN a.event_type = 'sale' THEN 1 END) as sales,
                      COUNT(CASE WHEN a.event_type = 'view' THEN 1 END) as views
               FROM analytics a
               JOIN products p ON a.product_id = p.id
               GROUP BY a.product_id
               ORDER BY revenue DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()

    return [
        {
            "product_id": r["product_id"],
            "name": r["name"],
            "status": r["status"],
            "created_at": r["created_at"],
            "revenue": r["revenue"] - r["refunds"],
            "gross_revenue": r["revenue"],
            "refunds": r["refunds"],
            "sales": r["sales"],
            "views": r["views"],
        }
        for r in rows
    ]


def get_ceo_score_trend() -> list[dict]:
    """CEO approval rate trend over time - are products getting better?"""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT DATE(p.created_at) as date,
                      AVG(pv.ceo_score) as avg_score,
                      COUNT(CASE WHEN pv.ceo_status = 'approved' THEN 1 END) as approved,
                      COUNT(CASE WHEN pv.ceo_status = 'rejected' THEN 1 END) as rejected,
                      COUNT(*) as total
               FROM product_variants pv
               JOIN products p ON pv.product_id = p.id
               WHERE pv.ceo_score > 0
               GROUP BY DATE(p.created_at)
               ORDER BY date ASC"""
        ).fetchall()

    return [
        {
            "date": r["date"],
            "avg_score": round(r["avg_score"], 1),
            "approved": r["approved"],
            "rejected": r["rejected"],
            "total": r["total"],
            "approval_rate": round(
                (r["approved"] / (r["approved"] + r["rejected"]) * 100)
                if (r["approved"] + r["rejected"]) > 0
                else 0,
                1,
            ),
        }
        for r in rows
    ]


def get_ai_provider_usage() -> list[dict]:
    """AI provider usage breakdown for pie chart."""
    with get_db() as conn:
        rows = conn.execute(
            """SELECT ai_provider, COUNT(*) as usage_count,
                      COUNT(CASE WHEN status = 'done' THEN 1 END) as success,
                      COUNT(CASE WHEN status = 'error' THEN 1 END) as errors
               FROM pipeline_logs
               WHERE ai_provider IS NOT NULL AND ai_provider != ''
               GROUP BY ai_provider
               ORDER BY usage_count DESC"""
        ).fetchall()

    return [
        {
            "provider": r["ai_provider"],
            "usage_count": r["usage_count"],
            "success": r["success"],
            "errors": r["errors"],
            "success_rate": round(
                (r["success"] / r["usage_count"] * 100) if r["usage_count"] > 0 else 0, 1
            ),
        }
        for r in rows
    ]


def generate_insights() -> list[dict]:
    """Generate AI-powered insights from analytics data."""
    insights = []

    with get_db() as conn:
        # Insight 1: Best-selling platform
        best_platform = conn.execute(
            """SELECT platform, SUM(revenue) as total, COUNT(*) as cnt
               FROM analytics WHERE event_type = 'sale'
               GROUP BY platform ORDER BY total DESC LIMIT 1"""
        ).fetchone()
        if best_platform and best_platform["total"] > 0:
            insights.append({
                "type": "revenue",
                "icon": "trending-up",
                "message": f"{best_platform['platform']} is your top revenue platform with ${best_platform['total']:.2f} from {best_platform['cnt']} sales.",
                "severity": "positive",
            })

        # Insight 2: Platform comparison
        platforms = conn.execute(
            """SELECT platform, SUM(revenue) as total
               FROM analytics WHERE event_type = 'sale'
               GROUP BY platform ORDER BY total DESC"""
        ).fetchall()
        if len(platforms) >= 2:
            top = platforms[0]
            second = platforms[1]
            if second["total"] > 0:
                ratio = round(top["total"] / second["total"], 1)
                if ratio >= 2:
                    insights.append({
                        "type": "comparison",
                        "icon": "bar-chart",
                        "message": f"Products on {top['platform']} earn {ratio}x more than {second['platform']}.",
                        "severity": "info",
                    })

        # Insight 3: CEO score trend
        recent_scores = conn.execute(
            """SELECT AVG(ceo_score) as avg_score
               FROM product_variants
               WHERE ceo_score > 0
               AND created_at >= datetime('now', '-30 days')"""
        ).fetchone()
        older_scores = conn.execute(
            """SELECT AVG(ceo_score) as avg_score
               FROM product_variants
               WHERE ceo_score > 0
               AND created_at < datetime('now', '-30 days')
               AND created_at >= datetime('now', '-60 days')"""
        ).fetchone()
        if recent_scores and older_scores and recent_scores["avg_score"] and older_scores["avg_score"]:
            diff = recent_scores["avg_score"] - older_scores["avg_score"]
            if abs(diff) >= 0.3:
                direction = "improved" if diff > 0 else "declined"
                severity = "positive" if diff > 0 else "warning"
                insights.append({
                    "type": "quality",
                    "icon": "award",
                    "message": f"Your average CEO score has {direction} from {older_scores['avg_score']:.1f} to {recent_scores['avg_score']:.1f} this month.",
                    "severity": severity,
                })

        # Insight 4: Best day of week for sales
        best_day = conn.execute(
            """SELECT
                  CASE CAST(strftime('%w', recorded_at) AS INTEGER)
                    WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday' WHEN 6 THEN 'Saturday'
                  END as day_name,
                  COUNT(*) as cnt
               FROM analytics WHERE event_type = 'sale'
               GROUP BY day_name ORDER BY cnt DESC LIMIT 1"""
        ).fetchone()
        if best_day and best_day["cnt"] > 0:
            insights.append({
                "type": "timing",
                "icon": "calendar",
                "message": f"Products posted on {best_day['day_name']} get the most sales ({best_day['cnt']} total).",
                "severity": "info",
            })

        # Insight 5: Conversion rate
        total_views = conn.execute(
            "SELECT COUNT(*) as cnt FROM analytics WHERE event_type = 'view'"
        ).fetchone()["cnt"]
        total_sales = conn.execute(
            "SELECT COUNT(*) as cnt FROM analytics WHERE event_type = 'sale'"
        ).fetchone()["cnt"]
        if total_views > 0:
            conv_rate = round(total_sales / total_views * 100, 1)
            severity = "positive" if conv_rate >= 5 else ("warning" if conv_rate >= 2 else "negative")
            insights.append({
                "type": "conversion",
                "icon": "target",
                "message": f"Your overall conversion rate is {conv_rate}% ({total_sales} sales from {total_views} views).",
                "severity": severity,
            })

        # Insight 6: Products without sales
        products_without_sales = conn.execute(
            """SELECT COUNT(*) as cnt FROM products p
               WHERE NOT EXISTS (
                   SELECT 1 FROM analytics a WHERE a.product_id = p.id AND a.event_type = 'sale'
               )"""
        ).fetchone()["cnt"]
        total_products = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()["cnt"]
        if total_products > 0 and products_without_sales > 0:
            pct = round(products_without_sales / total_products * 100, 0)
            insights.append({
                "type": "opportunity",
                "icon": "lightbulb",
                "message": f"{products_without_sales} of {total_products} products ({pct:.0f}%) have no recorded sales yet.",
                "severity": "warning" if pct > 50 else "info",
            })

        # Insight 7: Refund rate
        refund_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM analytics WHERE event_type = 'refund'"
        ).fetchone()["cnt"]
        if total_sales > 0 and refund_count > 0:
            refund_rate = round(refund_count / total_sales * 100, 1)
            severity = "negative" if refund_rate > 10 else ("warning" if refund_rate > 5 else "positive")
            insights.append({
                "type": "refunds",
                "icon": "alert-triangle",
                "message": f"Refund rate is {refund_rate}% ({refund_count} refunds out of {total_sales} sales).",
                "severity": severity,
            })

    # If no data-driven insights, provide defaults
    if not insights:
        insights.append({
            "type": "getting-started",
            "icon": "info",
            "message": "Start logging sales to see AI-powered insights about your product performance.",
            "severity": "info",
        })

    return insights


def import_sales_csv(csv_content: str) -> dict:
    """Import sales from CSV. Expected columns: product_id, platform, revenue, date (optional)."""
    reader = csv.DictReader(io.StringIO(csv_content))
    imported = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        try:
            product_id = int(row.get("product_id", 0))
            platform = row.get("platform", "").strip()
            revenue = float(row.get("revenue", 0))
            date = row.get("date", "").strip() or datetime.utcnow().isoformat()

            if not product_id or not platform:
                errors.append(f"Row {i}: missing product_id or platform")
                continue

            with get_db() as conn:
                conn.execute(
                    """INSERT INTO analytics (product_id, variant_id, platform, event_type, revenue, data, recorded_at)
                       VALUES (?, NULL, ?, 'sale', ?, '{}', ?)""",
                    (product_id, platform, revenue, date),
                )
            imported += 1
        except (ValueError, KeyError) as e:
            errors.append(f"Row {i}: {str(e)}")

    return {
        "imported": imported,
        "errors": errors,
        "message": f"Imported {imported} sales records" + (f" with {len(errors)} errors" if errors else ""),
    }
