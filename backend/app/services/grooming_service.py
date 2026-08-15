"""Aviation-academy grooming check from punch selfies (vision AI + photo quality)."""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from typing import Any, Optional

import httpx
from PIL import Image, ImageStat

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GROOMING_SYSTEM = """You are the grooming inspector for Calibre Aviation Academy (cabin crew / aviation training).
Judge ONLY what is visible in this attendance selfie. Be reasonably strict on hair and facial grooming.

Check these points:
1. Face clearly visible (real person selfie, not blank / covered / someone else's photo of a poster)
2. Hair: neat, combed or styled for academy (fail if messy, uncombed, greasy-looking clumps, covering eyes heavily, or clearly unkempt)
3. Facial grooming: clean face; if facial hair is present it must look neatly trimmed (fail if scruffy / uneven stubble that looks ungroomed)
4. Overall: professional, tidy appearance suitable for an aviation academy punch

Do NOT fail solely for glasses, skin tone, gender presentation, religious head covering that is neat, or mild makeup.
DO fail for clearly messy hair, ungroomed facial hair, or obviously unprofessional / sloppy look.

Respond with ONLY compact JSON (no markdown):
{"ok":true|false,"notes":"one short sentence","issues":["hair"|"facial_grooming"|"appearance"|"photo_quality"]}
"""

# Prefer aliases that stay current; older pinned IDs (gemini-2.0-flash) return 404.
DEFAULT_GEMINI_MODELS = (
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-2.5-flash-lite",
)


def grooming_ai_status() -> dict[str, Any]:
    settings = get_settings()
    if settings.gemini_api_key:
        return {
            "ready": True,
            "provider": "gemini",
            "model": settings.grooming_vision_model or DEFAULT_GEMINI_MODELS[0],
        }
    if settings.openai_api_key:
        return {
            "ready": True,
            "provider": "openai",
            "model": settings.grooming_vision_model or "gpt-4o-mini",
        }
    return {"ready": False, "provider": None, "model": None}


def _quality_check(image_bytes: bytes) -> tuple[bool, str, Image.Image]:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return False, "Invalid selfie image", Image.new("RGB", (64, 64))

    w, h = img.size
    if w < 240 or h < 240:
        return False, "Selfie too small — hold phone closer and retake", img

    small = img.resize((64, 64))
    stat = ImageStat.Stat(small)
    mean = sum(stat.mean) / 3
    stddev = sum(stat.stddev) / 3

    if mean < 28:
        return False, "Selfie too dark — improve lighting and retake", img
    if mean > 245:
        return False, "Selfie overexposed — retake with less glare", img
    if stddev < 6:
        return False, "Selfie looks blank or blurry — face the camera and retake", img

    return True, "ok", img


def _jpeg_b64(img: Image.Image, max_side: int = 768) -> str:
    copy = img.copy()
    copy.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    copy.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _parse_vision_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {"ok": False, "notes": "Could not read grooming result — retake selfie", "issues": ["photo_quality"]}


def _extract_gemini_text(body: dict[str, Any]) -> str:
    """Pull text from candidates, including multi-part / thinking responses."""
    candidates = body.get("candidates") or []
    if not candidates:
        feedback = body.get("promptFeedback") or {}
        block = feedback.get("blockReason") or body.get("error", {}).get("message")
        raise RuntimeError(f"Gemini blocked or empty response{': ' + str(block) if block else ''}")

    cand = candidates[0] or {}
    finish = cand.get("finishReason")
    parts = (cand.get("content") or {}).get("parts") or []
    text = ""
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("text"):
            text += part["text"]
    if text.strip():
        return text
    if finish and finish not in {"STOP", "MAX_TOKENS"}:
        raise RuntimeError(f"Gemini finished with {finish}")
    raise RuntimeError("Gemini returned empty grooming response")


async def _call_gemini_once(img: Image.Image, api_key: str, model: str) -> dict[str, Any]:
    b64 = _jpeg_b64(img)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GROOMING_SYSTEM},
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64}},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(url, params={"key": api_key}, json=payload)
        if res.status_code >= 400:
            # Some keys prefer header auth
            res = await client.post(url, headers={"x-goog-api-key": api_key}, json=payload)
        if res.status_code >= 400:
            detail = ""
            try:
                detail = res.json().get("error", {}).get("message", res.text[:200])
            except Exception:
                detail = res.text[:200]
            raise RuntimeError(f"Gemini {res.status_code}: {detail}")
        body = res.json()
    return _parse_vision_json(_extract_gemini_text(body))


async def _call_gemini(img: Image.Image, api_key: str, model: str) -> dict[str, Any]:
    """Try preferred model, then known-good flash aliases on 404/unavailable."""
    tried: list[str] = []
    models: list[str] = []
    for m in (model, *DEFAULT_GEMINI_MODELS):
        if m and m not in models:
            models.append(m)

    last_err: Optional[Exception] = None
    for m in models:
        tried.append(m)
        try:
            return await _call_gemini_once(img, api_key, m)
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            # Fall through on missing/retired models; re-raise hard auth errors after all tries
            if "404" in msg or "no longer available" in msg or "not found" in msg or "empty" in msg:
                logger.warning("Gemini model %s failed: %s", m, exc)
                continue
            if "401" in msg or "403" in msg or "api key" in msg:
                raise
            logger.warning("Gemini model %s failed: %s", m, exc)
            continue
    raise RuntimeError(f"All Gemini models failed ({', '.join(tried)}): {last_err}")


async def _call_openai(img: Image.Image, api_key: str, model: str) -> dict[str, Any]:
    b64 = _jpeg_b64(img)
    payload = {
        "model": model,
        "temperature": 0.1,
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": GROOMING_SYSTEM},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        res.raise_for_status()
        body = res.json()
    text = body.get("choices", [{}])[0].get("message", {}).get("content", "")
    return _parse_vision_json(text)


async def analyze_grooming(image_bytes: bytes) -> tuple[Optional[bool], str, dict[str, Any]]:
    """
    Returns (ok, notes, details).
    ok=True/False from vision AI; ok=None if AI key is not configured (photo quality still checked).
    """
    ok_q, note_q, img = _quality_check(image_bytes)
    if not ok_q:
        return False, note_q, {"issues": ["photo_quality"], "provider": None}

    status = grooming_ai_status()
    if not status["ready"]:
        return (
            None,
            "Photo saved — set GEMINI_API_KEY (or OPENAI_API_KEY) to check hair & grooming",
            {"issues": [], "provider": None, "ai_ready": False},
        )

    settings = get_settings()
    provider = status["provider"]
    model = status["model"]
    try:
        if provider == "gemini":
            result = await _call_gemini(img, settings.gemini_api_key, model)
        else:
            result = await _call_openai(img, settings.openai_api_key, model)
    except Exception as exc:
        logger.exception("Grooming vision API failed")
        err = str(exc)[:180]
        return (
            None,
            f"Grooming AI temporarily unavailable — selfie saved for review. {err}",
            {"issues": [], "provider": provider, "error": err, "ai_ready": True},
        )

    ok_raw = result.get("ok")
    if isinstance(ok_raw, str):
        ok = ok_raw.strip().lower() in {"true", "1", "yes", "ok", "pass"}
    else:
        ok = bool(ok_raw)

    notes = str(result.get("notes") or ("Grooming OK" if ok else "Grooming standards not met")).strip()
    issues = result.get("issues") if isinstance(result.get("issues"), list) else []
    issues = [str(i) for i in issues][:6]

    if not ok and not issues:
        issues = ["appearance"]

    if not ok and issues:
        label_map = {
            "hair": "hair",
            "facial_grooming": "facial grooming",
            "appearance": "appearance",
            "photo_quality": "photo quality",
        }
        labels = [label_map.get(i, i) for i in issues]
        if labels and "hair" not in notes.lower() and "facial" not in notes.lower():
            notes = f"{notes} (issues: {', '.join(labels[:3])})"

    return ok, notes[:250], {"issues": issues, "provider": provider, "ai_ready": True, "raw": result, "model": model}
