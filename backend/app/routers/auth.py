import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from ..config import get_settings
from ..deps import CurrentUser, Db, keyed_hash, new_csrf
from ..models import LoginCode, User, utcnow
from ..schemas import UserOut
from ..services import mail
from ..services.events import record

router = APIRouter(prefix="/api/auth", tags=["auth"])

CODE_TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
CODES_PER_WINDOW = 5
WINDOW = timedelta(minutes=15)
IP_LIMIT = 30

_ip_hits: dict[str, deque[float]] = defaultdict(deque)


def _ip_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _ip_hits[ip]
    while hits and now - hits[0] > WINDOW.total_seconds():
        hits.popleft()
    if len(hits) >= IP_LIMIT:
        retry_after = int(WINDOW.total_seconds() - (now - hits[0]))
        raise HTTPException(429, f"Too many attempts, try again in {retry_after}s")
    hits.append(now)


class CodeRequest(BaseModel):
    email: EmailStr


class CodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


def may_sign_in(db: Db, email: str) -> bool:
    s = get_settings()
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user.active
    if db.scalar(select(func.count(User.id))) == 0:
        return not s.admin_email or s.admin_email.lower() == email
    return s.open_signup


def start_session(request: Request, db: Db, user: User) -> dict:
    request.session.clear()
    request.session.update({"uid": user.id, "iat": int(time.time()), "csrf": new_csrf()})
    user.last_login_at = utcnow()
    db.commit()
    return me_payload(request, user)


def me_payload(request: Request, user: User) -> dict:
    s = get_settings()
    return {
        "user": UserOut.model_validate(user).model_dump(mode="json"),
        "csrf": request.session.get("csrf"),
        "features": {"oidc": s.oidc_enabled, "oidc_name": s.oidc_name, "passkeys": s.passkeys_enabled},
    }


def get_or_create_user(db: Db, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        return user
    first = db.scalar(select(func.count(User.id))) == 0
    user = User(email=email, name=email.split("@")[0], role="admin" if first else "member")
    db.add(user)
    db.flush()
    record(db, user, "user", user.id, "created", {"email": email, "role": user.role})
    return user


@router.get("/features")
def features() -> dict:
    s = get_settings()
    return {"oidc": s.oidc_enabled, "oidc_name": s.oidc_name, "passkeys": s.passkeys_enabled}


@router.post("/request-code")
def request_code(body: CodeRequest, request: Request, db: Db) -> dict:
    _ip_rate_limit(request)
    email = body.email.lower()
    if may_sign_in(db, email):
        oldest_recent = db.scalar(
            select(func.min(LoginCode.created_at)).where(
                LoginCode.email == email, LoginCode.created_at > utcnow() - WINDOW
            )
        )
        recent = db.scalar(
            select(func.count(LoginCode.id)).where(
                LoginCode.email == email, LoginCode.created_at > utcnow() - WINDOW
            )
        )
        if recent >= CODES_PER_WINDOW:
            retry_after = int((oldest_recent + WINDOW - utcnow()).total_seconds())
            raise HTTPException(429, f"Too many codes requested, try again in {retry_after}s")
        code = f"{secrets.randbelow(1_000_000):06d}"
        db.add(
            LoginCode(email=email, code_hash=keyed_hash(f"{email}:{code}"), expires_at=utcnow() + CODE_TTL)
        )
        db.commit()
        mail.send_login_code(email, code)
    # Same response whether or not the address is allowed, so it can't be used to probe accounts.
    return {"ok": True}


@router.post("/verify")
def verify(body: CodeVerify, request: Request, db: Db) -> dict:
    _ip_rate_limit(request)
    email = body.email.lower()
    row = db.scalar(
        select(LoginCode)
        .where(LoginCode.email == email, LoginCode.used.is_(False), LoginCode.expires_at > utcnow())
        .order_by(LoginCode.id.desc())
    )
    if not row or row.attempts >= MAX_ATTEMPTS:
        raise HTTPException(400, "Code expired or invalid, request a new one")
    if not hmac.compare_digest(row.code_hash, keyed_hash(f"{email}:{body.code}")):
        row.attempts += 1
        db.commit()
        raise HTTPException(400, "Wrong code")
    if not may_sign_in(db, email):
        raise HTTPException(403, "This email is not allowed to sign in")
    row.used = True
    user = get_or_create_user(db, email)
    return start_session(request, db, user)


@router.get("/me")
def me(request: Request, user: CurrentUser) -> dict:
    return me_payload(request, user)


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}
