from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from ..deps import CurrentUser, Db
from ..models import Bin, Room, Zone
from ..schemas import RoomIn, RoomOut, ZoneIn, ZoneOut, ZoneUpdate
from ..services.events import record

router = APIRouter(prefix="/api", tags=["locations"])


def _bin_counts(db: Db) -> dict[int, int]:
    rows = db.execute(
        select(Bin.zone_id, func.count(Bin.id))
        .where(Bin.status == "active", Bin.zone_id.is_not(None))
        .group_by(Bin.zone_id)
    )
    return {k: v for k, v in rows}


def _room_out(room: Room, counts: dict[int, int]) -> RoomOut:
    return RoomOut(
        id=room.id,
        name=room.name,
        notes=room.notes,
        zones=[
            ZoneOut(id=z.id, room_id=z.room_id, name=z.name, bin_count=counts.get(z.id, 0))
            for z in room.zones
        ],
    )


def _commit_unique(db: Db, what: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, f"A {what} with that name already exists") from exc


@router.get("/locations", response_model=list[RoomOut])
def list_locations(db: Db, user: CurrentUser) -> list[RoomOut]:
    rooms = db.scalars(select(Room).options(selectinload(Room.zones)).order_by(Room.name)).all()
    counts = _bin_counts(db)
    return [_room_out(r, counts) for r in rooms]


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(body: RoomIn, db: Db, user: CurrentUser) -> RoomOut:
    room = Room(name=body.name.strip(), notes=body.notes)
    db.add(room)
    _commit_unique(db, "room")
    record(db, user, "room", room.id, "created", {"name": room.name})
    db.commit()
    return _room_out(room, {})


@router.patch("/rooms/{room_id}", response_model=RoomOut)
def update_room(room_id: int, body: RoomIn, db: Db, user: CurrentUser) -> RoomOut:
    room = db.get(Room, room_id) or _404("Room")
    room.name, room.notes = body.name.strip(), body.notes
    record(db, user, "room", room.id, "updated", {"name": room.name})
    _commit_unique(db, "room")
    return _room_out(room, _bin_counts(db))


@router.delete("/rooms/{room_id}", status_code=204)
def delete_room(room_id: int, db: Db, user: CurrentUser) -> None:
    room = db.get(Room, room_id) or _404("Room")
    if room.zones:
        raise HTTPException(409, "Delete or move this room's zones first")
    record(db, user, "room", room.id, "deleted", {"name": room.name})
    db.delete(room)
    db.commit()


@router.post("/zones", response_model=ZoneOut, status_code=201)
def create_zone(body: ZoneIn, db: Db, user: CurrentUser) -> ZoneOut:
    db.get(Room, body.room_id) or _404("Room")
    zone = Zone(room_id=body.room_id, name=body.name.strip())
    db.add(zone)
    _commit_unique(db, "zone in this room")
    record(db, user, "zone", zone.id, "created", {"name": zone.name, "room_id": zone.room_id})
    db.commit()
    return ZoneOut(id=zone.id, room_id=zone.room_id, name=zone.name)


@router.patch("/zones/{zone_id}", response_model=ZoneOut)
def update_zone(zone_id: int, body: ZoneUpdate, db: Db, user: CurrentUser) -> ZoneOut:
    zone = db.get(Zone, zone_id) or _404("Zone")
    if body.room_id is not None:
        db.get(Room, body.room_id) or _404("Room")
        zone.room_id = body.room_id
    if body.name is not None:
        zone.name = body.name.strip()
    record(db, user, "zone", zone.id, "updated", {"name": zone.name, "room_id": zone.room_id})
    _commit_unique(db, "zone in this room")
    return ZoneOut(
        id=zone.id, room_id=zone.room_id, name=zone.name, bin_count=_bin_counts(db).get(zone.id, 0)
    )


@router.delete("/zones/{zone_id}", status_code=204)
def delete_zone(zone_id: int, db: Db, user: CurrentUser) -> None:
    zone = db.get(Zone, zone_id) or _404("Zone")
    if db.scalar(select(func.count(Bin.id)).where(Bin.zone_id == zone_id, Bin.status == "active")):
        raise HTTPException(409, "Move or retire the bins in this zone first")
    for retired in db.scalars(select(Bin).where(Bin.zone_id == zone_id)):
        retired.zone_id = None
    record(db, user, "zone", zone.id, "deleted", {"name": zone.name})
    db.delete(zone)
    db.commit()


def _404(what: str):
    raise HTTPException(404, f"{what} not found")
