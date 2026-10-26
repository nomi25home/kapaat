"""Tests for PR-11: add require_read to GET /api/tag-colors and GET /photos/.

When SERVICE_API_KEY is unset (open mode, the default test environment),
both routes remain accessible — require_read is a no-op without a key.
When SERVICE_API_KEY is set, anonymous requests must be denied.
"""

from __future__ import annotations

import importlib
import os

from fastapi.testclient import TestClient


def _reload_with_key(key: str):
    """Reload app with SERVICE_API_KEY set; return (app_module, client)."""
    os.environ["SERVICE_API_KEY"] = key
    os.environ["SERVICE_API_SCOPES"] = "read,write"
    import app as app_module

    importlib.reload(app_module)
    return app_module


def _cleanup(app_module):
    os.environ.pop("SERVICE_API_KEY", None)
    os.environ.pop("SERVICE_API_SCOPES", None)
    importlib.reload(app_module)


# ---------------------------------------------------------------------------
# GET /api/tag-colors
# ---------------------------------------------------------------------------


def test_tag_colors_open_when_no_api_key(client):
    """GET /api/tag-colors is accessible in open mode (no SERVICE_API_KEY)."""
    r = client.get("/api/tag-colors")
    assert r.status_code == 200


def test_tag_colors_denied_anonymous_when_api_key_set():
    """GET /api/tag-colors denies anonymous requests when SERVICE_API_KEY is configured."""
    import app as app_module

    _reload_with_key("pr11-test-key")
    try:
        with TestClient(app_module.app) as c:
            r = c.get("/api/tag-colors")
            assert r.status_code == 403, f"expected 403, got {r.status_code}"
    finally:
        _cleanup(app_module)


def test_tag_colors_allowed_with_valid_key():
    """GET /api/tag-colors succeeds with a valid Bearer token when SERVICE_API_KEY is set."""
    import app as app_module

    _reload_with_key("pr11-test-key-valid")
    try:
        with TestClient(app_module.app) as c:
            r = c.get("/api/tag-colors", headers={"Authorization": "Bearer pr11-test-key-valid"})
            assert r.status_code == 200, f"expected 200, got {r.status_code}"
    finally:
        _cleanup(app_module)


# ---------------------------------------------------------------------------
# GET /photos/{filename}
# ---------------------------------------------------------------------------


def test_photos_open_when_no_api_key(client):
    """GET /photos/ is accessible in open mode; missing file returns 404 not 403."""
    r = client.get("/photos/nonexistent-pr11.jpg")
    # Route is reached (require_read passes in open mode); file not found → 404
    assert r.status_code == 404, f"expected 404, got {r.status_code}"


def test_photos_denied_anonymous_when_api_key_set():
    """GET /photos/ denies anonymous requests when SERVICE_API_KEY is configured."""
    import app as app_module

    _reload_with_key("pr11-photo-key")
    try:
        with TestClient(app_module.app) as c:
            r = c.get("/photos/any-photo.jpg")
            assert r.status_code == 403, f"expected 403, got {r.status_code}"
    finally:
        _cleanup(app_module)
