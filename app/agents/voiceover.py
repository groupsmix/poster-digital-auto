"""AI Voice-Over Generator for AI Product Factory.

Generates a 30-second voice-over script from product description,
then converts to audio using TTS (ElevenLabs > Browser TTS fallback).
Returns audio file URL for playback and download.
"""

import json
import logging
import os
import uuid
from pathlib import Path

import httpx

from app.ai_failover import call_text_with_failover, TASK_CHAINS
from app.database import get_db

logger = logging.getLogger(__name__)

# Register voiceover task chain
TASK_CHAINS["voiceover"] = ["gemini_flash", "groq_llama", "cloudflare_llama", "cerebras_qwen"]

AUDIO_DIR = Path(__file__).parent.parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True)

HTTP_TIMEOUT = 60.0


def _build_script_prompt(product_name: str, product_description: str) -> str:
    """Build the AI prompt for generating a 30-second voice-over script."""
    return f"""You are an expert voice-over scriptwriter. Write a 30-second voice-over script for this product.

Product Name: {product_name}
Product Description: {product_description}

Requirements:
- The script should be 60-80 words (approximately 30 seconds when read aloud)
- Start with an attention-grabbing hook
- Highlight 2-3 key benefits
- End with a clear call-to-action
- Use conversational, engaging tone
- DO NOT include stage directions or speaker labels

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "script": "The full voice-over script text here",
  "duration_estimate": "30 seconds",
  "word_count": 70,
  "tone": "enthusiastic and professional"
}}"""


async def _call_elevenlabs_tts(text: str, api_key: str) -> bytes:
    """Call ElevenLabs Text-to-Speech API.

    Uses the free tier with the 'Rachel' voice.
    """
    voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
        },
    }

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code == 429:
            raise Exception("ElevenLabs rate limit exceeded")
        if response.status_code == 401:
            raise Exception("ElevenLabs API key invalid")
        response.raise_for_status()
        return response.content


async def generate_voiceover(product_id: int) -> dict:
    """Generate a voice-over for a product.

    1. AI writes a 30-second script
    2. TTS converts script to audio (ElevenLabs or fallback)
    3. Returns audio URL and script

    Args:
        product_id: The product ID.

    Returns:
        dict with success status, script, audio_url, and metadata.
    """
    # Fetch product details
    with get_db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if not product:
            return {"success": False, "message": "Product not found"}

        product_name = product["name"]
        product_description = product["brief"] or ""

        # Try to get richer description from variants
        if not product_description:
            variant = conn.execute(
                "SELECT description FROM product_variants WHERE product_id = ? LIMIT 1",
                (product_id,),
            ).fetchone()
            if variant:
                product_description = variant["description"] or ""

    if not product_description:
        product_description = f"A digital product called {product_name}"

    # Log pipeline start
    with get_db() as conn:
        conn.execute(
            "INSERT INTO pipeline_logs (product_id, agent, status, message) VALUES (?, ?, ?, ?)",
            (product_id, "voiceover", "running", "Generating voice-over script..."),
        )

    # Step 1: Generate script via AI
    prompt = _build_script_prompt(product_name, product_description)
    ai_result = await call_text_with_failover("voiceover", prompt)

    if not ai_result["success"]:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message) VALUES (?, ?, ?, ?, ?)",
                (product_id, "voiceover", ai_result.get("provider"), "error", ai_result["message"]),
            )
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
        script_data = json.loads(raw_text.strip())
    except json.JSONDecodeError:
        # If JSON parsing fails, use raw text as script
        script_data = {
            "script": raw_text.strip(),
            "duration_estimate": "30 seconds",
            "word_count": len(raw_text.split()),
            "tone": "professional",
        }

    script_text = script_data.get("script", raw_text.strip())

    # Step 2: TTS - try ElevenLabs, then fallback to script-only
    audio_url = ""
    tts_provider = "none"

    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if elevenlabs_key and not elevenlabs_key.startswith("your_"):
        try:
            audio_bytes = await _call_elevenlabs_tts(script_text, elevenlabs_key)
            filename = f"voiceover_{product_id}_{uuid.uuid4().hex[:8]}.mp3"
            file_path = AUDIO_DIR / filename
            file_path.write_bytes(audio_bytes)
            audio_url = f"/api/audio/{filename}"
            tts_provider = "elevenlabs"
            logger.info("Voice-over audio generated via ElevenLabs for product %d", product_id)
        except Exception as e:
            logger.warning("ElevenLabs TTS failed: %s, returning script only", e)

    # Log result
    with get_db() as conn:
        status = "success"
        message = f"Voice-over script generated ({script_data.get('word_count', '?')} words)"
        if audio_url:
            message += f", audio via {tts_provider}"
        else:
            message += ", use browser TTS for playback"

        conn.execute(
            "INSERT INTO pipeline_logs (product_id, agent, ai_provider, status, message) VALUES (?, ?, ?, ?, ?)",
            (product_id, "voiceover", ai_result.get("provider"), status, message),
        )

    return {
        "success": True,
        "product_id": product_id,
        "script": script_text,
        "duration_estimate": script_data.get("duration_estimate", "30 seconds"),
        "word_count": script_data.get("word_count", len(script_text.split())),
        "tone": script_data.get("tone", "professional"),
        "audio_url": audio_url,
        "tts_provider": tts_provider,
        "ai_provider": ai_result.get("provider"),
        "message": message,
    }
