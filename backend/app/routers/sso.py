"""Optional sign-in methods: OIDC (enabled by OIDC_* env) and passkeys (enabled by WEBAUTHN_RP_ID)."""

import json
import logging
from functools import lru_cache

from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..models import Passkey, User
from ..services.events import record
from .auth import _ip_rate_limit, get_or_create_user, start_session

log = logging.getLogger("kapaat.sso")
router = APIRouter(prefix="/api/auth", tags=["sso"])


# ── OIDC ─────────────────────────────────────────────────────────────────────
@lru_cache
def oauth() -> OAuth:
    s = get_settings()
    o = OAuth()
    o.register(
        "oidc",
        client_id=s.oidc_client_id,
        client_secret=s.oidc_client_secret,
        server_metadata_url=s.oidc_issuer.rstrip("/") + "/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return o


def _require_oidc() -> None:
    if not get_settings().oidc_enabled:
        raise HTTPException(404, "Single sign-on is not configured")


@router.get("/oidc/login")
async def oidc_login(request: Request):
    _require_oidc()
    _ip_rate_limit(request)
    return await oauth().oidc.authorize_redirect(
        request, get_settings().public_url + "/api/auth/oidc/callback"
    )


@router.get("/oidc/callback")
async def oidc_callback(request: Request, db: Db):
    _require_oidc()
    _ip_rate_limit(request)
    s = get_settings()
    try:
        token = await oauth().oidc.authorize_access_token(request)
    except OAuthError as exc:
        log.warning("OIDC callback failed: %s", exc.error)
        return RedirectResponse("/login?error=sso_failed", status_code=302)
    info = token.get("userinfo") or {}
    email = (info.get("email") or "").lower()
    if not email or info.get("email_verified") is False:
        return RedirectResponse("/login?error=sso_no_email", status_code=302)

    user = db.scalar(select(User).where(User.email == email))
    if user and not user.active:
        return RedirectResponse("/login?error=not_allowed", status_code=302)
    if not user:
        first = db.scalar(select(func.count(User.id))) == 0
        if not (first or s.open_signup):
            return RedirectResponse("/login?error=not_invited", status_code=302)
        user = get_or_create_user(db, email)
        user.name = info.get("name") or user.name
    if s.oidc_admin_group:
        groups = info.get("groups") or []
        if s.oidc_admin_group in groups:
            user.role = "admin"
    start_session(request, db, user)
    return RedirectResponse("/", status_code=302)


# ── Passkeys ─────────────────────────────────────────────────────────────────
def _rp() -> tuple[str, str]:
    s = get_settings()
    if not s.passkeys_enabled:
        raise HTTPException(404, "Passkeys are not configured")
    return s.webauthn_rp_id, s.public_url


class PasskeyName(BaseModel):
    name: str = Field(default="Passkey", max_length=80)


@router.get("/passkeys")
def list_passkeys(db: Db, user: CurrentUser) -> list[dict]:
    rows = db.scalars(select(Passkey).where(Passkey.user_id == user.id).order_by(Passkey.id))
    return [{"id": p.id, "name": p.name, "created_at": p.created_at} for p in rows]


@router.post("/passkeys/register/options")
def passkey_register_options(request: Request, db: Db, user: CurrentUser) -> dict:
    rp_id, _ = _rp()
    existing = db.scalars(select(Passkey.credential_id).where(Passkey.user_id == user.id)).all()
    opts = generate_registration_options(
        rp_id=rp_id,
        rp_name=get_settings().webauthn_rp_name,
        user_id=str(user.id).encode(),
        user_name=user.email,
        user_display_name=user.name or user.email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.REQUIRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=c) for c in existing],
    )
    request.session["webauthn_reg"] = bytes_to_base64url(opts.challenge)
    return json.loads(options_to_json(opts))


@router.post("/passkeys/register")
async def passkey_register(request: Request, db: Db, user: CurrentUser, name: str = "Passkey") -> dict:
    rp_id, origin = _rp()
    challenge = request.session.pop("webauthn_reg", None)
    if not challenge:
        raise HTTPException(400, "Start passkey registration again")
    try:
        verified = verify_registration_response(
            credential=await request.json(),
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=rp_id,
            expected_origin=origin,
        )
    except InvalidRegistrationResponse as exc:
        raise HTTPException(400, f"Passkey registration failed: {exc}") from exc
    pk = Passkey(
        user_id=user.id,
        name=name[:80] or "Passkey",
        credential_id=verified.credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
    )
    db.add(pk)
    record(db, user, "user", user.id, "passkey_added", {"name": pk.name})
    db.commit()
    return {"id": pk.id, "name": pk.name}


@router.delete("/passkeys/{passkey_id}", status_code=204)
def passkey_delete(passkey_id: int, db: Db, user: CurrentUser) -> None:
    pk = db.get(Passkey, passkey_id)
    if not pk or pk.user_id != user.id:
        raise HTTPException(404, "Passkey not found")
    db.delete(pk)
    db.commit()


@router.post("/passkeys/login/options")
def passkey_login_options(request: Request) -> dict:
    rp_id, _ = _rp()
    _ip_rate_limit(request)
    opts = generate_authentication_options(
        rp_id=rp_id, user_verification=UserVerificationRequirement.PREFERRED
    )
    request.session["webauthn_auth"] = bytes_to_base64url(opts.challenge)
    return json.loads(options_to_json(opts))


@router.post("/passkeys/login")
async def passkey_login(request: Request, db: Db) -> dict:
    rp_id, origin = _rp()
    _ip_rate_limit(request)
    challenge = request.session.pop("webauthn_auth", None)
    if not challenge:
        raise HTTPException(400, "Start passkey sign-in again")
    body = await request.json()
    try:
        raw_id = base64url_to_bytes(body.get("rawId") or body.get("id") or "")
    except Exception as exc:
        raise HTTPException(400, "Malformed passkey response") from exc
    pk = db.scalar(select(Passkey).where(Passkey.credential_id == raw_id))
    if not pk:
        raise HTTPException(400, "Unknown passkey")
    try:
        verified = verify_authentication_response(
            credential=body,
            expected_challenge=base64url_to_bytes(challenge),
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=pk.public_key,
            credential_current_sign_count=pk.sign_count,
        )
    except InvalidAuthenticationResponse as exc:
        raise HTTPException(400, "Passkey sign-in failed") from exc
    user = db.get(User, pk.user_id)
    if not user or not user.active:
        raise HTTPException(403, "This account is disabled")
    pk.sign_count = verified.new_sign_count
    return start_session(request, db, user)
