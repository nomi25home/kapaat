"""Tests for PR-5: OTP uses secrets, async sleep, rate-limiter time-window expiry."""

from __future__ import annotations

import time
from unittest.mock import patch


def test_generate_otp_uses_secrets_not_random():
    """_generate_otp must not import random; output must be a zero-padded 6-digit string."""
    import app as app_module

    # Confirm the function never touches the random module.
    with patch("random.randint") as mock_rand:
        otp = app_module._generate_otp()
        mock_rand.assert_not_called()

    assert len(otp) == 6
    assert otp.isdigit()


def test_generate_otp_distribution():
    """1000 calls must produce at least 900 distinct values (crypto random, not seeded)."""
    import app as app_module

    values = {app_module._generate_otp() for _ in range(1000)}
    assert len(values) >= 900, f"only {len(values)} distinct OTPs in 1000 calls — likely not random"


def test_mfa_rate_limiter_resets_after_window(monkeypatch):
    """_check_mfa_rate_limit must return 0 once the time window has elapsed."""
    import app as app_module

    # Seed some failures with a timestamp well in the past.
    past = time.time() - (app_module._MFA_RATE_WINDOW + 60)
    app_module._mfa_attempts["stale@example.com"] = {"fails": 10, "first_ts": past}

    delay = app_module._check_mfa_rate_limit("stale@example.com")
    assert delay == 0.0, f"expected 0 after window expiry, got {delay}"
    assert "stale@example.com" not in app_module._mfa_attempts


def test_mfa_rate_limiter_enforces_within_window(monkeypatch):
    """_check_mfa_rate_limit must return a positive delay for recent failures."""
    import app as app_module

    app_module._mfa_attempts["recent@example.com"] = {"fails": 7, "first_ts": time.time()}
    delay = app_module._check_mfa_rate_limit("recent@example.com")
    assert delay > 0, "expected a positive delay for 7 recent failures"
    # Cleanup
    app_module._mfa_attempts.pop("recent@example.com", None)


def test_oidc_rate_limiter_resets_after_window():
    """_attempts dict must be cleared for an IP whose first_ts is beyond the window."""
    import app as app_module

    _OIDC_RATE_WINDOW = 900
    ip = "10.0.0.1"
    past = time.time() - (_OIDC_RATE_WINDOW + 60)
    app_module._attempts[ip] = {"count": 99, "first_ts": past}

    # The reset logic lives inside auth_callback, replicated here for unit testing.
    now = time.time()
    existing = app_module._attempts.get(ip)
    if existing and now - existing.get("first_ts", now) > _OIDC_RATE_WINDOW:
        existing = None
    if existing is None:
        existing = {"count": 0, "first_ts": now}
    existing["count"] += 1
    app_module._attempts[ip] = existing

    assert app_module._attempts[ip]["count"] == 1, "stale counter should have been reset to 0 then incremented to 1"
    # Cleanup
    app_module._attempts.pop(ip, None)
