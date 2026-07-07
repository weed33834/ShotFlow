"""用户与认证 schemas。"""

from datetime import datetime
from typing import Optional

from app.schemas.common import ORMBase
from pydantic import EmailStr, Field


class UserOut(ORMBase):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(ORMBase):
    username: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = ""
    role: str = "member"


class UserUpdate(ORMBase):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)  # 传则改密


class LoginRequest(ORMBase):
    username: str
    password: str


class TokenResponse(ORMBase):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
