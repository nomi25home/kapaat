import io

import httpx
import pytest
from fastapi import HTTPException
from PIL import Image

from app.config import get_settings
from app.services import vision


def _jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buf, "JPEG")
    return buf.getvalue()


def _response(url: str, body: dict) -> httpx.Response:
    return httpx.Response(200, json=body, request=httpx.Request("POST", url))


@pytest.fixture
def vision_configured(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vision_api_base", "https://freellmapi.test/v1")
    monkeypatch.setattr(s, "vision_api_key", "test-key")
    return s


def test_detect_item_parses_json_fields(vision_configured, monkeypatch):
    def fake_post(url, **kwargs):
        assert url == "https://freellmapi.test/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        content = '{"name": " Cordless drill ", "category": "Tools", "notes": "A red drill", "tags": ["Drill", " power-tool", ""]}'
        return _response(url, {"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    assert vision.detect_item(_jpeg_bytes()) == {
        "name": "Cordless drill",
        "category": "Tools",
        "notes": "A red drill",
        "tags": ["drill", "power-tool"],
    }


def test_detect_item_raises_on_upstream_error(vision_configured, monkeypatch):
    monkeypatch.setattr(
        httpx, "post", lambda url, **kwargs: httpx.Response(500, request=httpx.Request("POST", url))
    )
    with pytest.raises(httpx.HTTPStatusError):
        vision.detect_item(_jpeg_bytes())


def test_detect_item_raises_on_bad_json(vision_configured, monkeypatch):
    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: _response(url, {"choices": [{"message": {"content": "not json"}}]}),
    )
    with pytest.raises(ValueError):
        vision.detect_item(_jpeg_bytes())


def test_detect_item_disabled_without_config(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "vision_api_base", "")
    with pytest.raises(HTTPException):
        vision.detect_item(_jpeg_bytes())
