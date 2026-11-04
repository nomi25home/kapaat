from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

HexColor = Field(default="#4cd7f6", pattern=r"^#[0-9a-fA-F]{6}$")


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(Orm):
    id: int
    email: str
    name: str
    role: str
    active: bool
    created_at: datetime
    last_login_at: datetime | None


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(default="", max_length=120)
    role: Literal["admin", "member"] = "member"


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    role: Literal["admin", "member"] | None = None
    active: bool | None = None


class TokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    scope: Literal["read", "write"] = "read"


class TokenOut(Orm):
    id: int
    name: str
    scope: str
    created_at: datetime
    last_used_at: datetime | None


# ── Locations ────────────────────────────────────────────────────────────────
class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    notes: str = ""


class ZoneIn(BaseModel):
    room_id: int
    name: str = Field(min_length=1, max_length=80)


class ZoneUpdate(BaseModel):
    room_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)


class ZoneOut(Orm):
    id: int
    room_id: int
    name: str
    bin_count: int = 0


class RoomOut(Orm):
    id: int
    name: str
    notes: str
    zones: list[ZoneOut] = []


class Location(BaseModel):
    room_id: int | None = None
    room: str | None = None
    zone_id: int | None = None
    zone: str | None = None


# ── Bins ─────────────────────────────────────────────────────────────────────
class BinIn(BaseModel):
    name: str = Field(default="", max_length=120)
    code: str | None = Field(default=None, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
    zone_id: int | None = None
    color: str = HexColor
    notes: str = ""


class BinUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    zone_id: int | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    notes: str | None = None
    clear_zone: bool = False


class BinOut(BaseModel):
    id: int
    code: str
    name: str
    color: str
    notes: str
    photo: str | None
    status: str
    created_at: datetime
    retired_at: datetime | None
    retire_reason: str
    location: Location
    item_count: int = 0


class BinRetire(BaseModel):
    reason: str = Field(default="", max_length=200)
    contents: Literal["move", "unassign"] = "unassign"
    target_bin_id: int | None = None


# ── Items ────────────────────────────────────────────────────────────────────
class TagOut(Orm):
    id: int
    name: str
    color: str


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class CheckoutOut(BaseModel):
    id: int
    item_id: int
    user: str | None
    out_at: datetime
    due_at: datetime | None
    in_at: datetime | None
    note: str


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="", max_length=80)
    qty: int = Field(default=1, ge=0, le=1_000_000)
    notes: str = ""
    bin_id: int | None = None
    tags: list[str] = []


class ItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=80)
    qty: int | None = Field(default=None, ge=0, le=1_000_000)
    notes: str | None = None
    tags: list[str] | None = None


class BinRef(BaseModel):
    id: int
    code: str
    name: str
    color: str


class ItemOut(BaseModel):
    id: int
    name: str
    category: str
    qty: int
    notes: str
    photo: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    retired_at: datetime | None
    retire_reason: str
    bin: BinRef | None
    location: Location
    tags: list[TagOut]
    checkout: CheckoutOut | None


class Retire(BaseModel):
    reason: str = Field(default="", max_length=200)


class MoveItems(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=1000)
    bin_id: int | None = None


class CheckoutIn(BaseModel):
    due_at: datetime | None = None
    note: str = Field(default="", max_length=300)


class EventOut(BaseModel):
    id: int
    at: datetime
    user: str | None
    entity: str
    entity_id: int
    action: str
    payload: dict


class WebhookIn(BaseModel):
    url: str = Field(default="", max_length=500)
    enabled: bool = False
    regenerate_secret: bool = False
