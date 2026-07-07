"""用户案例展示区模型：CaseStudy。"""

from typing import Optional

from app.db.base import Base, IDMixin, JSONType, TimestampMixin
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class CaseStudy(Base, IDMixin, TimestampMixin):
    """用户案例展示区 —— 社区化内容，公开浏览已发布案例。"""

    __tablename__ = "case_studies"

    title: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # 公开访问的 URL 标识，全小写 + 连字符
    slug: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    # 一句话摘要，列表展示用
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    # Markdown 正文
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 封面图路径
    cover_image: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    # 作者署名
    author: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # draft / published / archived
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="draft", index=True)
    # 标签数组，如 ["AIGC","短片"]
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    # 扩展元数据，如视频链接、制作周期
    meta: Mapped[dict] = mapped_column(JSONType, default=dict)
    # 可选关联项目
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
