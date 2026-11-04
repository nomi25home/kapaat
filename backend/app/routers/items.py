from fastapi import APIRouter, HTTPException
from sqlalchemy import exists, func, or_, select
from sqlalchemy.exc import IntegrityError

from ..deps import CurrentUser, Db
from ..models import Bin, Checkout, Event, Item, Tag, User, Zone, item_tags, utcnow
from ..schemas import CheckoutIn, CheckoutOut, EventOut, ItemIn, ItemOut, ItemUpdate, MoveItems, Retire
from ..services.events import record
from ..services.queries import active_bin, get_item, item_query, resolve_tags
from ..services.serialize import checkout_out, event_out, item_out, item_snapshot

router = APIRouter(prefix="/api", tags=["items"])


@router.get("/items", response_model=list[ItemOut])
def list_items(
    db: Db,
    user: CurrentUser,
    q: str = "",
    status: str = "active",
    room_id: int | None = None,
    zone_id: int | None = None,
    bin_id: int | None = None,
    tag: str | None = None,
    checked_out: bool | None = None,
    unassigned: bool = False,
    limit: int = 500,
    offset: int = 0,
) -> list[ItemOut]:
    stmt = item_query().order_by(Item.name, Item.id)
    if status != "all":
        stmt = stmt.where(Item.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Item.name.ilike(like),
                Item.category.ilike(like),
                Item.notes.ilike(like),
                Item.bin_id.in_(select(Bin.id).where(or_(Bin.code.ilike(like), Bin.name.ilike(like)))),
                Item.id.in_(select(item_tags.c.item_id).join(Tag).where(Tag.name.ilike(like))),
            )
        )
    if bin_id is not None:
        stmt = stmt.where(Item.bin_id == bin_id)
    if zone_id is not None:
        stmt = stmt.where(Item.bin_id.in_(select(Bin.id).where(Bin.zone_id == zone_id)))
    if room_id is not None:
        stmt = stmt.where(Item.bin_id.in_(select(Bin.id).join(Zone).where(Zone.room_id == room_id)))
    if unassigned:
        stmt = stmt.where(Item.bin_id.is_(None))
    if tag:
        stmt = stmt.where(Item.id.in_(select(item_tags.c.item_id).join(Tag).where(Tag.name == tag.lower())))
    if checked_out is not None:
        open_co = exists().where(Checkout.item_id == Item.id, Checkout.in_at.is_(None))
        stmt = stmt.where(open_co if checked_out else ~open_co)
    items = db.scalars(stmt.limit(min(limit, 2000)).offset(offset)).unique().all()
    return [item_out(i) for i in items]


@router.get("/items/{item_id}", response_model=ItemOut)
def read_item(item_id: int, db: Db, user: CurrentUser) -> ItemOut:
    return item_out(get_item(db, item_id))


@router.get("/items/{item_id}/history", response_model=list[EventOut])
def item_history(item_id: int, db: Db, user: CurrentUser) -> list[EventOut]:
    get_item(db, item_id)
    rows = db.execute(
        select(Event, User.name, User.email)
        .outerjoin(User, Event.user_id == User.id)
        .where(Event.entity == "item", Event.entity_id == item_id)
        .order_by(Event.at.desc(), Event.id.desc())
        .limit(100)
    ).all()
    return [event_out(e, name or email) for e, name, email in rows]


@router.post("/items", response_model=ItemOut, status_code=201)
def create_item(body: ItemIn, db: Db, user: CurrentUser) -> ItemOut:
    if body.bin_id is not None:
        active_bin(db, body.bin_id)
    item = Item(
        name=body.name.strip(),
        category=body.category.strip(),
        qty=body.qty,
        notes=body.notes,
        bin_id=body.bin_id,
        tags=resolve_tags(db, body.tags),
    )
    db.add(item)
    db.flush()
    item = get_item(db, item.id)
    record(db, user, "item", item.id, "created", item_snapshot(item))
    db.commit()
    return item_out(item)


@router.patch("/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, body: ItemUpdate, db: Db, user: CurrentUser) -> ItemOut:
    item = get_item(db, item_id)
    if item.status != "active":
        raise HTTPException(409, "Restore this item before editing it")
    for field in ("name", "category", "qty", "notes"):
        value = getattr(body, field)
        if value is not None:
            setattr(item, field, value.strip() if isinstance(value, str) and field != "notes" else value)
    if body.tags is not None:
        item.tags = resolve_tags(db, body.tags)
    item.updated_at = utcnow()
    record(db, user, "item", item.id, "updated", item_snapshot(item))
    db.commit()
    return item_out(item)


@router.post("/items/{item_id}/retire", response_model=ItemOut)
def retire_item(item_id: int, body: Retire, db: Db, user: CurrentUser) -> ItemOut:
    item = get_item(db, item_id)
    if item.status != "active":
        raise HTTPException(409, "Item is already retired")
    if item.open_checkout:
        raise HTTPException(409, "Check this item in before retiring it")
    item.status, item.retired_at, item.retire_reason = "retired", utcnow(), body.reason.strip()
    record(db, user, "item", item.id, "retired", {**item_snapshot(item), "reason": item.retire_reason})
    db.commit()
    return item_out(item)


@router.post("/items/{item_id}/restore", response_model=ItemOut)
def restore_item(item_id: int, db: Db, user: CurrentUser) -> ItemOut:
    item = get_item(db, item_id)
    if item.status != "retired":
        raise HTTPException(409, "Item is not retired")
    if item.bin and item.bin.status != "active":
        item.bin_id = None
    item.status, item.retired_at, item.retire_reason = "active", None, ""
    db.flush()
    db.expire(item, ["bin"])
    item = get_item(db, item_id)
    record(db, user, "item", item.id, "restored", item_snapshot(item))
    db.commit()
    return item_out(item)


@router.post("/items/move", response_model=list[ItemOut])
def move_items(body: MoveItems, db: Db, user: CurrentUser) -> list[ItemOut]:
    target = active_bin(db, body.bin_id) if body.bin_id is not None else None
    ids = list(dict.fromkeys(body.item_ids))
    items = db.scalars(item_query().where(Item.id.in_(ids))).unique().all()
    found = {i.id for i in items}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(404, f"Items not found: {missing[:10]}")
    retired = [i.id for i in items if i.status != "active"]
    if retired:
        raise HTTPException(409, f"Retired items can't be moved: {retired[:10]}")
    for item in items:
        if item.bin_id == (target.id if target else None):
            continue
        record(
            db,
            user,
            "item",
            item.id,
            "moved",
            {"from": item.bin.code if item.bin else None, "to": target.code if target else None},
        )
        item.bin_id = target.id if target else None
        item.updated_at = utcnow()
    db.commit()
    db.expire_all()
    return [item_out(i) for i in db.scalars(item_query().where(Item.id.in_(ids))).unique()]


@router.post("/items/{item_id}/checkout", response_model=ItemOut)
def checkout_item(item_id: int, body: CheckoutIn, db: Db, user: CurrentUser) -> ItemOut:
    item = get_item(db, item_id)
    if item.status != "active":
        raise HTTPException(409, "Retired items can't be checked out")
    if item.open_checkout:
        raise HTTPException(409, "Item is already checked out")
    db.add(Checkout(item_id=item.id, user_id=user.id, due_at=body.due_at, note=body.note.strip()))
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Item is already checked out") from exc
    db.expire(item, ["open_checkout"])
    item = get_item(db, item_id)
    record(
        db,
        user,
        "item",
        item.id,
        "checked_out",
        {
            **item_snapshot(item),
            "due_at": body.due_at.isoformat() if body.due_at else None,
            "note": body.note,
        },
    )
    db.commit()
    return item_out(item)


@router.post("/items/{item_id}/checkin", response_model=ItemOut)
def checkin_item(item_id: int, db: Db, user: CurrentUser) -> ItemOut:
    item = get_item(db, item_id)
    if not item.open_checkout:
        raise HTTPException(409, "Item is not checked out")
    db.get(Checkout, item.open_checkout.id).in_at = utcnow()
    db.flush()
    db.expire(item, ["open_checkout"])
    item = get_item(db, item_id)
    record(db, user, "item", item.id, "checked_in", item_snapshot(item))
    db.commit()
    return item_out(item)


@router.get("/checkouts", response_model=list[CheckoutOut])
def list_checkouts(
    db: Db, user: CurrentUser, open: bool = True, item_id: int | None = None
) -> list[CheckoutOut]:
    stmt = select(Checkout).order_by(Checkout.out_at.desc()).limit(500)
    if open:
        stmt = stmt.where(Checkout.in_at.is_(None))
    if item_id is not None:
        stmt = stmt.where(Checkout.item_id == item_id)
    return [checkout_out(c) for c in db.scalars(stmt)]


@router.get("/categories", response_model=list[str])
def categories(db: Db, user: CurrentUser) -> list[str]:
    rows = db.scalars(
        select(Item.category).where(Item.category != "").group_by(Item.category).order_by(func.count().desc())
    )
    return list(rows)
