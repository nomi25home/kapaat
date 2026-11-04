from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..deps import CurrentUser, Db
from ..models import Item, Tag, item_tags
from ..schemas import TagOut, TagUpdate

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("")
def list_tags(db: Db, user: CurrentUser) -> list[dict]:
    rows = db.execute(
        select(Tag, func.count(Item.id))
        .outerjoin(item_tags, item_tags.c.tag_id == Tag.id)
        .outerjoin(Item, (Item.id == item_tags.c.item_id) & (Item.status == "active"))
        .group_by(Tag.id)
        .order_by(Tag.name)
    ).all()
    return [{**TagOut.model_validate(t).model_dump(), "item_count": n} for t, n in rows]


@router.patch("/{tag_id}", response_model=TagOut)
def update_tag(tag_id: int, body: TagUpdate, db: Db, user: CurrentUser) -> Tag:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    if body.name is not None:
        tag.name = body.name.strip().lower()
    if body.color is not None:
        tag.color = body.color
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "A tag with that name already exists") from exc
    return tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Db, user: CurrentUser) -> None:
    tag = db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(404, "Tag not found")
    db.delete(tag)
    db.commit()
