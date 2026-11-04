import io

from PIL import Image


def make_location(api, room="Garage", zone="North wall"):
    r = api.post("/api/rooms", json={"name": room}).json()
    z = api.post("/api/zones", json={"room_id": r["id"], "name": zone}).json()
    return r, z


def make_bin(api, **kw):
    r = api.post("/api/bins", json=kw)
    assert r.status_code == 201, r.text
    return r.json()


def make_item(api, **kw):
    kw.setdefault("name", "Widget")
    r = api.post("/api/items", json=kw)
    assert r.status_code == 201, r.text
    return r.json()


def test_locations_tree_and_counts(admin):
    room, zone = make_location(admin)
    make_bin(admin, zone_id=zone["id"])
    tree = admin.get("/api/locations").json()
    assert tree[0]["name"] == "Garage"
    assert tree[0]["zones"][0]["bin_count"] == 1


def test_duplicate_names_conflict(admin):
    room, zone = make_location(admin)
    assert admin.post("/api/rooms", json={"name": "Garage"}).status_code == 409
    assert admin.post("/api/zones", json={"room_id": room["id"], "name": "North wall"}).status_code == 409


def test_zone_delete_blocked_while_bins_active(admin):
    room, zone = make_location(admin)
    b = make_bin(admin, zone_id=zone["id"])
    assert admin.delete(f"/api/zones/{zone['id']}").status_code == 409
    assert admin.delete(f"/api/rooms/{room['id']}").status_code == 409
    admin.post(f"/api/bins/{b['id']}/retire", json={})
    assert admin.delete(f"/api/zones/{zone['id']}").status_code == 204
    assert admin.delete(f"/api/rooms/{room['id']}").status_code == 204


def test_bin_codes_auto_and_custom(admin):
    assert make_bin(admin)["code"] == "B-0001"
    assert make_bin(admin)["code"] == "B-0002"
    assert make_bin(admin, code="tools-1")["code"] == "TOOLS-1"
    assert admin.post("/api/bins", json={"code": "Tools-1"}).status_code == 409
    assert admin.get("/api/bins/by-code/tools-1").json()["code"] == "TOOLS-1"


def test_bin_location_and_move_zone(admin):
    room, zone = make_location(admin)
    _, zone2 = make_location(admin, room="Attic", zone="Eaves")
    b = make_bin(admin, zone_id=zone["id"], name="Cables")
    assert b["location"] == {
        "room_id": room["id"],
        "room": "Garage",
        "zone_id": zone["id"],
        "zone": "North wall",
    }
    b = admin.patch(f"/api/bins/{b['id']}", json={"zone_id": zone2["id"]}).json()
    assert b["location"]["room"] == "Attic"
    b = admin.patch(f"/api/bins/{b['id']}", json={"clear_zone": True}).json()
    assert b["location"]["room"] is None


def test_items_can_be_added_unassigned_then_binned(admin):
    item = make_item(admin, name="Drill", tags=["Tools", "power"], qty=2)
    assert item["bin"] is None and [t["name"] for t in item["tags"]] == ["power", "tools"]
    unassigned = admin.get("/api/items", params={"unassigned": True}).json()
    assert [i["id"] for i in unassigned] == [item["id"]]
    b = make_bin(admin)
    moved = admin.post("/api/items/move", json={"item_ids": [item["id"]], "bin_id": b["id"]}).json()
    assert moved[0]["bin"]["code"] == b["code"]
    assert admin.get("/api/items", params={"unassigned": True}).json() == []


def test_search_and_filters(admin):
    room, zone = make_location(admin)
    b = make_bin(admin, zone_id=zone["id"], name="Holiday")
    make_item(admin, name="Fairy lights", bin_id=b["id"], tags=["xmas"])
    make_item(admin, name="Hammer", category="Tools")
    names = lambda **p: [i["name"] for i in admin.get("/api/items", params=p).json()]  # noqa: E731
    assert names(q="fairy") == ["Fairy lights"]
    assert names(q="holiday") == ["Fairy lights"]  # matches bin name
    assert names(q="xmas") == ["Fairy lights"]  # matches tag
    assert names(q="tools") == ["Hammer"]  # matches category
    assert names(room_id=room["id"]) == ["Fairy lights"]
    assert names(zone_id=zone["id"]) == ["Fairy lights"]
    assert names(tag="xmas") == ["Fairy lights"]


def test_bulk_move_is_atomic(admin):
    b1, b2 = make_bin(admin), make_bin(admin)
    a = make_item(admin, name="A", bin_id=b1["id"])
    c = make_item(admin, name="C", bin_id=b1["id"])
    r = admin.post("/api/items/move", json={"item_ids": [a["id"], c["id"], 9999], "bin_id": b2["id"]})
    assert r.status_code == 404
    assert {i["bin"]["id"] for i in admin.get("/api/items").json()} == {b1["id"]}
    r = admin.post("/api/items/move", json={"item_ids": [a["id"], c["id"]], "bin_id": b2["id"]})
    assert {i["bin"]["id"] for i in r.json()} == {b2["id"]}
    assert admin.get(f"/api/bins/{b2['id']}").json()["item_count"] == 2


def test_cannot_move_into_retired_bin(admin):
    b = make_bin(admin)
    admin.post(f"/api/bins/{b['id']}/retire", json={})
    i = make_item(admin)
    assert admin.post("/api/items/move", json={"item_ids": [i["id"]], "bin_id": b["id"]}).status_code == 409
    assert admin.post("/api/items", json={"name": "x", "bin_id": b["id"]}).status_code == 409


def test_offboard_item_and_restore(admin):
    i = make_item(admin)
    r = admin.post(f"/api/items/{i['id']}/retire", json={"reason": "donated"}).json()
    assert r["status"] == "retired" and r["retire_reason"] == "donated"
    assert admin.get("/api/items").json() == []
    assert len(admin.get("/api/items", params={"status": "retired"}).json()) == 1
    assert admin.patch(f"/api/items/{i['id']}", json={"name": "y"}).status_code == 409
    assert admin.post(f"/api/items/{i['id']}/restore").json()["status"] == "active"


def test_offboard_bin_moves_or_unassigns_contents(admin):
    b1, b2 = make_bin(admin), make_bin(admin)
    a = make_item(admin, name="A", bin_id=b1["id"])
    r = admin.post(f"/api/bins/{b1['id']}/retire", json={"contents": "move"})
    assert r.status_code == 422
    r = admin.post(
        f"/api/bins/{b1['id']}/retire",
        json={"contents": "move", "target_bin_id": b2["id"], "reason": "broken"},
    )
    assert r.json()["status"] == "retired"
    assert admin.get(f"/api/items/{a['id']}").json()["bin"]["id"] == b2["id"]
    admin.post(f"/api/bins/{b2['id']}/retire", json={"contents": "unassign"})
    assert admin.get(f"/api/items/{a['id']}").json()["bin"] is None
    assert [b["code"] for b in admin.get("/api/bins").json()] == []
    assert len(admin.get("/api/bins", params={"status": "retired"}).json()) == 2


def test_checkout_and_checkin(admin, member):
    i = make_item(admin, name="Ladder")
    r = member.post(f"/api/items/{i['id']}/checkout", json={"note": "painting"})
    assert r.status_code == 200 and r.json()["checkout"]["user"] == "member"
    assert member.post(f"/api/items/{i['id']}/checkout", json={}).status_code == 409
    assert admin.post(f"/api/items/{i['id']}/retire", json={}).status_code == 409
    assert [x["name"] for x in admin.get("/api/items", params={"checked_out": True}).json()] == ["Ladder"]
    assert len(admin.get("/api/checkouts").json()) == 1
    assert admin.post(f"/api/items/{i['id']}/checkin").json()["checkout"] is None
    assert admin.post(f"/api/items/{i['id']}/checkin").status_code == 409
    assert admin.get("/api/checkouts").json() == []
    assert len(admin.get("/api/checkouts", params={"open": False}).json()) == 1


def test_history_records_actions(admin):
    b = make_bin(admin)
    i = make_item(admin)
    admin.post("/api/items/move", json={"item_ids": [i["id"]], "bin_id": b["id"]})
    admin.post(f"/api/items/{i['id']}/checkout", json={})
    admin.post(f"/api/items/{i['id']}/checkin")
    actions = [e["action"] for e in admin.get(f"/api/items/{i['id']}/history").json()]
    assert actions == ["checked_in", "checked_out", "moved", "created"]


def test_tags_list_and_recolor(admin):
    make_item(admin, tags=["a", "b"])
    tags = admin.get("/api/tags").json()
    assert [(t["name"], t["item_count"]) for t in tags] == [("a", 1), ("b", 1)]
    r = admin.patch(f"/api/tags/{tags[0]['id']}", json={"color": "#ff0000"})
    assert r.json()["color"] == "#ff0000"


def _png(size=(40, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 10, 10)).save(buf, "PNG")
    return buf.getvalue()


def test_photo_upload_reencodes_and_serves(admin, anon):
    i = make_item(admin)
    r = admin.post(f"/api/items/{i['id']}/photo", files={"file": ("x.png", _png(), "image/png")})
    assert r.status_code == 200
    name = r.json()["photo"]
    assert name.endswith(".jpg")
    got = admin.get(f"/api/photos/{name}")
    assert got.status_code == 200 and got.content[:2] == b"\xff\xd8"
    assert anon.get(f"/api/photos/{name}").status_code == 401
    assert admin.get("/api/photos/../../etc/passwd").status_code == 404


def test_photo_rejects_non_images(admin):
    i = make_item(admin)
    r = admin.post(f"/api/items/{i['id']}/photo", files={"file": ("x.png", b"not an image", "image/png")})
    assert r.status_code == 400


def test_csv_export_escapes_formulas(admin):
    make_item(admin, name='=HYPERLINK("http://evil")')
    r = admin.get("/api/export/items.csv")
    assert r.status_code == 200
    assert "'=HYPERLINK" in r.text
