"""Import a Kapaat v1 SQLite database (and its photos) into Kapaat v2.

    docker compose run --rm -v /path/to/v1-data:/v1:ro api \
        python -m scripts.import_v1 --sqlite /v1/storage.db --photos /v1/photos --dry-run

The v1 database is opened read-only and never modified. Run with --dry-run first, then without.
Re-running is safe: bins whose code already exists and items already imported are skipped.

Mapping:
  v1 bins.zone  (the big area, e.g. "Garage")      -> v2 room
  v1 bins.room  (part of it, e.g. "North wall")     -> v2 zone   ("General" if blank)
  v1 bins.shelf_number                              -> appended to the bin's notes
  v1 bin_id                                         -> v2 bin code (old QR labels keep working)
  v1 items.tags (comma-separated) + tag_colors      -> v2 tags with colours
  v1 audit_log                                      -> v2 item history
"""

import argparse
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import func, select

from app.db import session_factory
from app.models import AppSetting, Bin, Event, Item, Room, Zone
from app.routers.photos import save_image_bytes
from app.services.queries import resolve_tags

CODE_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
HEX_OK = re.compile(r"^#[0-9a-fA-F]{6}$")
MAP_KEY = "v1_import_items"
BIN_MAP_KEY = "v1_import_bins"


@dataclass
class Report:
    rooms: int = 0
    zones: int = 0
    bins: int = 0
    bins_skipped: int = 0
    items: int = 0
    items_skipped: int = 0
    photos: int = 0
    history: int = 0
    warnings: list[str] = field(default_factory=list)

    def print(self, dry: bool) -> None:
        verb = "Would import" if dry else "Imported"
        print(
            f"{verb}: {self.rooms} rooms, {self.zones} zones, {self.bins} bins, {self.items} items, "
            f"{self.photos} photos, {self.history} history entries"
        )
        if self.bins_skipped or self.items_skipped:
            print(f"Skipped (already present): {self.bins_skipped} bins, {self.items_skipped} items")
        for w in self.warnings:
            print(f"  ! {w}")


def columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}  # noqa: S608 (fixed table names)


def safe_code(raw: str, taken: set[str], report: Report) -> str:
    code = raw.strip()
    if not CODE_OK.match(code):
        fixed = re.sub(r"[^A-Za-z0-9_-]+", "-", code).strip("-_")[:32] or "BIN"
        n, candidate = 1, fixed
        while candidate.lower() in taken:
            n += 1
            candidate = f"{fixed[:28]}-{n}"
        report.warnings.append(
            f"bin '{raw}' renamed to '{candidate}' (v2 codes allow A-Z, 0-9, - and _); reprint its label"
        )
        code = candidate
    return code


def load_photo(photos: Path | None, name: str | None, report: Report, what: str, dry: bool) -> str | None:
    if not photos or not name:
        return None
    path = photos / Path(name).name
    if not path.is_file():
        report.warnings.append(f"photo for {what} not found: {name}")
        return None
    if dry:
        report.photos += 1
        return None
    try:
        stored = save_image_bytes(path.read_bytes())
    except HTTPException:
        report.warnings.append(f"photo for {what} is not a readable image: {name}")
        return None
    report.photos += 1
    return stored


def run(sqlite_path: Path, photos: Path | None, dry: bool) -> Report:
    report = Report()
    src = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    bin_cols, item_cols = columns(src, "bins"), columns(src, "items")
    tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    db = session_factory()()
    try:
        taken = {c.lower() for c in db.scalars(select(Bin.code))}
        rooms = {r.name.lower(): r for r in db.scalars(select(Room))}
        zones = {(z.room_id, z.name.lower()): z for z in db.scalars(select(Zone))}
        bin_by_v1: dict[str, Bin] = {}
        bin_map_row = db.get(AppSetting, BIN_MAP_KEY) or AppSetting(key=BIN_MAP_KEY, value={})
        bin_map: dict[str, int] = dict(bin_map_row.value)

        if "tag_colors" in tables:
            for row in src.execute("SELECT tag_name, hex FROM tag_colors"):
                tag = resolve_tags(db, [row["tag_name"]])
                if tag and HEX_OK.match(row["hex"] or ""):
                    tag[0].color = row["hex"]

        for row in src.execute("SELECT * FROM bins ORDER BY bin_id"):
            v1_id = row["bin_id"]
            already = db.get(Bin, bin_map[v1_id]) if v1_id in bin_map else None
            if already:
                bin_by_v1[v1_id] = already
                report.bins_skipped += 1
                continue
            existing = db.scalar(select(Bin).where(func.lower(Bin.code) == v1_id.strip().lower()))
            if existing:
                bin_by_v1[v1_id] = existing
                report.bins_skipped += 1
                continue
            code = safe_code(v1_id, taken, report)

            room_name = (row["zone"] or "").strip() or "Unsorted"
            zone_name = ((row["room"] if "room" in bin_cols else "") or "").strip() or "General"
            room = rooms.get(room_name.lower())
            if not room:
                room = Room(name=room_name[:80])
                db.add(room)
                db.flush()
                rooms[room_name.lower()] = room
                report.rooms += 1
            zone = zones.get((room.id, zone_name.lower()))
            if not zone:
                zone = Zone(room_id=room.id, name=zone_name[:80])
                db.add(zone)
                db.flush()
                zones[(room.id, zone_name.lower())] = zone
                report.zones += 1

            shelf = (row["shelf_number"] or "").strip() if "shelf_number" in bin_cols else ""
            color = (
                row["color_code"]
                if "color_code" in bin_cols and HEX_OK.match(row["color_code"] or "")
                else "#4cd7f6"
            )
            b = Bin(
                code=code,
                name="",
                zone_id=zone.id,
                color=color,
                notes=f"Shelf {shelf}" if shelf else "",
                photo=load_photo(
                    photos, row["bin_photo"] if "bin_photo" in bin_cols else None, report, f"bin {v1_id}", dry
                ),
            )
            db.add(b)
            db.flush()
            db.add(
                Event(
                    entity="bin",
                    entity_id=b.id,
                    action="created",
                    payload={"code": code, "source": "v1 import"},
                    delivered_at=func.now(),
                )
            )
            taken.add(code.lower())
            bin_by_v1[v1_id] = b
            bin_map[v1_id] = b.id
            report.bins += 1

        mapping_row = db.get(AppSetting, MAP_KEY) or AppSetting(key=MAP_KEY, value={})
        mapping: dict[str, int] = dict(mapping_row.value)
        new_ids: dict[int, int] = {}
        for row in src.execute("SELECT * FROM items ORDER BY item_id"):
            v1_id = str(row["item_id"])
            if v1_id in mapping:
                report.items_skipped += 1
                continue
            target = bin_by_v1.get(row["bin_id"]) if row["bin_id"] else None
            if row["bin_id"] and not target:
                report.warnings.append(
                    f"item {v1_id} '{row['name']}' pointed at missing bin '{row['bin_id']}'; left unassigned"
                )
            tags = (row["tags"] or "").split(",") if "tags" in item_cols else []
            item = Item(
                name=(row["name"] or "Unnamed item")[:200],
                category=(row["category"] or "")[:80],
                qty=max(0, int(row["quantity"] or 0)),
                bin_id=target.id if target else None,
                tags=resolve_tags(db, tags),
                photo=load_photo(
                    photos,
                    row["item_photo"] if "item_photo" in item_cols else None,
                    report,
                    f"item {v1_id}",
                    dry,
                ),
            )
            db.add(item)
            db.flush()
            db.add(
                Event(
                    entity="item",
                    entity_id=item.id,
                    action="created",
                    payload={"bin": target.code if target else None, "source": "v1 import"},
                    delivered_at=func.now(),
                )
            )
            mapping[v1_id] = item.id
            new_ids[int(v1_id)] = item.id
            report.items += 1

        if "audit_log" in tables and new_ids:
            for row in src.execute(
                "SELECT actor, action, item_id, details, timestamp FROM audit_log ORDER BY id"
            ):
                v2_id = new_ids.get(row["item_id"]) if row["item_id"] is not None else None
                if v2_id is None:
                    continue
                db.add(
                    Event(
                        entity="item",
                        entity_id=v2_id,
                        action="v1_history",
                        payload={
                            "action": row["action"],
                            "details": (row["details"] or "")[:500],
                            "actor": row["actor"],
                            "at": row["timestamp"],
                        },
                        delivered_at=func.now(),
                    )
                )
                report.history += 1

        mapping_row.value = mapping
        db.merge(mapping_row)
        bin_map_row.value = bin_map
        db.merge(bin_map_row)
        if dry:
            db.rollback()
        else:
            db.commit()
    finally:
        db.close()
        src.close()
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sqlite", required=True, type=Path, help="path to the v1 database file")
    ap.add_argument("--photos", type=Path, help="path to the v1 photos directory")
    ap.add_argument("--dry-run", action="store_true", help="show what would be imported without writing")
    args = ap.parse_args(argv)
    if not args.sqlite.is_file():
        print(f"No such file: {args.sqlite}", file=sys.stderr)
        return 2
    report = run(args.sqlite, args.photos, args.dry_run)
    report.print(args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
