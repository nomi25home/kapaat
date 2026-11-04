from ..models import Bin, Checkout, Event, Item, Zone
from ..schemas import BinOut, BinRef, CheckoutOut, EventOut, ItemOut, Location, TagOut


def location_of_zone(zone: Zone | None) -> Location:
    if not zone:
        return Location()
    return Location(room_id=zone.room_id, room=zone.room.name, zone_id=zone.id, zone=zone.name)


def checkout_out(c: Checkout) -> CheckoutOut:
    return CheckoutOut(
        id=c.id,
        item_id=c.item_id,
        user=(c.user.name or c.user.email) if c.user else None,
        out_at=c.out_at,
        due_at=c.due_at,
        in_at=c.in_at,
        note=c.note,
    )


def bin_out(b: Bin, item_count: int = 0) -> BinOut:
    return BinOut(
        id=b.id,
        code=b.code,
        name=b.name,
        color=b.color,
        notes=b.notes,
        photo=b.photo,
        status=b.status,
        created_at=b.created_at,
        retired_at=b.retired_at,
        retire_reason=b.retire_reason,
        location=location_of_zone(b.zone),
        item_count=item_count,
    )


def item_out(i: Item) -> ItemOut:
    return ItemOut(
        id=i.id,
        name=i.name,
        category=i.category,
        qty=i.qty,
        notes=i.notes,
        photo=i.photo,
        status=i.status,
        created_at=i.created_at,
        updated_at=i.updated_at,
        retired_at=i.retired_at,
        retire_reason=i.retire_reason,
        bin=BinRef(id=i.bin.id, code=i.bin.code, name=i.bin.name, color=i.bin.color) if i.bin else None,
        location=location_of_zone(i.bin.zone if i.bin else None),
        tags=[TagOut.model_validate(t) for t in i.tags],
        checkout=checkout_out(i.open_checkout) if i.open_checkout else None,
    )


def item_snapshot(i: Item) -> dict:
    """Flat row used for audit payloads and webhook consumers such as Google Sheets."""
    loc = location_of_zone(i.bin.zone if i.bin else None)
    return {
        "id": i.id,
        "name": i.name,
        "category": i.category,
        "qty": i.qty,
        "notes": i.notes,
        "status": i.status,
        "bin": i.bin.code if i.bin else None,
        "room": loc.room,
        "zone": loc.zone,
        "tags": [t.name for t in i.tags],
        "checked_out": i.open_checkout is not None,
    }


def bin_snapshot(b: Bin) -> dict:
    loc = location_of_zone(b.zone)
    return {
        "id": b.id,
        "code": b.code,
        "name": b.name,
        "status": b.status,
        "room": loc.room,
        "zone": loc.zone,
        "color": b.color,
    }


def event_out(e: Event, user_label: str | None) -> EventOut:
    return EventOut(
        id=e.id,
        at=e.at,
        user=user_label,
        entity=e.entity,
        entity_id=e.entity_id,
        action=e.action,
        payload=e.payload,
    )
