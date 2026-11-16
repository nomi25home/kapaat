import base64
import io

import httpx
from fastapi import HTTPException
from PIL import Image, ImageOps

from ..config import get_settings

PROMPT = (
    "Write a short (under 15 words) plain description of this household/garage "
    "item for an inventory app. No preamble, just the description."
)


def describe_photo(data: bytes) -> str:
    s = get_settings()
    if not (s.vision_api_base and s.vision_api_key):
        raise HTTPException(503, "AI description is not configured")
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
            "max_tokens": 60,
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
