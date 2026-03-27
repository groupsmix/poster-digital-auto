"""AI Failover System for AI Product Factory.

Provides automatic failover between free AI providers for text and image generation.
Each task has a chain of providers - if one fails or hits rate limits, it tries the next.
Real API integrations for Gemini, Groq, Cloudflare Workers AI, Cerebras, and Mistral.
"""

import base64
import logging
import os
import uuid
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.database import get_db

logger = logging.getLogger(__name__)

IMAGES_DIR = Path(__file__).parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

HTTP_TIMEOUT = 120.0


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


# -- Provider Registry --

TEXT_PROVIDERS: dict[str, AIProvider] = {
    "gemini_pro": AIProvider("gemini_pro", "gemini-2.5-pro", "text", daily_limit=100),
    "gemini_flash": AIProvider("gemini_flash", "gemini-2.5-flash", "text", daily_limit=250),
    "groq_llama": AIProvider(
        "groq_llama", "llama-3.3-70b-versatile", "text", daily_limit=1000,
    ),
    "cloudflare_llama": AIProvider(
        "cloudflare_llama", "@cf/meta/llama-3.1-8b-instruct", "text", daily_limit=10000,
    ),
    "cerebras_qwen": AIProvider("cerebras_qwen", "qwen-3-32b", "text", daily_limit=1000),
    "mistral_large": AIProvider(
        "mistral_large", "mistral-large-latest", "text", daily_limit=500,
    ),
}

IMAGE_PROVIDERS: dict[str, AIProvider] = {
    "cloudflare_flux": AIProvider(
        "cloudflare_flux", "@cf/black-forest-labs/flux-1-schnell", "image", daily_limit=230,
    ),
    "huggingface_sd": AIProvider(
        "huggingface_sd", "stabilityai/stable-diffusion-xl-base-1.0", "image",
        daily_limit=200,
    ),
}

# -- Failover Chains per Task --

TASK_CHAINS: dict[str, list[str]] = {
    "research": ["gemini_pro", "gemini_flash", "groq_llama", "mistral_large"],
    "create": ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen"],
    "ceo_review": ["gemini_pro", "groq_llama", "mistral_large", "cerebras_qwen"],
    "captions": ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen"],
    "niche_finding": ["gemini_pro", "gemini_flash", "groq_llama", "mistral_large"],
    "trend_prediction": ["gemini_pro", "groq_llama", "mistral_large", "cerebras_qwen"],
    "remix": ["gemini_pro", "gemini_flash", "groq_llama", "mistral_large"],
}

IMAGE_CHAIN: list[str] = ["cloudflare_flux", "huggingface_sd"]


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
        "huggingface_sd": "HUGGINGFACE_API_TOKEN",
    }
    env_var = key_map.get(provider_name, "")
    return os.environ.get(env_var, "")


def _get_cloudflare_account_id() -> str:
    """Get Cloudflare account ID from environment."""
    return os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")


# -- Real API Call Implementations --


async def _call_gemini(model_name: str, api_key: str, prompt: str) -> str:
    """Call Google Gemini API (AI Studio REST API)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        response.raise_for_status()
        data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise Exception("No candidates in Gemini response")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise Exception("No parts in Gemini response candidate")
    return parts[0].get("text", "")


async def _call_groq(api_key: str, prompt: str) -> str:
    """Call Groq API (OpenAI-compatible)."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise Exception("No choices in Groq response")
    return choices[0].get("message", {}).get("content", "")


async def _call_cloudflare_text(api_token: str, prompt: str) -> str:
    """Call Cloudflare Workers AI text generation."""
    account_id = _get_cloudflare_account_id()
    if not account_id:
        raise Exception("CLOUDFLARE_ACCOUNT_ID not configured")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {"messages": [{"role": "user", "content": prompt}], "max_tokens": 4096}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        response.raise_for_status()
        data = response.json()
    result = data.get("result", {})
    return result.get("response", "")


async def _call_cerebras(api_key: str, prompt: str) -> str:
    """Call Cerebras API (OpenAI-compatible)."""
    url = "https://api.cerebras.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "qwen-3-32b",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise Exception("No choices in Cerebras response")
    return choices[0].get("message", {}).get("content", "")


async def _call_mistral(api_key: str, prompt: str) -> str:
    """Call Mistral AI API."""
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        response.raise_for_status()
        data = response.json()
    choices = data.get("choices", [])
    if not choices:
        raise Exception("No choices in Mistral response")
    return choices[0].get("message", {}).get("content", "")


async def _call_text_provider(provider_name: str, api_key: str, prompt: str) -> str:
    """Route to the correct text provider API."""
    if provider_name == "gemini_pro":
        return await _call_gemini("gemini-2.5-pro", api_key, prompt)
    elif provider_name == "gemini_flash":
        return await _call_gemini("gemini-2.5-flash", api_key, prompt)
    elif provider_name == "groq_llama":
        return await _call_groq(api_key, prompt)
    elif provider_name == "cloudflare_llama":
        return await _call_cloudflare_text(api_key, prompt)
    elif provider_name == "cerebras_qwen":
        return await _call_cerebras(api_key, prompt)
    elif provider_name == "mistral_large":
        return await _call_mistral(api_key, prompt)
    else:
        raise Exception(f"Unknown text provider: {provider_name}")


# -- Image Generation API Calls --


async def _call_cloudflare_image(api_token: str, prompt: str) -> bytes:
    """Call Cloudflare Workers AI FLUX image generation."""
    account_id = _get_cloudflare_account_id()
    if not account_id:
        raise Exception("CLOUDFLARE_ACCOUNT_ID not configured")
    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/@cf/black-forest-labs/flux-1-schnell"
    )
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {"prompt": prompt}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "image" in content_type:
            return response.content
        data = response.json()
        result = data.get("result", {})
        image_b64 = result.get("image", "")
        if not image_b64:
            raise Exception("No image in Cloudflare FLUX response")
        return base64.b64decode(image_b64)


async def _call_huggingface_image(api_token: str, prompt: str) -> bytes:
    """Call HuggingFace Inference API for image generation."""
    url = (
        "https://api-inference.huggingface.co/models/"
        "stabilityai/stable-diffusion-xl-base-1.0"
    )
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    payload = {"inputs": prompt}
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("429 Rate limit exceeded")
        if response.status_code == 503:
            raise Exception("Model is loading, try again later")
        response.raise_for_status()
        return response.content


async def _call_image_provider(provider_name: str, api_key: str, prompt: str) -> bytes:
    """Route to the correct image provider API."""
    if provider_name == "cloudflare_flux":
        return await _call_cloudflare_image(api_key, prompt)
    elif provider_name == "huggingface_sd":
        return await _call_huggingface_image(api_key, prompt)
    else:
        raise Exception(f"Unknown image provider: {provider_name}")


# -- Main Failover Functions --


async def call_text_with_failover(task: str, prompt: str) -> dict:
    """Try each provider in the chain for a text generation task.

    Args:
        task: Task type key from TASK_CHAINS
        prompt: The text prompt to send to the AI.

    Returns:
        dict with keys: success (bool), provider (str), result (str), message (str)
    """
    chain = TASK_CHAINS.get(task, TASK_CHAINS["create"])
    errors: list[str] = []

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
            result_text = await _call_text_provider(provider_name, api_key, prompt)
            provider.record_success()
            return {
                "success": True,
                "provider": provider_name,
                "model": provider.model,
                "result": result_text,
                "message": f"Generated by {provider_name}",
            }
        except Exception as e:
            error_msg = str(e)
            provider.record_failure(error_msg)
            errors.append(f"{provider_name}: {error_msg}")
            logger.warning(
                "Provider %s failed: %s, trying next...", provider_name, error_msg,
            )
            continue

    err_str = "; ".join(errors) if errors else "No configured API keys"
    return {
        "success": False,
        "provider": None,
        "model": None,
        "result": None,
        "message": f"All providers exhausted for task '{task}'. Errors: {err_str}. Try again in 1 hour.",
    }


async def call_image_with_failover(prompt: str) -> dict:
    """Try each image provider in chain order.

    Args:
        prompt: The image generation prompt.

    Returns:
        dict with keys: success, provider, image_url, local_path, message
    """
    errors: list[str] = []

    for provider_name in IMAGE_CHAIN:
        provider = IMAGE_PROVIDERS.get(provider_name)
        if provider is None:
            continue
        if not provider.is_available:
            logger.info("Image provider %s not available, skipping", provider_name)
            continue

        api_key = _get_api_key(provider_name)
        if not api_key or api_key.startswith("your_"):
            logger.info("No API key for %s, skipping", provider_name)
            continue

        try:
            image_bytes = await _call_image_provider(provider_name, api_key, prompt)
            filename = f"{uuid.uuid4().hex}.png"
            file_path = IMAGES_DIR / filename
            file_path.write_bytes(image_bytes)

            provider.record_success()
            return {
                "success": True,
                "provider": provider_name,
                "model": provider.model,
                "image_url": f"/api/images/{filename}",
                "local_path": str(file_path),
                "message": f"Image generated by {provider_name}",
            }
        except Exception as e:
            error_msg = str(e)
            provider.record_failure(error_msg)
            errors.append(f"{provider_name}: {error_msg}")
            logger.warning(
                "Image provider %s failed: %s, trying next...", provider_name, error_msg,
            )
            continue

    err_str = "; ".join(errors) if errors else "No configured API keys"
    return {
        "success": False,
        "provider": None,
        "model": None,
        "image_url": None,
        "local_path": None,
        "message": f"All image providers exhausted. Errors: {err_str}. Try again in 1 hour.",
    }


def get_all_provider_statuses() -> list[dict]:
    """Get status of all AI providers."""
    statuses = []
    for _name, p in {**TEXT_PROVIDERS, **IMAGE_PROVIDERS}.items():
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
