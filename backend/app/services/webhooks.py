import asyncio
import hashlib
import hmac
import json
import logging
from datetime import timedelta
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import session_factory
from ..models import Event, User, utcnow
from .events import webhook_config

log = logging.getLogger("kapaat.webhooks")

MAX_ATTEMPTS = 8
BATCH = 50
POLL_SECONDS = 5


def sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def envelope(ev: Event, user_label: str | None) -> dict[str, Any]:
    return {
        "id": ev.id,
        "event": f"{ev.entity}.{ev.action}",
        "entity": ev.entity,
        "entity_id": ev.entity_id,
        "action": ev.action,
        "at": ev.at.isoformat(),
        "user": user_label,
        "data": ev.payload,
    }


def post(client: httpx.Client, cfg: dict, body: dict) -> httpx.Response:
    raw = json.dumps(body, separators=(",", ":"), default=str).encode()
    return client.post(
        cfg["url"],
        content=raw,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Kapaat-Webhook/2",
            "X-Kapaat-Event": body["event"],
            "X-Kapaat-Signature": sign(cfg.get("secret", ""), raw),
        },
    )


def backoff(attempts: int) -> timedelta:
    return timedelta(seconds=min(30 * 2 ** (attempts - 1), 6 * 3600))


def deliver_pending(db: Session, client: httpx.Client) -> int:
    cfg = webhook_config(db)
    if not (cfg.get("enabled") and cfg.get("url")):
        return 0
    pending = (Event.delivered_at.is_(None), Event.attempts < MAX_ATTEMPTS)
    head = db.scalar(select(Event.next_attempt_at).where(*pending).order_by(Event.id).limit(1))
    if head and head > utcnow():
        return 0  # the oldest event is backing off; later events wait so receivers see them in order
    rows = db.execute(
        select(Event, User.name, User.email)
        .outerjoin(User, Event.user_id == User.id)
        .where(*pending)
        .order_by(Event.id)
        .limit(BATCH)
        .with_for_update(of=Event, skip_locked=True)
    ).all()
    sent = 0
    for ev, name, email in rows:
        try:
            resp = post(client, cfg, envelope(ev, name or email))
            ok, err = resp.is_success, f"HTTP {resp.status_code}"
        except httpx.HTTPError as exc:
            ok, err = False, f"{type(exc).__name__}: {exc}"[:300]
        if ok:
            ev.delivered_at = utcnow()
            sent += 1
        else:
            ev.attempts += 1
            ev.last_error = err
            ev.next_attempt_at = utcnow() + backoff(ev.attempts)
            db.commit()
            break  # keep ordering: don't send later events while an earlier one is failing
    db.commit()
    return sent


def _client() -> httpx.Client:
    return httpx.Client(timeout=15, follow_redirects=True)


async def worker(stop: asyncio.Event) -> None:
    def tick() -> None:
        with session_factory()() as db, _client() as client:
            deliver_pending(db, client)

    while not stop.is_set():
        try:
            await asyncio.to_thread(tick)
        except Exception:  # keep the worker alive through DB restarts etc.
            log.exception("webhook delivery failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_SECONDS)
        except TimeoutError:
            pass
