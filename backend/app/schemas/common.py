"""通用 schemas：统一响应、分页、健康检查。"""

from datetime import datetime
from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    """带 ORM 模式的基础 schema。"""

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """统一消息响应。"""

    message: str
    ok: bool = True


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    app: str
    version: str
    db: str
    redis: str
    timestamp: datetime


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应。"""

    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
