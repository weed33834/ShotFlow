"""项目、角色、资产模型。"""

from typing import List, Optional

from app.db.base import Base, IDMixin, JSONType, TimestampMixin
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Project(Base, IDMixin, TimestampMixin):
    """一部短片项目（如《奇点回响》）。"""

    __tablename__ = "projects"

    title: Mapped[str] = mapped_column(String(128), index=True)
    subtitle: Mapped[str] = mapped_column(String(128), default="")
    status: Mapped[str] = mapped_column(String(32), default="planning", index=True)
    # planning / pre_production / production / post_production / release / archived
    description: Mapped[str] = mapped_column(Text, default="")
    # 项目级配置（默认参数、风格基调等）
    config: Mapped[dict] = mapped_column(JSONType, default=dict)

    characters: Mapped[List["Character"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    shots: Mapped[List["Shot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    assets: Mapped[List["Asset"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    daily_briefs: Mapped[List["DailyBrief"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Character(Base, IDMixin, TimestampMixin):
    """角色圣经条目（如艾娃）。"""

    __tablename__ = "characters"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(64), index=True)
    # 角色锚点提示词（每镜必含）
    anchor_prompt: Mapped[str] = mapped_column(Text, default="")
    # 参考图相对路径列表
    reference_images: Mapped[list] = mapped_column(JSONType, default=list)
    description: Mapped[str] = mapped_column(Text, default="")

    project: Mapped["Project"] = relationship(back_populates="characters")


class Asset(Base, IDMixin, TimestampMixin):
    """通用资产记录（图片/视频/音频/文档/模型/工作流）。"""

    __tablename__ = "assets"

    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # image / video / audio / doc / workflow / model / config
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    # 相对于仓库根的路径
    path: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(default=0)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)

    project: Mapped[Optional["Project"]] = relationship(back_populates="assets")
