"""认证路由 — 登录、当前用户、用户 CRUD。

JWT 通过 Authorization: Bearer <token> 传递。
登录返回 {access_token, user}；后续请求携带 token 访问受保护端点。
"""

from app.api.deps import get_current_user, require_superuser
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.user import VALID_ROLES, User
from app.schemas.common import MessageResponse
from app.schemas.user import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserOut,
    UserUpdate,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """用户名密码登录，返回 JWT。"""
    user = db.scalars(select(User).where(User.username == payload.username)).first()
    if (
        not user
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)) -> User:
    """获取当前登录用户。"""
    return current


@router.get("", response_model=list[UserOut])
def list_users(
    current: User = Depends(require_superuser),
    db: Session = Depends(get_db),
) -> list[User]:
    """列出所有用户（仅超级管理员可访问，避免邮箱被枚举）。"""
    return list(db.scalars(select(User).order_by(User.id)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_superuser),
) -> User:
    """创建新用户（仅超级管理员可调用）。

    普通成员无法自行注册；初始管理员由 init_db.py --seed 写入。
    """
    if db.scalars(select(User).where(User.username == payload.username)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    if db.scalars(select(User).where(User.email == payload.email)).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")
    if payload.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"角色无效，可选: {sorted(VALID_ROLES)}",
        )
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """更新用户信息（本人或管理员）。

    普通用户只能改自己的资料性字段（密码、全名、邮箱）；
    role / is_active 这类影响权限与状态的字段，仅超级管理员可改，
    避免普通用户自行提权或把自己停用。
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    # 仅本人或超级管理员可改
    if current.id != user_id and not current.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改他人信息")
    data = payload.model_dump(exclude_unset=True)
    if "password" in data and data["password"]:
        user.hashed_password = hash_password(data.pop("password"))
    else:
        data.pop("password", None)
    # 彏响权限/状态的敏感字段，仅超级管理员可改
    sensitive = {"role", "is_active"}
    if sensitive & data.keys() and not current.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="角色与停用状态仅管理员可改"
        )
    if "role" in data and data["role"] not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色无效")
    # 邮箱变更时查重（排除自身），避免唯一约束在 commit 时抛 IntegrityError
    if "email" in data and data["email"] != user.email:
        existing = db.scalars(
            select(User).where(User.email == data["email"], User.id != user_id)
        ).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: int,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """删除用户（仅管理员）。"""
    if user_id == current.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能删除自己")
    if not current.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可删除用户")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    db.delete(user)
    db.commit()
    return MessageResponse(message=f"用户 {user_id} 已删除")
