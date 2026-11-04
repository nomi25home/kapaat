import io

import pytest
from pypdf import PdfReader

from app.labels.presets import PRESETS

MM = 72 / 25.4


def page_mm(reader: PdfReader, n: int = 0) -> tuple[float, float]:
    box = reader.pages[n].mediabox
    return round(float(box.width) / MM, 1), round(float(box.height) / MM, 1)


def make_bins(api, n):
    return [api.post("/api/bins", json={"name": f"Bin {i}"}).json()["id"] for i in range(n)]


def get_pdf(api, **params) -> PdfReader:
    r = api.get("/api/labels/pdf", params=params)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    return PdfReader(io.BytesIO(r.content))


def test_presets_listed_with_tape48_default(admin):
    data = admin.get("/api/labels/presets").json()
    assert data["default"] == "tape48"
    ids = {p["id"] for p in data["presets"]}
    assert {"tape48", "dk62", "a4-48", "letter-48", "a4-l7160", "letter-5160"} <= ids


def test_tape48_one_label_per_page_at_exact_size(admin):
    ids = make_bins(admin, 3)
    pdf = get_pdf(admin, bins=",".join(map(str, ids)))
    assert len(pdf.pages) == 3
    assert page_mm(pdf) == (48.0, 30.0)
    assert "B-0001" in pdf.pages[0].extract_text()


@pytest.mark.parametrize("preset", [p for p in PRESETS.values() if p.page])
def test_sheet_layouts_fit_on_page(preset):
    pw, ph = preset.page_size()
    right = preset.margin_left + (preset.cols - 1) * preset.pitch_x + preset.label_w
    bottom = preset.margin_top + (preset.rows - 1) * preset.pitch_y + preset.label_h
    assert preset.margin_left >= 0 and preset.margin_top >= 0
    assert right <= pw + 0.01 and bottom <= ph + 0.01
    if preset.crop_marks:
        assert preset.pitch_x - preset.label_w >= 3  # room for cutting between labels


def test_sheet_paginates_and_start_offset(admin):
    p = PRESETS["a4-l7160"]
    ids = make_bins(admin, p.per_page + 1)
    pdf = get_pdf(admin, bins=",".join(map(str, ids)), preset="a4-l7160")
    assert len(pdf.pages) == 2 and page_mm(pdf) == (210.0, 297.0)
    pdf = get_pdf(admin, bins=",".join(map(str, ids[:2])), preset="a4-l7160", start=p.per_page - 1)
    assert len(pdf.pages) == 2


def test_copies_and_item_labels(admin):
    b = admin.post("/api/bins", json={}).json()
    i = admin.post("/api/items", json={"name": "Glue gun", "bin_id": b["id"]}).json()
    pdf = get_pdf(admin, items=str(i["id"]), copies=2)
    assert len(pdf.pages) == 2 and "Glue gun" in pdf.pages[0].extract_text()


def test_bad_requests(admin):
    assert admin.get("/api/labels/pdf", params={"preset": "nope"}).status_code == 422
    assert admin.get("/api/labels/pdf", params={"bins": "abc"}).status_code == 422
    assert admin.get("/api/labels/pdf", params={"bins": "999"}).status_code == 404
