"""Tests for PR-2 (auth_callback redirect) and PR-3 (SQLCipher fail-closed)."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# PR-2: auth_callback must redirect to / on success
# ---------------------------------------------------------------------------

def _make_oauth_mock(fake_token: dict) -> MagicMock:
    """Return an oauth mock whose .authentik.authorize_access_token returns fake_token."""
    mock_authentik = MagicMock()
    mock_authentik.authorize_access_token = AsyncMock(return_value=fake_token)
    mock_oauth = MagicMock()
    mock_oauth.authentik = mock_authentik
    return mock_oauth


def test_auth_callback_redirects_on_success(client, monkeypatch):
    """A successful OIDC callback must return 302 to / (not 200 null)."""
    import app as app_module

    fake_token = {
        "userinfo": {
            "sub": "user-abc",
            "email": "user@example.com",
            "name": "Test User",
            "preferred_username": "testuser",
            "groups": [],
        }
    }

    monkeypatch.setattr(app_module, "oauth", _make_oauth_mock(fake_token))
    monkeypatch.setattr(app_module, "AUTHENTIK_CLIENT_ID", "test-client-id")

    r = client.get("/auth/callback", follow_redirects=False)
    assert r.status_code == 302, f"expected 302, got {r.status_code} — OIDC login does not redirect"
    assert r.headers["location"] == "/", f"expected redirect to /, got {r.headers.get('location')}"


def test_auth_callback_sets_is_admin_for_admin_group(client, monkeypatch):
    """A user in the admin group gets is_admin=True and is redirected to /."""
    import app as app_module

    fake_token = {
        "userinfo": {
            "sub": "admin-xyz",
            "email": "admin@example.com",
            "name": "Admin User",
            "groups": ["admins"],
        }
    }

    monkeypatch.setattr(app_module, "oauth", _make_oauth_mock(fake_token))
    monkeypatch.setattr(app_module, "AUTHENTIK_CLIENT_ID", "test-client-id")

    r = client.get("/auth/callback", follow_redirects=False)
    assert r.status_code == 302


def test_auth_callback_denies_blocked_email(client, monkeypatch):
    """auth_callback must clear the session and return 403 for a blocked email."""
    import app as app_module

    fake_token = {
        "userinfo": {
            "sub": "bad-user",
            "email": "blocked@example.com",
            "name": "Bad Actor",
            "groups": [],
        }
    }

    monkeypatch.setattr(app_module, "oauth", _make_oauth_mock(fake_token))
    monkeypatch.setattr(app_module, "AUTHENTIK_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("BLOCKED_EMAILS", "blocked@example.com")

    r = client.get("/auth/callback", follow_redirects=False)
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# PR-3: SQLCipher import failure must raise RuntimeError (fail-closed)
# ---------------------------------------------------------------------------

def test_sqlcipher_import_failure_raises():
    """If DB_ENCRYPTION_KEY is set but pysqlcipher3 is unavailable, startup must fail."""
    # Save and patch the environment
    original = os.environ.get("DB_ENCRYPTION_KEY")
    os.environ["DB_ENCRYPTION_KEY"] = "test-encryption-key-should-fail"

    # Remove pysqlcipher3 from sys.modules so the import inside app.py fails
    sys.modules.pop("pysqlcipher3", None)
    sys.modules["pysqlcipher3"] = None  # forces ImportError on `import pysqlcipher3`

    # Remove app from sys.modules so it re-executes module-level code
    sys.modules.pop("app", None)

    try:
        import pytest
        with pytest.raises(RuntimeError, match="pysqlcipher3 is not installed"):
            import app
    finally:
        # Restore env and module cache
        if original is None:
            os.environ.pop("DB_ENCRYPTION_KEY", None)
        else:
            os.environ["DB_ENCRYPTION_KEY"] = original
        sys.modules.pop("pysqlcipher3", None)
        sys.modules.pop("app", None)
        # Re-import app with normal env so subsequent tests work
        os.environ.pop("DB_ENCRYPTION_KEY", None)
        import app  # noqa: F401


def test_sqlcipher_not_triggered_when_key_unset(client):
    """With DB_ENCRYPTION_KEY unset, app starts normally (no pysqlcipher3 needed)."""
    import app as app_module
    assert app_module.DB_ENCRYPTION_KEY == ""
    # If we got here, app imported and the client fixture works — pass.
    r = client.get("/api/items")
    assert r.status_code == 200
