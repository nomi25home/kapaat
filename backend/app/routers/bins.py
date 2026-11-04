from fastapi import APIRouter, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from ..deps import CurrentUser, Db
from ..models import Bin, Item, Zone, bin_code_seq, utcnow
from ..schemas import BinIn, BinOut, BinRetire, BinUpdate
from ..services.events import record
from ..services.queries import active_bin, bin_item_counts, get_bin
from ..services.serialize import bin_out, bin_snapshot

router = APIRouter(prefix="/api/bins", tags=["bins"])


def _next_code(db: Db) -> str:
    while True:
        code = f"B-{db.scalar(bin_code_seq.next_value()):04d}"
        if not db.scalar(select(Bin.id).where(func.lower(Bin.code) == code.lower())):
            return code


def _check_zone(db: Db, zone_id: int | None) -> None:
    if zone_id is not None and not db.get(Zone, zone_id):
        raise HTTPException(404, "Zone not found")


@router.get("", response_model=list[BinOut])
def list_bins(
    db: Db,
    user: CurrentUser,
    q: str = "",
    status: str = "active",
    room_id: int | None = None,
    zone_id: int | None = None,
    unassigned: bool = False,
) -> list[BinOut]:
    stmt = select(Bin).options(joinedload(Bin.zone).joinedload(Zone.room)).order_by(Bin.code)
    if status != "all":
        stmt = stmt.where(Bin.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Bin.code.ilike(like), Bin.name.ilike(like)))
    if zone_id is not None:
        stmt = stmt.where(Bin.zone_id == zone_id)
    if room_id is not None:
        stmt = stmt.join(Zone, Bin.zone_id == Zone.id).where(Zone.room_id == room_id)
    if unassigned:
        stmt = stmt.where(Bin.zone_id.is_(None))
    bins = db.scalars(stmt).all()
    counts = bin_item_counts(db, [b.id for b in bins])
    return [bin_out(b, counts.get(b.id, 0)) for b in bins]


@router.get("/by-code/{code}", response_model=BinOut)
def bin_by_code(code: str, db: Db, user: CurrentUser) -> BinOut:
    bin_id = db.scalar(select(Bin.id).where(func.lower(Bin.code) == code.lower()))
    if not bin_id:
        raise HTTPException(404, "Bin not found")
    return bin_out(get_bin(db, bin_id), bin_item_counts(db, [bin_id]).get(bin_id, 0))


@router.get("/{bin_id}", response_model=BinOut)
def read_bin(bin_id: int, db: Db, user: CurrentUser) -> BinOut:
    return bin_out(get_bin(db, bin_id), bin_item_counts(db, [bin_id]).get(bin_id, 0))


@router.post("", response_model=BinOut, status_code=201)
def create_bin(body: BinIn, db: Db, user: CurrentUser) -> BinOut:
    _check_zone(db, body.zone_id)
    code = body.code.strip().upper() if body.code else _next_code(db)
    if db.scalar(select(Bin.id).where(func.lower(Bin.code) == code.lower())):
        raise HTTPException(409, f"Bin code {code} is already used")
    b = Bin(code=code, name=body.name.strip(), zone_id=body.zone_id, color=body.color, notes=body.notes)
    db.add(b)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, f"Bin code {code} is already used") from exc
    b = get_bin(db, b.id)
    record(db, user, "bin", b.id, "created", bin_snapshot(b))
    db.commit()
    return bin_out(b)


@router.patch("/{bin_id}", response_model=BinOut)
def update_bin(bin_id: int, body: BinUpdate, db: Db, user: CurrentUser) -> BinOut:
    b = active_bin(db, bin_id)
    if body.clear_zone:
        b.zone_id = None
    elif body.zone_id is not None:
        _check_zone(db, body.zone_id)
        b.zone_id = body.zone_id
    for field in ("name", "color", "notes"):
        value = getattr(body, field)
        if value is not None:
            setattr(b, field, value.strip() if field == "name" else value)
    db.flush()
    db.expire(b, ["zone"])
    b = get_bin(db, bin_id)
    record(db, user, "bin", b.id, "updated", bin_snapshot(b))
    db.commit()
    return bin_out(b, bin_item_counts(db, [b.id]).get(b.id, 0))


@router.post("/{bin_id}/retire", response_model=BinOut)
def retire_bin(bin_id: int, body: BinRetire, db: Db, user: CurrentUser) -> BinOut:
    b = active_bin(db, bin_id)
    target = None
    if body.contents == "move":
        if body.target_bin_id is None or body.target_bin_id == bin_id:
            raise HTTPException(422, "Pick a different bin to move the contents to")
        target = active_bin(db, body.target_bin_id)
    contents = db.scalars(select(Item).where(Item.bin_id == bin_id, Item.status == "active")).all()
    for item in contents:
        item.bin_id = target.id if target else None
        record(
            db,
            user,
            "item",
            item.id,
            "moved",
            {"from": b.code, "to": target.code if target else None, "reason": "bin retired"},
        )
    b.status, b.retired_at, b.retire_reason = "retired", utcnow(), body.reason.strip()
    record(
        db,
        user,
        "bin",
        b.id,
        "retired",
        {**bin_snapshot(b), "reason": b.retire_reason, "moved_items": len(contents)},
    )
    db.commit()
    return bin_out(b)


@router.post("/{bin_id}/restore", response_model=BinOut)
def restore_bin(bin_id: int, db: Db, user: CurrentUser) -> BinOut:
    b = get_bin(db, bin_id)
    if b.status != "retired":
        raise HTTPException(409, "Bin is not retired")
    b.status, b.retired_at, b.retire_reason = "active", None, ""
    record(db, user, "bin", b.id, "restored", bin_snapshot(b))
    db.commit()
    return bin_out(b, bin_item_counts(db, [b.id]).get(b.id, 0))
