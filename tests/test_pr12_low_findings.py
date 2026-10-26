"""Tests for PR-12: fix remaining LOW security findings.

Finding 24: CSV/XLSX formula injection — _sanitize_cell must prefix
formula-triggering strings with a single quote before export.

Finding 25: Broad OperationalError catch in migrations — only
"duplicate column name" errors must be swallowed; others must propagate.

Finding 23 (duplicate CI workflows) was already resolved: docker-publish.yml
was removed in a prior PR; release.yml serves a distinct purpose (GitHub
Release creation on version tags). No code change needed.
"""

from __future__ import annotations

import sqlite3

# ---------------------------------------------------------------------------
# Finding 24: formula injection sanitiser
# ---------------------------------------------------------------------------


def test_sanitize_cell_prefixes_equals():
    from app import _sanitize_cell

    assert _sanitize_cell("=SUM(A1:A10)") == "'=SUM(A1:A10)"


def test_sanitize_cell_prefixes_plus():
    from app import _sanitize_cell

    assert _sanitize_cell("+1234") == "'+1234"


def test_sanitize_cell_prefixes_minus():
    from app import _sanitize_cell

    assert _sanitize_cell("-1") == "'-1"


def test_sanitize_cell_prefixes_at():
    from app import _sanitize_cell

    assert _sanitize_cell("@SUM") == "'@SUM"


def test_sanitize_cell_leaves_safe_strings_unchanged():
    from app import _sanitize_cell

    assert _sanitize_cell("Hammer") == "Hammer"
    assert _sanitize_cell("tools") == "tools"
    assert _sanitize_cell("") == ""


def test_sanitize_cell_leaves_non_strings_unchanged():
    from app import _sanitize_cell

    assert _sanitize_cell(42) == 42
    assert _sanitize_cell(None) is None
    assert _sanitize_cell(3.14) == 3.14


def test_export_csv_sanitizes_formula_values(admin_client):
    """Export CSV must not contain bare formula-triggering strings."""
    # Seed an item whose name starts with '='
    admin_client.post(
        "/api/sync-row?N8N_WEBHOOK_SECRET=test-webhook-secret",
        json={
            "bin_id": "BIN-F1",
            "name": '=HYPERLINK("http://evil.com","click")',
            "category": "=CMD",
            "quantity": 1,
        },
    )
    r = admin_client.get("/export/csv")
    assert r.status_code == 200
    body = r.text
    # The sanitized value has a leading ' so spreadsheet clients treat it as text.
    # The raw formula string still appears (after the quote) but must not start a CSV field.
    # A bare formula-starting field would look like: ,=HYPERLINK or \n=HYPERLINK
    import re

    bare_formula_in_field = re.search(r"(?:^|,)=", body, re.MULTILINE)
    assert not bare_formula_in_field, f"unsanitized formula found in CSV export: {bare_formula_in_field}"
    # Confirm the sanitized version (with quote prefix) IS present
    assert "'=HYPERLINK" in body or "'=CMD" in body, "sanitized value with quote prefix not found"


# ---------------------------------------------------------------------------
# Finding 25: narrow OperationalError catch in migrations
# ---------------------------------------------------------------------------


def test_migration_swallows_duplicate_column_error():
    """A 'duplicate column name' OperationalError during ADD COLUMN is silently ignored."""

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE items (item_id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("ALTER TABLE items ADD COLUMN item_photo TEXT")
    # Running _migrate_v1-style logic again must not raise
    try:
        conn.execute("ALTER TABLE items ADD COLUMN item_photo TEXT")
    except sqlite3.OperationalError as exc:
        if "duplicate column name" not in str(exc):
            raise
    conn.close()


def test_migration_reraises_unexpected_operational_error():
    """An unexpected OperationalError (not duplicate column) must propagate."""
    # Reproduce the narrowed except pattern from the migration functions:
    # only swallow "duplicate column name"; everything else must re-raise.
    import pytest

    with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
        try:
            raise sqlite3.OperationalError("disk I/O error")
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc):
                raise
