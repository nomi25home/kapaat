from fastapi.testclient import TestClient

from .conftest import login


def test_first_user_becomes_admin(admin):
    me = admin.get("/api/auth/me").json()
    assert me["user"]["role"] == "admin"
    assert me["csrf"]


def test_unknown_email_gets_no_code_after_bootstrap(anon, admin, outbox):
    r = anon.post("/api/auth/request-code", json={"email": "stranger@example.com"})
    assert r.status_code == 200  # same response, no enumeration
    assert "stranger@example.com" not in outbox


def test_invited_member_can_sign_in(member):
    me = member.get("/api/auth/me").json()
    assert me["user"]["role"] == "member"


def test_wrong_code_is_rejected_and_locked_after_five(anon, outbox):
    anon.post("/api/auth/request-code", json={"email": "a@example.com"})
    good = outbox["a@example.com"]
    bad = "000000" if good != "000000" else "111111"
    for _ in range(5):
        assert anon.post("/api/auth/verify", json={"email": "a@example.com", "code": bad}).status_code == 400
    r = anon.post("/api/auth/verify", json={"email": "a@example.com", "code": good})
    assert r.status_code == 400 and "expired" in r.json()["detail"]


def test_code_is_single_use(app, outbox):
    with TestClient(app) as c:
        login(c, outbox, "a@example.com")
        r = c.post("/api/auth/verify", json={"email": "a@example.com", "code": outbox["a@example.com"]})
        assert r.status_code == 400


def test_code_request_rate_limit(anon, outbox):
    for _ in range(5):
        assert anon.post("/api/auth/request-code", json={"email": "a@example.com"}).status_code == 200
    assert anon.post("/api/auth/request-code", json={"email": "a@example.com"}).status_code == 429


def test_requires_login(anon):
    assert anon.get("/api/items").status_code == 401


def test_csrf_required_for_session_writes(admin):
    r = admin.c.post("/api/rooms", json={"name": "Garage"})
    assert r.status_code == 403
    assert admin.post("/api/rooms", json={"name": "Garage"}).status_code == 201


def test_logout(admin):
    admin.post("/api/auth/logout")
    assert admin.get("/api/auth/me").status_code == 401


def test_member_cannot_manage_users(member):
    assert member.get("/api/users").status_code == 403
    assert member.post("/api/users", json={"email": "x@example.com"}).status_code == 403


def test_last_admin_cannot_be_demoted(admin):
    me = admin.get("/api/auth/me").json()["user"]
    r = admin.patch(f"/api/users/{me['id']}", json={"role": "member"})
    assert r.status_code == 409


def test_deactivated_user_loses_access(admin, member):
    uid = member.get("/api/auth/me").json()["user"]["id"]
    assert admin.patch(f"/api/users/{uid}", json={"active": False}).status_code == 200
    assert member.get("/api/items").status_code == 401


def test_api_tokens_scopes(admin, anon):
    read = admin.post("/api/tokens", json={"name": "ro", "scope": "read"}).json()["token"]
    write = admin.post("/api/tokens", json={"name": "rw", "scope": "write"}).json()["token"]
    h_read = {"Authorization": f"Bearer {read}"}
    h_write = {"Authorization": f"Bearer {write}"}
    assert anon.get("/api/items", headers=h_read).status_code == 200
    assert anon.post("/api/rooms", json={"name": "A"}, headers=h_read).status_code == 403
    # token writes need no CSRF header
    assert anon.post("/api/rooms", json={"name": "A"}, headers=h_write).status_code == 201
    assert anon.get("/api/items", headers={"Authorization": "Bearer kpt_nope"}).status_code == 401
    tokens = admin.get("/api/tokens").json()
    assert {t["name"] for t in tokens} == {"ro", "rw"} and "token" not in tokens[0]


def test_admin_email_restricts_bootstrap(anon, outbox, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "admin_email", "owner@example.com")
    anon.post("/api/auth/request-code", json={"email": "someone@example.com"})
    assert "someone@example.com" not in outbox
    anon.post("/api/auth/request-code", json={"email": "owner@example.com"})
    assert "owner@example.com" in outbox
