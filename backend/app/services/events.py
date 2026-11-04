from typing import Any

from sqlalchemy.orm import Session

from ..models import AppSetting, Event, User, utcnow

WEBHOOK_KEY = "webhook"


def webhook_config(db: Session) -> dict[str, Any]:
    row = db.get(AppSetting, WEBHOOK_KEY)
    return dict(row.value) if row else {}


def record(
    db: Session,
    user: User | None,
    entity: str,
    entity_id: int,
    action: str,
    payload: dict[str, Any] | None = None,
) -> Event:
    """Add an audit event; it is queued for webhook delivery only when a webhook is enabled."""
    cfg = webhook_config(db)
    queued = bool(cfg.get("enabled") and cfg.get("url"))
    ev = Event(
        user_id=user.id if user else None,
        entity=entity,
        entity_id=entity_id,
        action=action,
        payload=payload or {},
        delivered_at=None if queued else utcnow(),
    )
    db.add(ev)
    return ev
