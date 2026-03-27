"""AI Failover System for AI Product Factory.

Provides automatic failover between free AI providers for text and image generation.
Each task has a chain of providers - if one fails or hits rate limits, it tries the next.
"""

import os
import json
import logging
from datetime import datetime
from dataclasses import dataclass, field

from app.database import get_db

logger = logging.getLogger(__name__)


@dataclass
class AIProvider:
    """Represents an AI provider with status tracking."""
    name: str
    model: str
    provider_type: str  # "text" or "image"
    status: str = "active"  # active, rate_limited, error, disabled
    requests_today: int = 0
    daily_limit: int = 0
    last_used: str = ""
    last_error: str = ""

    @property
    def is_available(self) -> bool:
        """Check if provider is available for requests."""
        if self.status in ("error", "disabled"):
            return False
        if self.daily_limit > 0 and self.requests_today >= self.daily_limit:
            return False
        return True

    def record_success(self):
        """Record a successful request."""
        self.requests_today += 1
        self.last_used = datetime.utcnow().isoformat()
        self.status = "active"
        self._save_to_db()

    def record_failure(self, error: str):
        """Record a failed request."""
        self.last_error = error
        self.last_used = datetime.utcnow().isoformat()
        if "rate limit" in error.lower() or "429" in error:
            self.status = "rate_limited"
        else:
            self.status = "error"
        self._save_to_db()

    def _save_to_db(self):
        """Persist provider status to database."""
        with get_db() as conn:
            conn.execute(
                """UPDATE ai_status
                   SET status = ?, requests_today = ?, last_used = ?, last_error = ?
                   WHERE provider = ?""",
                (self.status, self.requests_today, self.last_used, self.last_error, self.name),
            )


# ── Provider Registry ──────────────────────────────────────────────────

TEXT_PROVIDERS: dict[str, AIProvider] = {
    "gemini_pro": AIProvider("gemini_pro", "gemini-2.5-pro", "text", daily_limit=100),
    "gemini_flash": AIProvider("gemini_flash", "gemini-2.5-flash", "text", daily_limit=250),
    "groq_llama": AIProvider("groq_llama", "llama-3.3-70b", "text", daily_limit=1000),
    "cloudflare_llama": AIProvider("cloudflare_llama", "llama-3.1-8b", "text", daily_limit=10000),
    "cerebras_qwen": AIProvider("cerebras_qwen", "qwen-3-32b", "text", daily_limit=1000),
    "mistral_large": AIProvider("mistral_large", "mistral-large", "text", daily_limit=500),
}

IMAGE_PROVIDERS: dict[str, AIProvider] = {
    "cloudflare_flux": AIProvider("cloudflare_flux", "flux-1-schnell", "image", daily_limit=230),
    "playground_ai": AIProvider("playground_ai", "playground-v2", "image", daily_limit=500),
    "leonardo_ai": AIProvider("leonardo_ai", "leonardo-v2", "image", daily_limit=150),
    "huggingface_sd": AIProvider("huggingface_sd", "stable-diffusion-xl", "image", daily_limit=200),
}

# ── Failover Chains per Task ──────────────────────────────────────────

TASK_CHAINS: dict[str, list[str]] = {
    "research": ["gemini_pro", "gemini_flash", "groq_llama", "mistral_large"],
    "create": ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen"],
    "ceo_review": ["gemini_pro", "groq_llama", "mistral_large", "cerebras_qwen"],
    "captions": ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen"],
    "niche_finding": ["gemini_pro", "gemini_flash", "groq_llama", "mistral_large"],
    "trend_prediction": ["gemini_pro", "groq_llama", "mistral_large", "cerebras_qwen"],
}

IMAGE_CHAIN: list[str] = [
    "cloudflare_flux", "playground_ai", "leonardo_ai", "huggingface_sd"
]


def _get_api_key(provider_name: str) -> str:
    """Get the API key for a provider from environment variables."""
    key_map = {
        "gemini_pro": "GEMINI_API_KEY",
        "gemini_flash": "GEMINI_API_KEY",
        "groq_llama": "GROQ_API_KEY",
        "cloudflare_llama": "CLOUDFLARE_API_TOKEN",
        "cerebras_qwen": "CEREBRAS_API_KEY",
        "mistral_large": "MISTRAL_API_KEY",
        "cloudflare_flux": "CLOUDFLARE_API_TOKEN",
    }
    env_var = key_map.get(provider_name, "")
    return os.environ.get(env_var, "")


async def call_text_with_failover(task: str, prompt: str) -> dict:
    """Try each provider in the chain for a text generation task.

    Args:
        task: Task type key from TASK_CHAINS (research, create, ceo_review, captions, etc.)
        prompt: The text prompt to send to the AI.

    Returns:
        dict with keys: success (bool), provider (str), result (str), message (str)
    """
    chain = TASK_CHAINS.get(task, TASK_CHAINS["create"])
    errors = []

    for provider_name in chain:
        provider = TEXT_PROVIDERS.get(provider_name)
        if provider is None:
            continue
        if not provider.is_available:
            logger.info("Provider %s not available, skipping", provider_name)
            continue

        api_key = _get_api_key(provider_name)
        if not api_key or api_key.startswith("your_"):
            logger.info("No API key for %s, skipping", provider_name)
            continue

        try:
            # Placeholder: actual API call would go here
            # For now, record success and return a simulated response
            provider.record_success()
            return {
                "success": True,
                "provider": provider_name,
                "model": provider.model,
                "result": f"[AI response from {provider.model}] — API integration pending",
                "message": f"Generated by {provider_name}",
            }
        except Exception as e:
            error_msg = str(e)
            provider.record_failure(error_msg)
            errors.append(f"{provider_name}: {error_msg}")
            logger.warning("Provider %s failed: %s, trying next...", provider_name, error_msg)
            continue

    return {
        "success": False,
        "provider": None,
        "model": None,
        "result": None,
        "message": f"All providers exhausted for task '{task}'. Errors: {'; '.join(errors) if errors else 'No configured API keys'}. Try again in 1 hour.",
    }


async def call_image_with_failover(prompt: str) -> dict:
    """Try each image provider in chain order.

    Args:
        prompt: The image generation prompt.

    Returns:
        dict with keys: success (bool), provider (str), image_url (str), message (str)
    """
    errors = []

    for provider_name in IMAGE_CHAIN:
        provider = IMAGE_PROVIDERS.get(provider_name)
        if provider is None:
            continue
        if not provider.is_available:
            logger.info("Image provider %s not available, skipping", provider_name)
            continue

        try:
            # Placeholder: actual image generation API call would go here
            provider.record_success()
            return {
                "success": True,
                "provider": provider_name,
                "model": provider.model,
                "image_url": f"/api/images/generated_{provider_name}.png",
                "message": f"Image generated by {provider_name}",
            }
        except Exception as e:
            error_msg = str(e)
            provider.record_failure(error_msg)
            errors.append(f"{provider_name}: {error_msg}")
            logger.warning("Image provider %s failed: %s, trying next...", provider_name, error_msg)
            continue

    return {
        "success": False,
        "provider": None,
        "model": None,
        "image_url": None,
        "message": f"All image providers exhausted. Errors: {'; '.join(errors) if errors else 'No configured API keys'}. Try again in 1 hour.",
    }


def get_all_provider_statuses() -> list[dict]:
    """Get status of all AI providers."""
    statuses = []
    for name, p in {**TEXT_PROVIDERS, **IMAGE_PROVIDERS}.items():
        statuses.append({
            "name": p.name,
            "model": p.model,
            "type": p.provider_type,
            "status": p.status,
            "requests_today": p.requests_today,
            "daily_limit": p.daily_limit,
            "available": p.is_available,
            "last_used": p.last_used,
            "last_error": p.last_error,
        })
    return statuses


def reset_all_daily_limits():
    """Reset daily request counters for all providers."""
    for p in TEXT_PROVIDERS.values():
        p.requests_today = 0
        p.status = "active"
        p.last_error = ""
    for p in IMAGE_PROVIDERS.values():
        p.requests_today = 0
        p.status = "active"
        p.last_error = ""

    with get_db() as conn:
        conn.execute(
            "UPDATE ai_status SET requests_today = 0, status = 'active', last_error = ''"
        )


def load_provider_statuses_from_db():
    """Load provider statuses from the database on startup."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM ai_status").fetchall()

    for row in rows:
        provider_name = row["provider"]
        if provider_name in TEXT_PROVIDERS:
            p = TEXT_PROVIDERS[provider_name]
        elif provider_name in IMAGE_PROVIDERS:
            p = IMAGE_PROVIDERS[provider_name]
        else:
            continue

        p.status = row["status"]
        p.requests_today = row["requests_today"]
        p.daily_limit = row["daily_limit"]
        p.last_used = row["last_used"] or ""
        p.last_error = row["last_error"] or ""
