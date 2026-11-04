import hashlib
import hmac
import json

import httpx

from app.db import session_factory
from app.services import webhooks


class Receiver:
    def __init__(self, status=200):
        self.status = status
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return httpx.Response(self.status)

    def client(self):
        return httpx.Client(transport=httpx.MockTransport(self))

    @property
    def bodies(self):
        return [json.loads(c.content) for c in self.calls]


def drain(rx: Receiver) -> int:
    with session_factory()() as db, rx.client() as client:
        return webhooks.deliver_pending(db, client)


def enable(api, url="https://hooks.example/kapaat"):
    r = api.put("/api/settings/webhook", json={"url": url, "enabled": True})
    assert r.status_code == 200, r.text
    return r.json()


def test_events_before_enabling_are_not_sent(admin):
    admin.post("/api/items", json={"name": "Old"})
    enable(admin)
    rx = Receiver()
    assert drain(rx) == 0


def test_signed_delivery_in_order(admin):
    cfg = enable(admin)
    b = admin.post("/api/bins", json={"name": "Tools"}).json()
    admin.post("/api/items", json={"name": "Saw", "bin_id": b["id"], "tags": ["garden"]})
    rx = Receiver()
    assert drain(rx) == 2
    assert [x["event"] for x in rx.bodies] == ["bin.created", "item.created"]
    item = rx.bodies[1]["data"]
    assert item["bin"] == b["code"] and item["tags"] == ["garden"] and rx.bodies[1]["user"] == "admin"
    req = rx.calls[0]
    expected = "sha256=" + hmac.new(cfg["secret"].encode(), req.content, hashlib.sha256).hexdigest()
    assert req.headers["x-kapaat-signature"] == expected
    assert drain(Receiver()) == 0  # nothing left


def test_failures_retry_with_backoff_then_park(admin):
    enable(admin)
    admin.post("/api/items", json={"name": "A"})
    admin.post("/api/items", json={"name": "B"})
    bad = Receiver(status=500)
    assert drain(bad) == 0
    assert len(bad.calls) == 1  # stops at first failure to keep order
    assert drain(bad) == 0 and len(bad.calls) == 1  # backoff: not retried immediately
    status = admin.get("/api/settings/webhook").json()
    assert status["pending"] == 2 and status["last_error"] == "HTTP 500"


def test_parked_events_can_be_requeued(admin):
    from sqlalchemy import update

    from app.models import Event

    enable(admin)
    admin.post("/api/items", json={"name": "A"})
    with session_factory()() as db:
        db.execute(update(Event).values(attempts=webhooks.MAX_ATTEMPTS, last_error="HTTP 500"))
        db.commit()
    assert len(admin.get("/api/settings/webhook").json()["failed"]) == 1
    assert admin.post("/api/settings/webhook/retry").json()["requeued"] == 1
    assert drain(Receiver()) == 1


def test_snapshot_contains_inventory(admin):
    enable(admin)
    admin.post("/api/items", json={"name": "Lamp"})
    drain(Receiver())
    assert admin.post("/api/settings/webhook/snapshot").json() == {"queued": True, "items": 1, "bins": 0}
    rx = Receiver()
    drain(rx)
    assert rx.bodies[0]["event"] == "inventory.snapshot"
    assert rx.bodies[0]["data"]["items"][0]["name"] == "Lamp"


def test_webhook_settings_admin_only_and_validated(admin, member):
    assert member.get("/api/settings/webhook").status_code == 403
    assert admin.put("/api/settings/webhook", json={"url": "ftp://x", "enabled": True}).status_code == 422
    assert admin.put("/api/settings/webhook", json={"url": "", "enabled": True}).status_code == 422
    first = enable(admin)["secret"]
    again = admin.put(
        "/api/settings/webhook", json={"url": "https://h.example", "enabled": True, "regenerate_secret": True}
    ).json()["secret"]
    assert first and again and first != again
