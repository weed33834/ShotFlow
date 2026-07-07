"""用户案例展示区 schemas。"""

from datetime import datetime
from typing import Optional

from app.schemas.common import ORMBase
from pydantic import Field


class CaseStudyBase(ORMBase):
    title: str
    slug: str
    summary: str = ""
    content_md: str = ""
    cover_image: str = ""
    author: str = ""
    status: str = "draft"
    tags: list[str] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    project_id: Optional[int] = None


class CaseStudyCreate(CaseStudyBase):
    pass


class CaseStudyUpdate(ORMBase):
    """部分更新，所有字段可选。"""

    title: Optional[str] = None
    slug: Optional[str] = None
    summary: Optional[str] = None
    content_md: Optional[str] = None
    cover_image: Optional[str] = None
    author: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[list[str]] = None
    meta: Optional[dict] = None
    project_id: Optional[int] = None


class CaseStudyOut(CaseStudyBase):
    id: int
    created_at: datetime
    updated_at: datetime
