import os
import tempfile

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://kapaat:kapaat@localhost:5432/kapaat_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789")
os.environ.setdefault("PHOTOS_DIR", tempfile.mkdtemp(prefix="kapaat-photos-"))
os.environ.setdefault("WEBHOOK_WORKER", "false")
os.environ.setdefault("BASE_URL", "http://kapaat.test")

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.db import Base, get_engine  # noqa: E402
from app.main import create_app  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402

assert "test" in os.environ["DATABASE_URL"], "Refusing to run tests against a non-test database"


@pytest.fixture(scope="session", autouse=True)
def migrated():
    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(__file__), "..", "alembic"))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_db():
    tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with get_engine().begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        conn.execute(text("ALTER SEQUENCE bin_code_seq RESTART WITH 1"))
    auth_router._ip_hits.clear()
    yield


@pytest.fixture
def outbox(monkeypatch):
    sent: dict[str, str] = {}
    monkeypatch.setattr(
        auth_router.mail, "send_login_code", lambda email, code: sent.__setitem__(email, code)
    )
    return sent


class Api:
    """TestClient wrapper that sends the CSRF header the frontend would send."""

    def __init__(self, client: TestClient):
        self.c = client
        self.csrf = ""

    def _h(self, extra=None):
        return {"X-CSRF-Token": self.csrf, **(extra or {})}

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def post(self, url, **kw):
        return self.c.post(url, headers=self._h(kw.pop("headers", None)), **kw)

    def put(self, url, **kw):
        return self.c.put(url, headers=self._h(kw.pop("headers", None)), **kw)

    def patch(self, url, **kw):
        return self.c.patch(url, headers=self._h(kw.pop("headers", None)), **kw)

    def delete(self, url, **kw):
        return self.c.delete(url, headers=self._h(kw.pop("headers", None)), **kw)


def login(client: TestClient, outbox: dict, email: str) -> Api:
    assert client.post("/api/auth/request-code", json={"email": email}).status_code == 200
    r = client.post("/api/auth/verify", json={"email": email, "code": outbox[email]})
    assert r.status_code == 200, r.text
    api = Api(client)
    api.csrf = r.json()["csrf"]
    return api


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def anon(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin(app, outbox):
    with TestClient(app) as c:
        yield login(c, outbox, "admin@example.com")


@pytest.fixture
def member(app, outbox, admin):
    admin.post("/api/users", json={"email": "member@example.com", "role": "member"})
    with TestClient(app) as c:
        yield login(c, outbox, "member@example.com")
