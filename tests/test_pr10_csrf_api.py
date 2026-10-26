"""Tests for PR-10: remove blanket /api/ CSRF exemption.

Session-authed /api/ POST routes must reject requests that omit a valid CSRF
token; the /api/sync-row webhook (secret-auth) must remain exempt.
"""

from __future__ import annotations

import json
from base64 import b64encode

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION_CSRF = "test-csrf-token-pr10"


def _make_admin_client_no_csrf(app_module):
    """Return a TestClient with an admin session but WITHOUT an X-CSRF-Token default header."""
    from fastapi.testclient import TestClient
    from itsdangerous import TimestampSigner

    signer = TimestampSigner(app_module.AUTH_SECRET_KEY)
    session_data = {
        "user": {
            "sub": "test-admin-pr10",
            "email": "admin@example.com",
            "name": "Test Admin",
            "groups": ["admins"],
        },
        "is_admin": True,
        "csrf_token": _SESSION_CSRF,
    }
    cookie_val = signer.sign(b64encode(json.dumps(session_data).encode("utf-8"))).decode("utf-8")
    c = TestClient(app_module.app, raise_server_exceptions=True)
    c.__enter__()
    c.cookies.set("session", cookie_val)
    # Deliberately do NOT set c.headers["X-CSRF-Token"]
    return c


@pytest.fixture
def admin_no_csrf():
    """Admin session without a default X-CSRF-Token header."""
    import app as app_module

    c = _make_admin_client_no_csrf(app_module)
    yield c
    c.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# CSRF is now enforced on session-authed /api/ POST routes
# ---------------------------------------------------------------------------


def test_bulk_tag_rejects_missing_csrf(admin_no_csrf):
    """POST /api/bulk-tag without CSRF header must return 403."""
    r = admin_no_csrf.post("/api/bulk-tag", json={"item_ids": [], "tags": ["x"]})
    assert r.status_code == 403, f"expected 403 without CSRF, got {r.status_code}: {r.text}"


def test_bulk_tag_rejects_wrong_csrf(admin_no_csrf):
    """POST /api/bulk-tag with a wrong CSRF token must return 403."""
    r = admin_no_csrf.post(
        "/api/bulk-tag",
        json={"item_ids": [], "tags": ["x"]},
        headers={"X-CSRF-Token": "definitely-wrong-token"},
    )
    assert r.status_code == 403, f"expected 403 with wrong CSRF, got {r.status_code}: {r.text}"


def test_bulk_tag_accepts_valid_csrf(admin_no_csrf):
    """POST /api/bulk-tag with a correct CSRF token must not be blocked by CSRF middleware."""
    r = admin_no_csrf.post(
        "/api/bulk-tag",
        json={"item_ids": [], "tags": ["x"]},
        headers={"X-CSRF-Token": _SESSION_CSRF},
    )
    # Route logic returns 400 (no valid item_ids/tags) — the point is it's not 403 from CSRF.
    assert r.status_code != 403, f"CSRF middleware rejected a valid token (got {r.status_code})"


def test_move_items_rejects_missing_csrf(admin_no_csrf):
    """POST /api/move-items without CSRF header must return 403."""
    r = admin_no_csrf.post("/api/move-items", json={"item_ids": [1], "bin_id": "X"})
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_tag_colors_post_rejects_missing_csrf(admin_no_csrf):
    """POST /api/tag-colors without CSRF header must return 403."""
    r = admin_no_csrf.post("/api/tag-colors", json={"tag": "t", "hex": "#fff"})
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_backup_retention_post_rejects_missing_csrf(admin_no_csrf):
    """POST /api/backup/retention without CSRF header must return 403."""
    r = admin_no_csrf.post("/api/backup/retention")
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_import_csv_rejects_missing_csrf(admin_no_csrf):
    """POST /api/import-csv without CSRF header must return 403."""
    import io

    csv_data = b"bin_id,name,category,quantity\n"
    r = admin_no_csrf.post(
        "/api/import-csv",
        files={"file": ("data.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


# ---------------------------------------------------------------------------
# /api/sync-row webhook must remain CSRF-exempt
# ---------------------------------------------------------------------------


def test_sync_row_still_exempt_from_csrf(client):
    """/api/sync-row must succeed with its webhook secret and no CSRF token."""
    r = client.post(
        "/api/sync-row?N8N_WEBHOOK_SECRET=test-webhook-secret",
        json={"bin_id": "BIN-CSRF1", "name": "Widget", "category": "parts", "quantity": 1},
        # No X-CSRF-Token header — still must work because path is in _CSRF_EXEMPT_PATHS
    )
    assert r.status_code == 200, f"sync-row should not require CSRF, got {r.status_code}: {r.text}"


def test_sync_conflicts_resolve_rejects_missing_csrf(admin_no_csrf):
    """POST /api/sync-conflicts/.../resolve without CSRF header must return 403."""
    r = admin_no_csrf.post("/api/sync-conflicts/1/resolve")
    assert r.status_code == 403, f"expected 403, got {r.status_code}"
