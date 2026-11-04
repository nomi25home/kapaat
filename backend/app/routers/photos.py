import io
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, ImageOps, UnidentifiedImageError

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..services.events import record
from ..services.queries import active_bin, get_item

router = APIRouter(prefix="/api", tags=["photos"])

MAX_SIDE = 1600
NAME_RE = re.compile(r"^[0-9a-f]{32}\.jpg$")
Image.MAX_IMAGE_PIXELS = 60_000_000


def photos_dir() -> Path:
    path = Path(get_settings().photos_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def _store(file: UploadFile) -> str:
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise HTTPException(413, f"Photo is larger than {get_settings().max_upload_mb} MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
        if img.format not in {"JPEG", "PNG", "WEBP", "GIF", "MPO"}:
            raise HTTPException(400, "Upload a JPEG, PNG, WebP or GIF image")
        # Re-encode: normalises orientation, strips EXIF/GPS, bounds size.
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(400, "That file is not a readable image") from exc
    name = f"{uuid.uuid4().hex}.jpg"
    img.save(photos_dir() / name, "JPEG", quality=85, optimize=True)
    return name


def _remove(name: str | None) -> None:
    if name and NAME_RE.match(name):
        (photos_dir() / name).unlink(missing_ok=True)


@router.post("/items/{item_id}/photo")
async def upload_item_photo(item_id: int, file: UploadFile, db: Db, user: CurrentUser) -> dict:
    item = get_item(db, item_id)
    name = await _store(file)
    old, item.photo = item.photo, name
    record(db, user, "item", item.id, "photo_updated", {})
    db.commit()
    _remove(old)
    return {"photo": name}


@router.delete("/items/{item_id}/photo", status_code=204)
def delete_item_photo(item_id: int, db: Db, user: CurrentUser) -> None:
    item = get_item(db, item_id)
    old, item.photo = item.photo, None
    db.commit()
    _remove(old)


@router.post("/bins/{bin_id}/photo")
async def upload_bin_photo(bin_id: int, file: UploadFile, db: Db, user: CurrentUser) -> dict:
    b = active_bin(db, bin_id)
    name = await _store(file)
    old, b.photo = b.photo, name
    record(db, user, "bin", b.id, "photo_updated", {})
    db.commit()
    _remove(old)
    return {"photo": name}


@router.delete("/bins/{bin_id}/photo", status_code=204)
def delete_bin_photo(bin_id: int, db: Db, user: CurrentUser) -> None:
    b = active_bin(db, bin_id)
    old, b.photo = b.photo, None
    db.commit()
    _remove(old)


@router.get("/photos/{name}")
def get_photo(name: str, user: CurrentUser) -> FileResponse:
    if not NAME_RE.match(name):
        raise HTTPException(404, "Photo not found")
    path = photos_dir() / name
    if not path.is_file():
        raise HTTPException(404, "Photo not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=31536000"})
