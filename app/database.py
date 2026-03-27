"""Database initialization and connection management for AI Product Factory."""

import os
import sqlite3
from contextlib import contextmanager

# Use /data/app.db for persistent storage in production (Oracle Cloud volume),
# fall back to local file for development
DB_PATH = os.environ.get("DATABASE_PATH", "/data/app.db") if os.path.isdir("/data") else "app.db"


def get_connection() -> sqlite3.Connection:
    """Get a new database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            product_type TEXT DEFAULT 'digital',
            brief TEXT,
            target_platforms TEXT DEFAULT '[]',
            target_languages TEXT DEFAULT '["en"]',
            status TEXT DEFAULT 'pending',
            plan_mode TEXT DEFAULT 'A',
            research_data TEXT DEFAULT '{}',
            niche_data TEXT DEFAULT '{}',
            trend_data TEXT DEFAULT '{}',
            remix_parent_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS product_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            language TEXT DEFAULT 'en',
            title TEXT,
            description TEXT,
            tags TEXT DEFAULT '[]',
            price TEXT,
            image_urls TEXT DEFAULT '[]',
            ceo_score REAL DEFAULT 0,
            ceo_feedback TEXT DEFAULT '',
            ceo_status TEXT DEFAULT 'pending',
            revision_count INTEGER DEFAULT 0,
            post_status TEXT DEFAULT 'pending',
            post_url TEXT DEFAULT '',
            ab_variant TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            caption TEXT,
            video_url TEXT DEFAULT '',
            voice_url TEXT DEFAULT '',
            post_status TEXT DEFAULT 'pending',
            post_url TEXT DEFAULT '',
            scheduled_at TEXT,
            posted_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS repurposed_content (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            content TEXT,
            platform TEXT,
            post_status TEXT DEFAULT 'draft',
            scheduled_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS niche_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            demand_score INTEGER,
            competition TEXT,
            monthly_searches INTEGER,
            evidence TEXT,
            suggested_price TEXT,
            best_platforms TEXT DEFAULT '[]',
            status TEXT DEFAULT 'new',
            created_product_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS trend_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trend_name TEXT NOT NULL,
            predicted_peak TEXT,
            current_phase TEXT DEFAULT 'early_rise',
            confidence INTEGER DEFAULT 50,
            action TEXT,
            time_remaining TEXT,
            category TEXT DEFAULT '',
            evidence TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            created_product_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            variant_id INTEGER,
            platform TEXT,
            event_type TEXT,
            revenue REAL DEFAULT 0,
            data TEXT DEFAULT '{}',
            recorded_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ab_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            test_name TEXT,
            variant_a_id INTEGER,
            variant_b_id INTEGER,
            variant_c_id INTEGER,
            winner_id INTEGER,
            status TEXT DEFAULT 'running',
            started_at TEXT DEFAULT (datetime('now')),
            ended_at TEXT
        );

        CREATE TABLE IF NOT EXISTS customer_personas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age_range TEXT,
            description TEXT,
            preferences TEXT DEFAULT '{}',
            platforms TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS email_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            subject_lines TEXT DEFAULT '[]',
            email_body TEXT,
            follow_up_day3 TEXT,
            follow_up_day7 TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS revenue_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_amount REAL,
            period TEXT DEFAULT 'monthly',
            current_amount REAL DEFAULT 0,
            products_needed INTEGER,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS platform_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT NOT NULL UNIQUE,
            type TEXT DEFAULT 'selling',
            tone TEXT DEFAULT '',
            plan_mode TEXT DEFAULT 'A',
            enabled INTEGER DEFAULT 1,
            max_title_length INTEGER,
            max_description_length INTEGER,
            custom_instructions TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS settings_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ai_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL UNIQUE,
            model TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            requests_today INTEGER DEFAULT 0,
            daily_limit INTEGER DEFAULT 0,
            last_used TEXT,
            last_error TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS pipeline_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            agent TEXT NOT NULL,
            ai_provider TEXT,
            status TEXT DEFAULT 'running',
            message TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS faq_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            times_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """)

    conn.commit()
    conn.close()


def seed_platform_settings():
    """Insert default platform settings if table is empty."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM platform_settings")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return

    platforms = [
        # Selling platforms
        ("Gumroad", "selling", "casual", "A", 1, 80, 5000, "Creator-friendly, direct tone. Use casual language."),
        ("Payhip", "selling", "professional", "A", 1, 100, 5000, "Clean, professional, value-focused descriptions."),
        ("Lemon Squeezy", "selling", "modern", "A", 1, 100, 5000, "Modern, tech-savvy, concise copy."),
        # Social platforms
        ("Reddit", "social", "helpful", "A", 1, 300, 10000, "Community-focused, NO hard selling. Be helpful and genuine."),
        ("Tumblr", "social", "creative", "B", 1, 200, 5000, "Visual, creative, hashtag-heavy, aesthetic vibes."),
        ("Twitter", "social", "punchy", "A", 1, 280, 280, "Short, punchy, max 280 chars. Hook in first line."),
        ("Pinterest", "social", "seo", "B", 1, 100, 500, "SEO-heavy description, keyword-rich for discovery."),
        ("Telegram", "social", "direct", "B", 1, 200, 4096, "Direct, informative, include links and CTAs."),
        ("Instagram", "social", "engaging", "A", 1, 200, 2200, "Engaging caption + hashtags + CTA. Visual-first."),
        ("TikTok", "social", "trendy", "A", 1, 150, 2200, "Trendy, casual, hook in first line. Use trending sounds."),
        ("Facebook", "social", "conversational", "A", 1, 200, 5000, "Conversational, value-focused, community-building."),
        ("Quora", "social", "educational", "A", 1, 200, 5000, "Answer-style, educational, helpful. Establish authority."),
    ]

    cursor.executemany(
        """INSERT INTO platform_settings
           (platform, type, tone, plan_mode, enabled, max_title_length, max_description_length, custom_instructions)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        platforms,
    )

    conn.commit()
    conn.close()


def seed_preferences():
    """Insert default preferences if table is empty."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM settings_preferences")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return

    import json
    defaults = [
        ("default_platforms", json.dumps(["Gumroad", "Payhip"])),
        ("default_languages", json.dumps(["en"])),
        ("default_plan_mode", json.dumps("A")),
        ("default_price_range", json.dumps({"min": 5, "max": 15})),
        ("notification_niche_finder", json.dumps(True)),
        ("notification_trend_alerts", json.dumps(True)),
        ("notification_ceo_rejections", json.dumps(True)),
        ("notification_revenue_milestones", json.dumps(True)),
        ("notification_method", json.dumps("dashboard")),
    ]

    cursor.executemany(
        """INSERT INTO settings_preferences (key, value)
           VALUES (?, ?)""",
        defaults,
    )

    conn.commit()
    conn.close()


def seed_ai_status():
    """Insert default AI provider statuses if table is empty."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM ai_status")
    count = cursor.fetchone()[0]
    if count > 0:
        conn.close()
        return

    providers = [
        ("gemini_pro", "gemini-2.5-pro", "active", 0, 100),
        ("gemini_flash", "gemini-2.5-flash", "active", 0, 250),
        ("groq_llama", "llama-3.3-70b", "active", 0, 1000),
        ("cloudflare_llama", "llama-3.1-8b", "active", 0, 10000),
        ("cerebras_qwen", "qwen-3-32b", "active", 0, 1000),
        ("mistral_large", "mistral-large", "active", 0, 500),
        ("cloudflare_flux", "flux-1-schnell", "active", 0, 230),
        ("playground_ai", "playground-v2", "active", 0, 500),
        ("leonardo_ai", "leonardo-v2", "active", 0, 150),
        ("huggingface_sd", "stable-diffusion-xl", "active", 0, 200),
    ]

    cursor.executemany(
        """INSERT INTO ai_status (provider, model, status, requests_today, daily_limit)
           VALUES (?, ?, ?, ?, ?)""",
        providers,
    )

    conn.commit()
    conn.close()
