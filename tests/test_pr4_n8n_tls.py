"""Tests for PR-4: n8n webhook TLS verification."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def test_n8n_tls_verify_default_is_true(monkeypatch):
    """Without N8N_CA_BUNDLE set, verify must be True (not False)."""
    import app as app_module

    monkeypatch.delenv("N8N_CA_BUNDLE", raising=False)
    monkeypatch.setattr(app_module, "N8N_WEBHOOK_URL", "https://n8n.example.com/webhook/test")

    with patch("app.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        app_module.trigger_n8n_sync("BIN-T1", "Widget", "tools", 1, item_id=42)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["verify"] is True, f"expected verify=True, got {kwargs['verify']!r}"


def test_n8n_tls_verify_uses_ca_bundle(monkeypatch, tmp_path):
    """When N8N_CA_BUNDLE is set to a path, verify must use that path."""
    import app as app_module

    ca_path = str(tmp_path / "ca.crt")
    monkeypatch.setenv("N8N_CA_BUNDLE", ca_path)
    monkeypatch.setattr(app_module, "N8N_WEBHOOK_URL", "https://n8n.example.com/webhook/test")

    with patch("app.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        app_module.trigger_n8n_sync("BIN-T2", "Wrench", "tools", 2, item_id=99)
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["verify"] == ca_path, f"expected verify={ca_path!r}, got {kwargs['verify']!r}"


def test_n8n_no_request_when_url_unset(monkeypatch):
    """trigger_n8n_sync must be a no-op when N8N_WEBHOOK_URL is blank."""
    import app as app_module

    monkeypatch.setattr(app_module, "N8N_WEBHOOK_URL", "")

    with patch("app.requests.post") as mock_post:
        app_module.trigger_n8n_sync("BIN-T3", "Hammer", "tools", 1)
        mock_post.assert_not_called()
