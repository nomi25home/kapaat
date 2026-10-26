"""Tests for PR-8: photo upload size limit and content-type validation."""

from __future__ import annotations

import io


def _png_header() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


def _jpg_header() -> bytes:
    return b"\xff\xd8\xff\xe0" + b"\x00" * 100


def test_upload_photo_rejects_oversized_file(admin_client, tmp_path, monkeypatch):
    """An upload that exceeds MAX_PHOTO_BYTES must return 413."""
    import app as app_module

    monkeypatch.setattr(app_module, "PHOTOS_DIR", tmp_path)
    monkeypatch.setattr(app_module, "_MAX_PHOTO_BYTES", 10)  # tiny limit

    data = b"A" * 11  # one byte over
    r = admin_client.post(
        "/upload-photo/item/1",
        files={"file": ("test.jpg", io.BytesIO(data), "image/jpeg")},
    )
    assert r.status_code == 413, f"expected 413, got {r.status_code}"


def test_upload_photo_rejects_bad_magic_bytes(admin_client, tmp_path, monkeypatch):
    """A .jpg file whose content is not JPEG magic bytes must return 400."""
    import app as app_module

    monkeypatch.setattr(app_module, "PHOTOS_DIR", tmp_path)

    data = b"This is not an image" + b"\x00" * 100
    r = admin_client.post(
        "/upload-photo/item/1",
        files={"file": ("fake.jpg", io.BytesIO(data), "image/jpeg")},
    )
    assert r.status_code == 400, f"expected 400 for bad magic bytes, got {r.status_code}"


def test_upload_photo_accepts_valid_png(admin_client, tmp_path, monkeypatch):
    """A valid PNG file must be accepted (201/200) and written to PHOTOS_DIR."""
    import app as app_module

    monkeypatch.setattr(app_module, "PHOTOS_DIR", tmp_path)

    data = _png_header()
    r = admin_client.post(
        "/upload-photo/item/1",
        files={"file": ("photo.png", io.BytesIO(data), "image/png")},
    )
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
    assert any(tmp_path.iterdir()), "no file written to PHOTOS_DIR"


def test_upload_photo_anonymous_denied(client, tmp_path, monkeypatch):
    """An unauthenticated request must be rejected (require_admin)."""
    import app as app_module

    monkeypatch.setattr(app_module, "PHOTOS_DIR", tmp_path)

    r = client.post(
        "/upload-photo/item/1",
        files={"file": ("photo.jpg", io.BytesIO(_jpg_header()), "image/jpeg")},
    )
    assert r.status_code in (401, 403), f"expected 401/403 for anonymous, got {r.status_code}"
