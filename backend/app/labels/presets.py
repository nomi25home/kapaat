from dataclasses import asdict, dataclass

A4 = (210.0, 297.0)
LETTER = (215.9, 279.4)


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    label_w: float  # mm
    label_h: float
    page: tuple[float, float] | None = None  # None: page is the label itself (label makers / rolls)
    cols: int = 1
    rows: int = 1
    margin_left: float = 0.0
    margin_top: float = 0.0
    pitch_x: float = 0.0  # distance between left edges of neighbouring labels
    pitch_y: float = 0.0
    crop_marks: bool = False

    @property
    def per_page(self) -> int:
        return self.cols * self.rows

    def page_size(self) -> tuple[float, float]:
        return self.page or (self.label_w, self.label_h)

    def public(self) -> dict:
        d = asdict(self)
        d["per_page"] = self.per_page
        d["page"] = list(self.page_size())
        return d


def _plain_sheet(
    pid: str, name: str, page: tuple[float, float], w: float, h: float, gutter: float = 4.0
) -> Preset:
    margin = 10.0
    cols = int((page[0] - 2 * margin + gutter) // (w + gutter))
    rows = int((page[1] - 2 * margin + gutter) // (h + gutter))
    used_w = cols * w + (cols - 1) * gutter
    used_h = rows * h + (rows - 1) * gutter
    return Preset(
        id=pid,
        name=name,
        description=f"{w:g} × {h:g} mm on plain paper, {cols * rows} per sheet, with crop marks for cutting.",
        label_w=w,
        label_h=h,
        page=page,
        cols=cols,
        rows=rows,
        margin_left=(page[0] - used_w) / 2,
        margin_top=(page[1] - used_h) / 2,
        pitch_x=w + gutter,
        pitch_y=h + gutter,
        crop_marks=True,
    )


PRESETS: dict[str, Preset] = {
    p.id: p
    for p in (
        Preset(
            id="tape48",
            name="48 mm tape label",
            description="48 × 30 mm, one label per page. Fits under 48 mm clear packing tape; "
            "use with a label maker or print and trim.",
            label_w=48,
            label_h=30,
        ),
        Preset(
            id="dk62",
            name="Brother DK 62 mm",
            description="62 × 29 mm, one label per page (Brother DK-11209 / DK-22205 continuous).",
            label_w=62,
            label_h=29,
        ),
        _plain_sheet("a4-48", "A4 plain paper — 48 mm labels", A4, 48, 30),
        _plain_sheet("letter-48", "Letter plain paper — 48 mm labels", LETTER, 48, 30),
        Preset(
            id="a4-l7160",
            name="A4 Avery L7160 (21 per sheet)",
            description="63.5 × 38.1 mm sticker sheets, 3 × 7.",
            label_w=63.5,
            label_h=38.1,
            page=A4,
            cols=3,
            rows=7,
            margin_left=7.25,
            margin_top=15.15,
            pitch_x=66.04,
            pitch_y=38.1,
        ),
        Preset(
            id="letter-5160",
            name="Letter Avery 5160 (30 per sheet)",
            description="66.7 × 25.4 mm (2⅝ × 1 in) sticker sheets, 3 × 10.",
            label_w=66.675,
            label_h=25.4,
            page=LETTER,
            cols=3,
            rows=10,
            margin_left=4.7625,
            margin_top=12.7,
            pitch_x=69.85,
            pitch_y=25.4,
        ),
    )
}

DEFAULT_PRESET = "tape48"
