"""流水线 schemas：工作流、渲染任务、质检、日报。"""

from datetime import date, datetime
from typing import Literal, Optional

from app.schemas.common import ORMBase
from pydantic import Field


class WorkflowBase(ORMBase):
    name: str
    file_path: str = ""
    description: str = ""
    parameters: dict = {}
    node_dependencies: list = []


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowOut(WorkflowBase):
    id: int
    created_at: datetime
    updated_at: datetime


# ===== 渲染任务 =====
# 任务类型与状态常量（与模型层对齐）
TASK_TYPES = {"keyframe", "video_i2v", "video_t2v", "kling", "tts", "music"}
TASK_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}


class RenderTaskCreate(ORMBase):
    """提交渲染任务。

    task_type 决定走哪条生成链路：
      keyframe   -> Flux 关键帧（ComfyUI）
      video_i2v  -> Wan2.2 图生视频（ComfyUI）
      video_t2v  -> Wan2.2 文生视频（ComfyUI）
      kling      -> 可灵复杂镜头（云端 API）
      tts        -> ElevenLabs 配音
      music      -> Suno 配乐
    """

    task_type: Literal["keyframe", "video_i2v", "video_t2v", "kling", "tts", "music"]
    prompt: str = ""
    priority: int = Field(default=0, ge=0, le=100)
    max_retry: int = 3
    project_id: Optional[int] = None
    shot_id: Optional[int] = None
    extra: dict = {}


class RenderTaskOut(ORMBase):
    id: int
    project_id: Optional[int]
    shot_id: Optional[int]
    task_type: str
    prompt: str
    priority: int
    status: str
    retry_count: int
    max_retry: int
    celery_task_id: str
    extra: dict
    error: str
    error_class: str
    checkpoint: str
    progress: int
    worker_id: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class RenderTaskUpdate(ORMBase):
    """更新任务（目前仅支持改优先级，后续可扩展）。"""

    priority: Optional[int] = Field(default=None, ge=0, le=100)


class RenderTaskStatusOut(ORMBase):
    """轻量状态查询响应。"""

    id: int
    task_type: str
    status: str
    retry_count: int
    progress: int
    error: str
    celery_task_id: str


# ===== 质检 =====
class QaReportBase(ORMBase):
    shot_id: Optional[int] = None
    defects: list = []
    severity: str = "info"
    fix_status: str = "open"
    fix_note: str = ""
    report_md: str = ""


class QaReportCreate(QaReportBase):
    pass


class QaReportOut(QaReportBase):
    id: int
    created_at: datetime
    updated_at: datetime


# ===== 日报 =====
class DailyBriefBase(ORMBase):
    project_id: Optional[int] = None
    brief_date: date
    author: str = ""
    content: str = ""


class DailyBriefCreate(DailyBriefBase):
    pass


class DailyBriefOut(DailyBriefBase):
    id: int
    created_at: datetime
    updated_at: datetime
