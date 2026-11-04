from fastapi import HTTPException
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..models import Bin, Item, Tag, Zone


def item_query() -> Select[tuple[Item]]:
    return select(Item).options(
        joinedload(Item.bin).joinedload(Bin.zone).joinedload(Zone.room),
        selectinload(Item.tags),
        joinedload(Item.open_checkout),
    )


def get_item(db: Session, item_id: int) -> Item:
    item = db.scalars(item_query().where(Item.id == item_id)).unique().first()
    if not item:
        raise HTTPException(404, "Item not found")
    return item


def get_bin(db: Session, bin_id: int) -> Bin:
    b = db.scalars(
        select(Bin).options(joinedload(Bin.zone).joinedload(Zone.room)).where(Bin.id == bin_id)
    ).first()
    if not b:
        raise HTTPException(404, "Bin not found")
    return b


def active_bin(db: Session, bin_id: int) -> Bin:
    b = get_bin(db, bin_id)
    if b.status != "active":
        raise HTTPException(409, f"Bin {b.code} is retired")
    return b


def bin_item_counts(db: Session, bin_ids: list[int]) -> dict[int, int]:
    if not bin_ids:
        return {}
    rows = db.execute(
        select(Item.bin_id, func.count(Item.id))
        .where(Item.bin_id.in_(bin_ids), Item.status == "active")
        .group_by(Item.bin_id)
    )
    return {k: v for k, v in rows}


def resolve_tags(db: Session, names: list[str]) -> list[Tag]:
    cleaned = sorted({n.strip().lower() for n in names if n.strip()})
    if not cleaned:
        return []
    existing = {t.name: t for t in db.scalars(select(Tag).where(Tag.name.in_(cleaned)))}
    for name in cleaned:
        if name not in existing:
            if len(name) > 40:
                raise HTTPException(422, f"Tag '{name[:20]}…' is longer than 40 characters")
            tag = Tag(name=name)
            db.add(tag)
            existing[name] = tag
    db.flush()
    return [existing[n] for n in cleaned]
