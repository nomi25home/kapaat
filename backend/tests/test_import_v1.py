import io
import sqlite3

import pytest
from PIL import Image

from app.routers.photos import photos_dir
from scripts import import_v1

V1_SCHEMA = """
CREATE TABLE bins (bin_id TEXT PRIMARY KEY, zone TEXT NOT NULL, shelf_number TEXT, color_code TEXT,
                   bin_photo TEXT, room TEXT DEFAULT '', last_synced_at TEXT);
CREATE TABLE items (item_id INTEGER PRIMARY KEY AUTOINCREMENT, bin_id TEXT, name TEXT NOT NULL, category TEXT,
                    quantity INTEGER DEFAULT 1, item_photo TEXT, tags TEXT DEFAULT '', version INTEGER DEFAULT 1,
                    last_synced_at TEXT);
CREATE TABLE tag_colors (tag_name TEXT PRIMARY KEY, hex TEXT NOT NULL);
CREATE TABLE audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT NOT NULL, action TEXT NOT NULL,
                        item_id INTEGER, details TEXT, timestamp TEXT NOT NULL DEFAULT (datetime('now')));
"""


@pytest.fixture
def v1(tmp_path):
    """A generated v1 database — never a real household one."""
    photos = tmp_path / "photos"
    photos.mkdir()
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (0, 120, 200)).save(buf, "PNG")
    (photos / "item_1_123.png").write_bytes(buf.getvalue())
    (photos / "broken.jpg").write_bytes(b"nope")

    path = tmp_path / "storage.db"
    conn = sqlite3.connect(path)
    conn.executescript(V1_SCHEMA)
    conn.executemany(
        "INSERT INTO bins (bin_id, zone, shelf_number, color_code, room, bin_photo) VALUES (?,?,?,?,?,?)",
        [
            ("GAR-1", "Garage", "2", "#3b82f6", "North Wall", None),
            ("GAR-2", "Garage", "", "red", "", "broken.jpg"),
            ("Attic box 7", "Attic", None, None, "Eaves", None),
        ],
    )
    conn.executemany(
        "INSERT INTO items (bin_id, name, category, quantity, item_photo, tags) VALUES (?,?,?,?,?,?)",
        [
            ("GAR-1", "Drill", "Tools", 1, "item_1_123.png", "power,tools"),
            ("GAR-1", "Bits", "Tools", 40, None, "tools"),
            ("Attic box 7", "Ornaments", "", 3, None, ""),
            ("GHOST", "Orphan", None, 1, None, None),
        ],
    )
    conn.execute("INSERT INTO tag_colors VALUES ('tools', '#ff8800')")
    conn.execute(
        "INSERT INTO audit_log (actor, action, item_id, details) VALUES ('a@x', 'UPDATE', 1, 'qty 2->1')"
    )
    conn.commit()
    conn.close()
    return path, photos


def test_dry_run_writes_nothing(v1, admin):
    path, photos = v1
    before = sorted(p.name for p in photos_dir().iterdir())
    report = import_v1.run(path, photos, dry=True)
    assert (report.bins, report.items) == (3, 4)
    assert admin.get("/api/bins").json() == [] and admin.get("/api/items").json() == []
    after = sorted(p.name for p in photos_dir().iterdir())
    assert before == after


def test_import_maps_hierarchy_tags_photos_history(v1, admin):
    path, photos = v1
    src_before = path.read_bytes()
    report = import_v1.run(path, photos, dry=False)
    assert path.read_bytes() == src_before  # v1 db untouched
    assert (report.rooms, report.zones, report.bins, report.items, report.photos) == (2, 3, 3, 4, 1)
    assert any("renamed to 'Attic-box-7'" in w for w in report.warnings)
    assert any("not a readable image" in w for w in report.warnings)
    assert any("missing bin 'GHOST'" in w for w in report.warnings)

    rooms = {r["name"]: [z["name"] for z in r["zones"]] for r in admin.get("/api/locations").json()}
    assert rooms == {"Attic": ["Eaves"], "Garage": ["General", "North Wall"]}

    gar1 = admin.get("/api/bins/by-code/gar-1").json()  # old labels resolve case-insensitively
    assert gar1["notes"] == "Shelf 2" and gar1["color"] == "#3b82f6" and gar1["item_count"] == 2
    assert gar1["location"]["room"] == "Garage" and gar1["location"]["zone"] == "North Wall"
    assert admin.get("/api/bins/by-code/GAR-2").json()["color"] == "#4cd7f6"  # invalid colour replaced

    drill = next(i for i in admin.get("/api/items", params={"q": "drill"}).json())
    assert [t["name"] for t in drill["tags"]] == ["power", "tools"] and drill["photo"]
    assert {t["name"]: t["color"] for t in admin.get("/api/tags").json()}["tools"] == "#ff8800"
    assert admin.get(f"/api/photos/{drill['photo']}").status_code == 200
    history = admin.get(f"/api/items/{drill['id']}/history").json()
    assert sorted(h["action"] for h in history) == ["created", "v1_history"]
    assert admin.get("/api/items", params={"unassigned": True}).json()[0]["name"] == "Orphan"


def test_reimport_is_idempotent(v1, admin):
    path, photos = v1
    import_v1.run(path, photos, dry=False)
    again = import_v1.run(path, photos, dry=False)
    assert (again.bins, again.items, again.bins_skipped, again.items_skipped) == (0, 0, 3, 4)
    assert len(admin.get("/api/items").json()) == 4


def test_cli_missing_file(tmp_path, capsys):
    assert import_v1.main(["--sqlite", str(tmp_path / "nope.db")]) == 2
