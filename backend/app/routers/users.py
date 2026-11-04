import secrets

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from ..deps import AdminUser, CurrentUser, Db, hash_token
from ..models import ApiToken, User
from ..schemas import TokenCreate, TokenOut, UserCreate, UserOut, UserUpdate
from ..services.events import record

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Db, admin: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.email)))


@router.post("/users", response_model=UserOut, status_code=201)
def invite_user(body: UserCreate, db: Db, admin: AdminUser) -> User:
    email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise HTTPException(409, "That email already has an account")
    user = User(email=email, name=body.name or email.split("@")[0], role=body.role)
    db.add(user)
    db.flush()
    record(db, admin, "user", user.id, "invited", {"email": email, "role": body.role})
    db.commit()
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: Db, admin: AdminUser) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    demoting = (body.role == "member" or body.active is False) and user.role == "admin"
    if demoting:
        admins = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.active.is_(True)))
        if admins <= 1:
            raise HTTPException(409, "Kapaat needs at least one active admin")
    for field in ("name", "role", "active"):
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    record(db, admin, "user", user.id, "updated", body.model_dump(exclude_none=True))
    db.commit()
    return user


@router.patch("/me", response_model=UserOut)
def update_me(body: UserUpdate, db: Db, user: CurrentUser) -> User:
    if body.name is not None:
        user.name = body.name
    db.commit()
    return user


@router.get("/tokens", response_model=list[TokenOut])
def list_tokens(db: Db, user: CurrentUser) -> list[ApiToken]:
    return list(db.scalars(select(ApiToken).where(ApiToken.user_id == user.id).order_by(ApiToken.id)))


@router.post("/tokens", status_code=201)
def create_token(body: TokenCreate, db: Db, user: CurrentUser) -> dict:
    token = "kpt_" + secrets.token_urlsafe(32)
    row = ApiToken(user_id=user.id, name=body.name, scope=body.scope, token_hash=hash_token(token))
    db.add(row)
    db.commit()
    return {**TokenOut.model_validate(row).model_dump(mode="json"), "token": token}


@router.delete("/tokens/{token_id}", status_code=204)
def delete_token(token_id: int, db: Db, user: CurrentUser) -> None:
    row = db.get(ApiToken, token_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Token not found")
    db.delete(row)
    db.commit()
