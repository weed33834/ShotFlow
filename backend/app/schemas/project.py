"""项目相关 schemas。"""

from datetime import datetime
from typing import Optional

from app.schemas.common import ORMBase


class ProjectBase(ORMBase):
    title: str
    subtitle: str = ""
    status: str = "planning"
    description: str = ""
    config: dict = {}


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(ORMBase):
    """部分更新，所有字段可选。"""

    title: Optional[str] = None
    subtitle: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict] = None


class ProjectOut(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime


class CharacterBase(ORMBase):
    name: str
    anchor_prompt: str = ""
    reference_images: list = []
    description: str = ""


class CharacterCreate(CharacterBase):
    project_id: int


class CharacterOut(CharacterBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class AssetBase(ORMBase):
    asset_type: str
    path: str
    filename: str
    size_bytes: int = 0
    checksum: str = ""
    tags: list = []
    meta: dict = {}


class AssetCreate(AssetBase):
    project_id: Optional[int] = None


class AssetOut(AssetBase):
    id: int
    project_id: Optional[int]
    created_at: datetime
    updated_at: datetime
