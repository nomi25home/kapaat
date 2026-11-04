from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..labels.presets import DEFAULT_PRESET, PRESETS
from ..labels.render import LabelData, render_pdf
from ..models import Bin, Item, Zone
from ..services.queries import item_query

router = APIRouter(prefix="/api/labels", tags=["labels"])

MAX_LABELS = 600


def _ids(raw: str) -> list[int]:
    try:
        return [int(x) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise HTTPException(422, "Use comma-separated numeric ids") from exc


@router.get("/presets")
def presets(user: CurrentUser) -> dict:
    return {"default": DEFAULT_PRESET, "presets": [p.public() for p in PRESETS.values()]}


@router.get("/pdf")
def labels_pdf(
    db: Db,
    user: CurrentUser,
    bins: str = "",
    items: str = "",
    preset: str = DEFAULT_PRESET,
    start: int = Query(0, ge=0, le=99),
    copies: int = Query(1, ge=1, le=20),
    outline: bool = False,
) -> Response:
    p = PRESETS.get(preset)
    if not p:
        raise HTTPException(422, f"Unknown preset '{preset}'")
    base = get_settings().public_url
    labels: list[LabelData] = []

    bin_ids = _ids(bins)
    if bin_ids:
        rows = db.scalars(
            select(Bin).options(joinedload(Bin.zone).joinedload(Zone.room)).where(Bin.id.in_(bin_ids))
        ).all()
        by_id = {b.id: b for b in rows}
        for bid in bin_ids:
            b = by_id.get(bid)
            if not b:
                raise HTTPException(404, f"Bin {bid} not found")
            where = " › ".join(
                x for x in (b.zone.room.name if b.zone else "", b.zone.name if b.zone else "") if x
            )
            labels.append(LabelData(url=f"{base}/b/{b.code}", title=b.code, subtitle=b.name, detail=where))

    item_ids = _ids(items)
    if item_ids:
        by_id = {i.id: i for i in db.scalars(item_query().where(Item.id.in_(item_ids))).unique()}
        for iid in item_ids:
            i = by_id.get(iid)
            if not i:
                raise HTTPException(404, f"Item {iid} not found")
            labels.append(
                LabelData(
                    url=f"{base}/i/{i.id}",
                    title=i.name,
                    subtitle=i.bin.code if i.bin else "",
                    detail=i.category,
                )
            )

    labels = [lab for lab in labels for _ in range(copies)]
    if len(labels) > MAX_LABELS:
        raise HTTPException(422, f"At most {MAX_LABELS} labels per PDF")
    pdf = render_pdf(p, labels, start=start, outline=outline)
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="kapaat-labels-{p.id}.pdf"'},
    )
