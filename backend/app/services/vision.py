import base64
import io
import json

import httpx
from fastapi import HTTPException
from PIL import Image, ImageOps

from ..config import get_settings

PROMPT = (
    "Identify this household/garage item from its photo for an inventory app. "
    "Respond with strict JSON only, no markdown fences, no extra text, matching exactly this shape: "
    '{"name": "short item name", "category": "one or two word category", '
    '"notes": "a short (under 15 words) plain description", "tags": ["lowercase", "keyword", "tags"]}. '
    "Use at most 4 tags. If unsure about a field, give your best guess rather than leaving it empty."
)


def detect_item(data: bytes) -> dict:
    s = get_settings()
    if not (s.vision_api_base and s.vision_api_key):
        raise HTTPException(503, "AI detection is not configured")
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((768, 768))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode()
    resp = httpx.post(
        f"{s.vision_api_base.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {s.vision_api_key}"},
        json={
            "model": s.vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    ],
                }
            ],
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
        },
        timeout=25,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    return {
        "name": str(parsed.get("name", "")).strip()[:200],
        "category": str(parsed.get("category", "")).strip()[:80],
        "notes": str(parsed.get("notes", "")).strip(),
        "tags": [str(t).strip().lower() for t in parsed.get("tags", []) if str(t).strip()][:4],
    }
