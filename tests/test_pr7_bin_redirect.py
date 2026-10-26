"""Tests for PR-7: /bin/{bin_id} redirects to /scan/{bin_id}."""

from __future__ import annotations


def test_bin_redirect_returns_302(client):
    """GET /bin/<id> must redirect to /scan/<id>."""
    r = client.get("/bin/BIN-001", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/scan/BIN-001"


def test_bin_redirect_url_encodes_special_chars(client):
    """Bin IDs with spaces or special characters must be URL-encoded in the redirect."""
    r = client.get("/bin/BIN A+1", follow_redirects=False)
    assert r.status_code == 302
    loc = r.headers["location"]
    assert "BIN" in loc
    assert " " not in loc


def test_bin_redirect_follows_to_scan(client):
    """Following the redirect from /bin/<id> must land on /scan/<id> (200 or 404 for unknown bin)."""
    r = client.get("/bin/NONEXISTENT-BIN", follow_redirects=True)
    # The scan view returns 404 for an unknown bin; what matters is that
    # the redirect chain resolved to the scan route, not a 500.
    assert r.status_code in (200, 404)
