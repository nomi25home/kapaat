import csv
import io
from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ..deps import CurrentUser, Db
from ..models import Item
from ..services.queries import item_query
from ..services.serialize import item_snapshot

router = APIRouter(prefix="/api/export", tags=["export"])

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
COLUMNS = ["id", "name", "category", "qty", "bin", "room", "zone", "tags", "checked_out", "status", "notes"]


def safe_cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


@router.get("/items.csv")
def export_items(db: Db, user: CurrentUser, include_retired: bool = False) -> StreamingResponse:
    stmt = item_query().order_by(Item.id)
    if not include_retired:
        stmt = stmt.where(Item.status == "active")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for item in db.scalars(stmt).unique():
        row = item_snapshot(item)
        row["tags"] = ", ".join(row["tags"])
        writer.writerow({k: safe_cell(v) for k, v in row.items()})
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="kapaat-items-{stamp}.csv"'},
    )
