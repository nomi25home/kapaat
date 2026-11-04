from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Sequence,
    String,
    Table,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


Timestamp = DateTime(timezone=True)

bin_code_seq = Sequence("bin_code_seq", start=1)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    role: Mapped[str] = mapped_column(String(16), default="member")  # admin | member
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(Timestamp)


class LoginCode(Base):
    __tablename__ = "login_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    code_hash: Mapped[str] = mapped_column(String(128))
    expires_at: Mapped[datetime] = mapped_column(Timestamp)
    attempts: Mapped[int] = mapped_column(default=0)
    used: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)


class Passkey(Base):
    __tablename__ = "passkeys"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80), default="Passkey")
    credential_id: Mapped[bytes] = mapped_column(LargeBinary, unique=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)


class ApiToken(Base):
    __tablename__ = "api_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    scope: Mapped[str] = mapped_column(String(8), default="read")  # read | write
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(Timestamp)
    user: Mapped[User] = relationship()


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    zones: Mapped[list["Zone"]] = relationship(back_populates="room", order_by="Zone.name")


class Zone(Base):
    __tablename__ = "zones"
    __table_args__ = (UniqueConstraint("room_id", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    room: Mapped[Room] = relationship(back_populates="zones")


class Bin(Base):
    __tablename__ = "bins"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zones.id", ondelete="RESTRICT"), index=True)
    color: Mapped[str] = mapped_column(String(9), default="#4cd7f6")
    notes: Mapped[str] = mapped_column(Text, default="")
    photo: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(10), default="active")
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    retired_at: Mapped[datetime | None] = mapped_column(Timestamp)
    retire_reason: Mapped[str] = mapped_column(String(200), default="")
    zone: Mapped[Zone | None] = relationship()


item_tags = Table(
    "item_tags",
    Base.metadata,
    Column("item_id", ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    color: Mapped[str] = mapped_column(String(9), default="#869397")


class Item(Base):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(80), default="")
    qty: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, default="")
    bin_id: Mapped[int | None] = mapped_column(ForeignKey("bins.id", ondelete="RESTRICT"), index=True)
    photo: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(10), default="active")
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)
    retired_at: Mapped[datetime | None] = mapped_column(Timestamp)
    retire_reason: Mapped[str] = mapped_column(String(200), default="")
    bin: Mapped[Bin | None] = relationship()
    tags: Mapped[list[Tag]] = relationship(secondary=item_tags, order_by="Tag.name")
    open_checkout: Mapped["Checkout | None"] = relationship(
        primaryjoin="and_(Checkout.item_id == Item.id, Checkout.in_at.is_(None))",
        viewonly=True,
        uselist=False,
    )


class Checkout(Base):
    __tablename__ = "checkouts"
    __table_args__ = (
        Index(
            "one_open_checkout_per_item",
            "item_id",
            unique=True,
            postgresql_where=text("in_at IS NULL"),
            sqlite_where=text("in_at IS NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    out_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    due_at: Mapped[datetime | None] = mapped_column(Timestamp)
    in_at: Mapped[datetime | None] = mapped_column(Timestamp)
    note: Mapped[str] = mapped_column(String(300), default="")
    user: Mapped[User | None] = relationship()


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    entity: Mapped[str] = mapped_column(String(16))
    entity_id: Mapped[int] = mapped_column()
    action: Mapped[str] = mapped_column(String(24))
    payload: Mapped[dict] = mapped_column(JsonType, default=dict)
    delivered_at: Mapped[datetime | None] = mapped_column(Timestamp)
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_error: Mapped[str] = mapped_column(String(300), default="")


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JsonType, default=dict)
