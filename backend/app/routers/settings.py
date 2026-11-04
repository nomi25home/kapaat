import secrets
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, update

from ..deps import AdminUser, Db
from ..models import AppSetting, Bin, Event, Item, utcnow
from ..schemas import WebhookIn
from ..services import webhooks
from ..services.events import WEBHOOK_KEY, record, webhook_config
from ..services.queries import item_query
from ..services.serialize import bin_snapshot, item_snapshot

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _status(db: Db, cfg: dict) -> dict:
    pending = db.scalar(
        select(func.count(Event.id)).where(
            Event.delivered_at.is_(None), Event.attempts < webhooks.MAX_ATTEMPTS
        )
    )
    failed = db.scalars(
        select(Event)
        .where(Event.delivered_at.is_(None), Event.attempts >= webhooks.MAX_ATTEMPTS)
        .order_by(Event.id.desc())
        .limit(20)
    ).all()
    last_error = db.scalar(
        select(Event.last_error).where(Event.last_error != "").order_by(Event.id.desc()).limit(1)
    )
    return {
        "url": cfg.get("url", ""),
        "enabled": bool(cfg.get("enabled")),
        "secret": cfg.get("secret", ""),
        "pending": pending,
        "last_error": last_error or "",
        "failed": [
            {"id": e.id, "event": f"{e.entity}.{e.action}", "at": e.at, "error": e.last_error} for e in failed
        ],
    }


@router.get("/webhook")
def get_webhook(db: Db, admin: AdminUser) -> dict:
    return _status(db, webhook_config(db))


@router.put("/webhook")
def put_webhook(body: WebhookIn, db: Db, admin: AdminUser) -> dict:
    url = body.url.strip()
    if url and urlparse(url).scheme not in {"http", "https"}:
        raise HTTPException(422, "Webhook URL must start with http:// or https://")
    if body.enabled and not url:
        raise HTTPException(422, "Set a URL before enabling the webhook")
    row = db.get(AppSetting, WEBHOOK_KEY) or AppSetting(key=WEBHOOK_KEY, value={})
    cfg = dict(row.value)
    if body.regenerate_secret or not cfg.get("secret"):
        cfg["secret"] = secrets.token_urlsafe(24)
    if body.enabled and not cfg.get("enabled"):
        # Only events from now on are sent; older history isn't replayed (use "send snapshot" for that).
        db.execute(update(Event).where(Event.delivered_at.is_(None)).values(delivered_at=utcnow()))
    cfg.update(url=url, enabled=body.enabled)
    row.value = cfg
    db.merge(row)
    db.commit()
    return _status(db, cfg)


@router.post("/webhook/test")
def test_webhook(db: Db, admin: AdminUser) -> dict:
    cfg = webhook_config(db)
    if not cfg.get("url"):
        raise HTTPException(422, "Set a webhook URL first")
    body = {
        "id": 0,
        "event": "kapaat.ping",
        "entity": "kapaat",
        "entity_id": 0,
        "action": "ping",
        "at": utcnow().isoformat(),
        "user": admin.email,
        "data": {"message": "Hello from Kapaat"},
    }
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            resp = webhooks.post(client, cfg, body)
    except httpx.HTTPError as exc:
        return {"ok": False, "status": None, "error": str(exc)[:300]}
    return {
        "ok": resp.is_success,
        "status": resp.status_code,
        "error": "" if resp.is_success else resp.text[:300],
    }


@router.post("/webhook/snapshot")
def snapshot(db: Db, admin: AdminUser) -> dict:
    cfg = webhook_config(db)
    if not (cfg.get("enabled") and cfg.get("url")):
        raise HTTPException(422, "Enable the webhook first")
    items = [item_snapshot(i) for i in db.scalars(item_query().where(Item.status == "active")).unique()]
    bins = [bin_snapshot(b) for b in db.scalars(select(Bin).where(Bin.status == "active").order_by(Bin.code))]
    record(db, admin, "inventory", 0, "snapshot", {"items": items, "bins": bins})
    db.commit()
    return {"queued": True, "items": len(items), "bins": len(bins)}


@router.post("/webhook/retry")
def retry_failed(db: Db, admin: AdminUser) -> dict:
    n = db.execute(
        update(Event)
        .where(Event.delivered_at.is_(None), Event.attempts >= webhooks.MAX_ATTEMPTS)
        .values(attempts=0, next_attempt_at=None)
    ).rowcount
    db.commit()
    return {"requeued": n}
