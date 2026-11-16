import io

import httpx
import pytest
from PIL import Image

from app.config import get_settings
from app.services import vision


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def vision_configured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vision_api_base", "https://freellmapi.test/v1")
    monkeypatch.setattr(s, "vision_api_key", "test-key")
    return s


def test_describe_photo_returns_trimmed_content(vision_configured, monkeypatch):
    def fake_post(url, **kwargs):
        assert url == "https://freellmapi.test/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        req = httpx.Request("POST", url)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "  A red widget  "}}]}, request=req
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    assert vision.describe_photo(_jpeg_bytes()) == "A red widget"


def test_describe_photo_raises_on_upstream_error(vision_configured, monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda url, **kwargs: httpx.Response(500, request=httpx.Request("POST", url))
    )
    with pytest.raises(httpx.HTTPStatusError):
        vision.describe_photo(_jpeg_bytes())


def test_describe_photo_disabled_without_config(monkeypatch):
    from fastapi import HTTPException

    s = get_settings()
    monkeypatch.setattr(s, "vision_api_base", "")
    with pytest.raises(HTTPException):
        vision.describe_photo(_jpeg_bytes())
