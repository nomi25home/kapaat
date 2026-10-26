"""Tests for PR-1: authentication enforcement on backup, export, and mutation routes.

With AUTHENTIK_CLIENT_ID unset (see conftest.py), `_require_auth` returns None
(open mode). require_admin / require_write check session["is_admin"] directly,
so anonymous requests (no session cookie) must be denied even in open mode.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sync_row(client, payload):
    return client.post("/api/sync-row?N8N_WEBHOOK_SECRET=test-webhook-secret", json=payload)


def _seed_bin_and_item(admin_client):
    admin_client.post(
        "/add-bin",
        data={"bin_id": "BIN-T1", "zone": "Garage", "shelf": "A1", "color": "#000000", "room": ""},
    )
    _sync_row(admin_client, {"bin_id": "BIN-T1", "name": "Drill", "category": "tools", "quantity": 1})


# ---------------------------------------------------------------------------
# PR-1a: GET /api/backup requires admin
# ---------------------------------------------------------------------------

def test_backup_db_anonymous_denied(client):
    r = client.get("/api/backup")
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_backup_db_admin_allowed(admin_client):
    r = admin_client.get("/api/backup")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/octet-stream"


# ---------------------------------------------------------------------------
# PR-1b: GET /api/backup/download requires admin
# ---------------------------------------------------------------------------

def test_backup_download_anonymous_denied(client):
    r = client.get("/api/backup/download")
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_backup_download_admin_allowed(admin_client):
    r = admin_client.get("/api/backup/download")
    assert r.status_code == 200
    assert "zip" in r.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# PR-1c: GET /api/backup/retention is read-only (no deletions)
# ---------------------------------------------------------------------------

def test_backup_retention_get_is_read_only(admin_client, tmp_path, monkeypatch):
    import app as app_module

    real_path = app_module.Path
    app_module.Path = lambda p: tmp_path / str(p).lstrip("/")
    try:
        backups = tmp_path / "data" / "backups"
        backups.mkdir(parents=True)
        for i in range(12):
            (backups / f"backup-{i}.zip").write_bytes(b"zip")

        r = admin_client.get("/api/backup/retention")
        assert r.status_code == 200
        body = r.json()
        # GET must NOT prune — all 12 files should still exist
        assert "pruned" not in body, "GET /api/backup/retention must not prune files"
        assert "excess" in body
        assert len(body["excess"]) == 2
        # Files must still be on disk
        remaining = list(backups.glob("*.zip"))
        assert len(remaining) == 12, f"GET should not delete files; found {len(remaining)}"
    finally:
        app_module.Path = real_path


def test_backup_retention_post_prunes(admin_client, tmp_path):
    import app as app_module

    real_path = app_module.Path
    app_module.Path = lambda p: tmp_path / str(p).lstrip("/")
    try:
        backups = tmp_path / "data" / "backups"
        backups.mkdir(parents=True)
        for i in range(15):
            (backups / f"backup-{i}.zip").write_bytes(b"zip")

        r = admin_client.post("/api/backup/retention")
        assert r.status_code == 200
        body = r.json()
        assert body["retention_limit"] == 10
        assert len(body["kept"]) == 10
        assert len(body["pruned"]) == 5
    finally:
        app_module.Path = real_path


def test_backup_retention_post_anonymous_denied(client):
    r = client.post("/api/backup/retention")
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# PR-1d: GET /export/{file_type} requires admin
# ---------------------------------------------------------------------------

def test_export_csv_anonymous_denied(client):
    r = client.get("/export/csv")
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_export_xlsx_anonymous_denied(client):
    r = client.get("/export/xlsx")
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_export_csv_admin_allowed(admin_client):
    r = admin_client.get("/export/csv")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# PR-1e: POST /add-item requires write permission
# ---------------------------------------------------------------------------

def test_add_item_anonymous_denied(client):
    # First create a bin via sync-row so the bin exists
    _sync_row(client, {"bin_id": "BIN-I1", "name": "seed", "category": "c", "quantity": 1})
    r = client.post("/add-item", data={"bin_id": "BIN-I1", "name": "Hammer", "category": "tools", "qty": 2})
    assert r.status_code == 403, f"expected 403, got {r.status_code}"


def test_add_item_admin_allowed(admin_client, client):
    admin_client.post("/add-bin", data={"bin_id": "BIN-I2", "zone": "Z", "shelf": "S", "color": "#000", "room": ""})
    r = admin_client.post("/add-item", data={"bin_id": "BIN-I2", "name": "Hammer", "category": "tools", "qty": 1})
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ---------------------------------------------------------------------------
# PR-1f: GET /api/sync-conflicts requires read permission
# ---------------------------------------------------------------------------

def test_sync_conflicts_anonymous_denied_when_api_key_set(monkeypatch):
    """When SERVICE_API_KEY is configured, anonymous access to sync-conflicts is denied."""
    import importlib
    import os

    from fastapi.testclient import TestClient

    import app as app_module

    os.environ["SERVICE_API_KEY"] = "test-key-scoped"
    os.environ["SERVICE_API_SCOPES"] = "read,write"
    importlib.reload(app_module)
    try:
        with TestClient(app_module.app) as c:
            r = c.get("/api/sync-conflicts")
            assert r.status_code == 403
    finally:
        del os.environ["SERVICE_API_KEY"]
        importlib.reload(app_module)


def test_sync_conflicts_open_when_no_api_key(client):
    """With no SERVICE_API_KEY, require_read allows all — backward-compat."""
    r = client.get("/api/sync-conflicts")
    assert r.status_code == 200
