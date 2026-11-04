import pytest

from app.config import get_settings
from app.routers import sso


def test_optional_methods_disabled_by_default(anon, admin):
    assert anon.get("/api/auth/features").json() == {
        "oidc": False,
        "oidc_name": "Single sign-on",
        "passkeys": False,
    }
    assert anon.get("/api/auth/oidc/login", follow_redirects=False).status_code == 404
    assert anon.post("/api/auth/passkeys/login/options").status_code == 404
    assert admin.post("/api/auth/passkeys/register/options").status_code == 404


@pytest.fixture
def passkeys_on(monkeypatch):
    monkeypatch.setattr(get_settings(), "webauthn_rp_id", "kapaat.test")


def test_passkey_options_issue_challenges(passkeys_on, admin, anon):
    reg = admin.post("/api/auth/passkeys/register/options").json()
    assert reg["rp"]["id"] == "kapaat.test" and reg["challenge"]
    assert reg["authenticatorSelection"]["residentKey"] == "required"
    login = anon.post("/api/auth/passkeys/login/options").json()
    assert login["rpId"] == "kapaat.test" and login["challenge"]


def test_passkey_login_rejects_without_challenge_or_unknown_key(passkeys_on, anon):
    assert anon.post("/api/auth/passkeys/login", json={"id": "AAAA"}).status_code == 400
    anon.post("/api/auth/passkeys/login/options")
    assert anon.post("/api/auth/passkeys/login", json={"id": "AAAA", "rawId": "AAAA"}).status_code == 400


@pytest.fixture
def oidc(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "oidc_issuer", "https://idp.example")
    monkeypatch.setattr(s, "oidc_client_id", "kapaat")
    monkeypatch.setattr(s, "oidc_client_secret", "shh")
    monkeypatch.setattr(s, "oidc_admin_group", "kapaat-admins")
    userinfo = {}

    class FakeClient:
        async def authorize_access_token(self, request):
            return {"userinfo": dict(userinfo)}

    class FakeOAuth:
        oidc = FakeClient()

    monkeypatch.setattr(sso, "oauth", lambda: FakeOAuth())
    return userinfo


def test_oidc_first_user_and_invites(oidc, app):
    from fastapi.testclient import TestClient

    oidc.update(email="Owner@Example.com", email_verified=True, name="Owner")
    with TestClient(app) as c:
        r = c.get("/api/auth/oidc/callback", follow_redirects=False)
        assert r.status_code == 302 and r.headers["location"] == "/"
        me = c.get("/api/auth/me").json()["user"]
        assert me["email"] == "owner@example.com" and me["role"] == "admin" and me["name"] == "Owner"

    oidc.update(email="stranger@example.com", name="S")
    with TestClient(app) as c:
        r = c.get("/api/auth/oidc/callback", follow_redirects=False)
        assert r.headers["location"] == "/login?error=not_invited"
        assert c.get("/api/auth/me").status_code == 401


def test_oidc_admin_group_and_unverified_email(oidc, app, admin):
    from fastapi.testclient import TestClient

    admin.post("/api/users", json={"email": "m@example.com"})
    oidc.update(email="m@example.com", email_verified=True, groups=["kapaat-admins"])
    with TestClient(app) as c:
        c.get("/api/auth/oidc/callback", follow_redirects=False)
        assert c.get("/api/auth/me").json()["user"]["role"] == "admin"

    oidc.update(email="m@example.com", email_verified=False)
    with TestClient(app) as c:
        r = c.get("/api/auth/oidc/callback", follow_redirects=False)
        assert r.headers["location"] == "/login?error=sso_no_email"
