import base64
import io
import json
import time

import httpx
from fastapi import HTTPException
from PIL import Image, ImageOps

from ..config import get_settings

_MAX_ATTEMPTS = 2
_RETRY_DELAY_S = 1.5

PROMPT = (
    "Identify this household/garage item from its photo for an inventory app. "
    "Respond with strict JSON only, no markdown fences, no extra text, with exactly these keys: "
    '{"name": <short item name>, "category": <one or two word category>, '
    '"notes": <a short (under 15 words) plain description>, "tags": [<up to 4 lowercase keyword tags>]}. '
    "The angle-bracket placeholders describe what each value should contain — "
    "replace every one of them with your own best guess about THIS photo. "
    "Never return a placeholder, example, or the schema itself as a value."
)

# If a model ignores the instructions and echoes the schema's placeholder wording
# back as a literal value, treat that as a failed detection rather than real data.
_PLACEHOLDER_MARKERS = ("short item name", "one or two word category", "plain description", "keyword tag")


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
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
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
            break
        except httpx.HTTPError:
            # A multi-provider router can be transiently slow or down; one retry
            # often lands on a different, healthy provider.
            if attempt == _MAX_ATTEMPTS:
                raise
            time.sleep(_RETRY_DELAY_S)
    content = resp.json()["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    result = {
        "name": str(parsed.get("name", "")).strip()[:200],
        "category": str(parsed.get("category", "")).strip()[:80],
        "notes": str(parsed.get("notes", "")).strip(),
        "tags": [str(t).strip().lower() for t in parsed.get("tags", []) if str(t).strip()][:4],
    }
    fields_text = " ".join([result["name"], result["category"], result["notes"], *result["tags"]]).lower()
    if any(marker in fields_text for marker in _PLACEHOLDER_MARKERS):
        raise ValueError("model echoed the prompt's schema instead of describing the photo")
    return result
