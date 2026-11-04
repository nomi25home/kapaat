import io
from dataclasses import dataclass

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from reportlab.lib.colors import Color, black
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from .presets import Preset

CUT_GREY = Color(0.55, 0.55, 0.55)
MARK_LEN = 2.5  # mm
MARK_GAP = 0.8  # mm between a label corner and its crop mark


@dataclass
class LabelData:
    url: str
    title: str  # big text, e.g. bin code
    subtitle: str = ""  # e.g. bin name / item name
    detail: str = ""  # e.g. "Garage › North wall"


def _fit(text: str, font: str, max_size: float, min_size: float, width: float) -> tuple[str, float]:
    """Largest font size (pt) at which text fits width (pt); truncates with an ellipsis at min size."""
    size = max_size
    while size > min_size and stringWidth(text, font, size) > width:
        size -= 0.25
    if stringWidth(text, font, size) <= width:
        return text, size
    while text and stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text + "…", size


def _draw_qr(c: Canvas, url: str, x: float, y: float, side: float) -> None:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    n = len(matrix)
    cell = side / n
    c.setFillColor(black)
    for r, row in enumerate(matrix):
        run_start = None
        for col in range(n + 1):
            on = col < n and row[col]
            if on and run_start is None:
                run_start = col
            elif not on and run_start is not None:
                # One rectangle per horizontal run keeps the PDF small; tiny overlap avoids hairline gaps.
                c.rect(
                    x + run_start * cell,
                    y + side - (r + 1) * cell,
                    (col - run_start) * cell + 0.01,
                    cell + 0.01,
                    stroke=0,
                    fill=1,
                )
                run_start = None


def _draw_label(c: Canvas, data: LabelData, x: float, y: float, w: float, h: float) -> None:
    pad = min(2.0, h * 0.08) * mm
    qr_side = h - 2 * pad
    _draw_qr(c, data.url, x + pad, y + pad, qr_side)

    tx = x + pad + qr_side + pad * 1.2
    tw = w - (tx - x) - pad
    top = y + h - pad
    c.setFillColor(black)

    title, title_size = _fit(data.title, "Helvetica-Bold", min(h * 0.36, 26), 7, tw)
    lines: list[tuple[str, str, float]] = [(title, "Helvetica-Bold", title_size)]
    if data.subtitle:
        sub, sub_size = _fit(data.subtitle, "Helvetica", min(title_size * 0.55, 11), 5.5, tw)
        lines.append((sub, "Helvetica", sub_size))
    if data.detail:
        det, det_size = _fit(data.detail, "Helvetica", min(title_size * 0.42, 8.5), 5, tw)
        lines.append((det, "Helvetica", det_size))

    block = sum(size * 1.15 for _, _, size in lines)
    cursor = y + (h + block) / 2
    cursor = min(cursor, top)
    for text, font, size in lines:
        cursor -= size
        c.setFont(font, size)
        c.drawString(tx, cursor, text)
        cursor -= size * 0.15

    c.setFont("Helvetica", 4.5)
    c.setFillColor(CUT_GREY)
    c.drawRightString(x + w - pad, y + pad * 0.6, "kapaat")


def _crop_marks(c: Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setStrokeColor(CUT_GREY)
    c.setLineWidth(0.3)
    g, ln = MARK_GAP * mm, MARK_LEN * mm
    for cx, cy, sx, sy in ((x, y, -1, -1), (x + w, y, 1, -1), (x, y + h, -1, 1), (x + w, y + h, 1, 1)):
        c.line(cx + sx * g, cy, cx + sx * (g + ln), cy)
        c.line(cx, cy + sy * g, cx, cy + sy * (g + ln))
    c.setDash(1, 2)
    c.setLineWidth(0.2)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setDash()


def render_pdf(preset: Preset, labels: list[LabelData], start: int = 0, outline: bool = False) -> bytes:
    page_w, page_h = preset.page_size()
    buf = io.BytesIO()
    c = Canvas(buf, pagesize=(page_w * mm, page_h * mm))
    c.setTitle("Kapaat labels")
    c.setCreator("Kapaat")
    w, h = preset.label_w * mm, preset.label_h * mm

    slot = start % preset.per_page if preset.per_page > 1 else 0
    for i, data in enumerate(labels):
        if i and slot == 0:
            c.showPage()
        col, row = slot % preset.cols, slot // preset.cols
        x = (preset.margin_left + col * preset.pitch_x) * mm
        y = (page_h - preset.margin_top - row * preset.pitch_y) * mm - h
        _draw_label(c, data, x, y, w, h)
        if preset.crop_marks:
            _crop_marks(c, x, y, w, h)
        elif outline:
            c.setStrokeColor(CUT_GREY)
            c.setLineWidth(0.2)
            c.setDash(1, 2)
            c.rect(x, y, w, h, stroke=1, fill=0)
            c.setDash()
        slot = (slot + 1) % preset.per_page
    if not labels:
        c.setFont("Helvetica", 8)
        c.drawString(5 * mm, page_h * mm / 2, "No labels selected")
    c.showPage()
    c.save()
    return buf.getvalue()
