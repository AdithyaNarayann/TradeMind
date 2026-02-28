"""
Translation proxy route — proxies Gemini translation requests
through the backend so the API key is never exposed to the frontend.

POST /api/v1/translate  → translate text via Gemini
"""
import os
import httpx
import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List

from .auth_routes import get_current_user
from ..middleware import limiter

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/translate", tags=["Translation"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash-lite:generateContent"
)


class TranslateRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, max_length=500)
    target_language: str = Field(..., min_length=1, max_length=50)
    target_language_name: str = Field(..., min_length=1, max_length=100)


class TranslateResponse(BaseModel):
    translations: List[str]


@router.post("", response_model=TranslateResponse)
@limiter.limit("10/minute")
async def translate_text(
    request,           # needed for rate limiter
    body: TranslateRequest,
    user=Depends(get_current_user),
):
    """Proxy translation request to Gemini so API key stays server-side."""
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Translation service not configured (GEMINI_API_KEY missing)",
        )

    # Build numbered list for translation
    numbered = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(body.texts))

    prompt = (
        f"You are a professional translator. Translate ALL of the following "
        f"{len(body.texts)} texts from English to {body.target_language_name}.\n\n"
        f"RULES:\n"
        f"1. Return EXACTLY {len(body.texts)} translations, one per line\n"
        f"2. Each line MUST start with the number in brackets like [1], [2], etc.\n"
        f"3. Preserve ALL special characters and placeholders exactly.\n"
        f"4. Maintain the same tone and formality.\n\n"
        f"Texts:\n{numbered}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4096},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract text content from Gemini response
        raw = data["candidates"][0]["content"]["parts"][0]["text"]

        # Parse numbered translations
        import re
        translations = []
        for line in raw.strip().split("\n"):
            m = re.match(r"\[(\d+)\]\s*(.*)", line.strip())
            if m:
                translations.append(m.group(2))

        # If parsing failed, fall back to returning original texts
        if len(translations) != len(body.texts):
            logger.warning(
                "translation_parse_mismatch",
                expected=len(body.texts),
                got=len(translations),
            )
            # Pad or truncate
            while len(translations) < len(body.texts):
                translations.append(body.texts[len(translations)])
            translations = translations[: len(body.texts)]

        return TranslateResponse(translations=translations)

    except httpx.HTTPStatusError as e:
        logger.error("gemini_api_error", status=e.response.status_code)
        raise HTTPException(status_code=502, detail="Translation service error")
    except Exception as e:
        logger.error("translation_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Translation failed")
