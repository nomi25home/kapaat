import hashlib
import hmac
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .models import ApiToken, User, utcnow

Db = Annotated[Session, Depends(get_db)]

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def keyed_hash(value: str) -> str:
    return hmac.new(get_settings().secret_key.encode(), value.encode(), hashlib.sha256).hexdigest()


def new_csrf() -> str:
    return secrets.token_urlsafe(24)


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return None


def _user_from_token(db: Session, token: str, request: Request) -> User:
    row = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(token)))
    if not row or not row.user.active:
        raise HTTPException(401, "Invalid API token")
    if request.method in UNSAFE_METHODS and row.scope != "write":
        raise HTTPException(403, "Token is read-only")
    row.last_used_at = utcnow()
    db.commit()
    request.state.auth = "token"
    return row.user


def current_user(request: Request, db: Db) -> User:
    token = _bearer(request)
    if token:
        return _user_from_token(db, token, request)

    uid = request.session.get("uid")
    if not uid:
        raise HTTPException(401, "Not signed in")
    issued = request.session.get("iat", 0)
    if datetime.now().timestamp() - issued > get_settings().session_days * 86400:
        request.session.clear()
        raise HTTPException(401, "Session expired")
    user = db.get(User, uid)
    if not user or not user.active:
        request.session.clear()
        raise HTTPException(401, "Not signed in")

    if request.method in UNSAFE_METHODS:
        sent = request.headers.get("x-csrf-token", "")
        expected = request.session.get("csrf", "")
        if not expected or not hmac.compare_digest(sent, expected):
            raise HTTPException(403, "CSRF token missing or invalid")
    request.state.auth = "session"
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def admin_user(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return user


AdminUser = Annotated[User, Depends(admin_user)]
