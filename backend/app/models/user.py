"""用户模型。"""

from app.db.base import Base, IDMixin, TimestampMixin
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

# 预定义角色（与 07_Team/roles.md 对齐）
VALID_ROLES = {
    "admin",  # 超级管理员
    "director",  # 导演/编剧
    "art_director",  # AI 美术指导
    "algo_engineer",  # AI 算法工程师
    "video_operator",  # AI 视频操作员
    "post_lead",  # 后期总监
    "sound_designer",  # 声音设计师
    "qa",  # QA 质量总监
    "ops",  # 运维/部署工程师
    "pm",  # 项目制片人
    "member",  # 普通成员
}


class User(Base, IDMixin, TimestampMixin):
    """系统用户，对应团队成员。"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(64), default="")
    role: Mapped[str] = mapped_column(String(32), default="member", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
