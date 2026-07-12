"""ORM 模型汇总 — 统一导出，便于 Alembic autogenerate 与关系解析。"""

from app.models.case_study import CaseStudy
from app.models.pipeline import (
    TASK_STATUSES,
    TASK_TYPES,
    DailyBrief,
    QaReport,
    RenderTask,
    Workflow,
)
from app.models.production import Dialogue, Keyframe, Shot, VideoClip
from app.models.project import Asset, Character, Project
from app.models.spec import FlowDoc, GenerationTask, Spec
from app.models.user import VALID_ROLES, User

__all__ = [
    # 用户
    "User",
    "VALID_ROLES",
    # 项目
    "Project",
    "Character",
    "Asset",
    # 生产
    "Shot",
    "Keyframe",
    "VideoClip",
    "Dialogue",
    # 流水线
    "Workflow",
    "RenderTask",
    "TASK_TYPES",
    "TASK_STATUSES",
    "QaReport",
    "DailyBrief",
    # 第一版：中央规格 / 生成任务 / 流程文件
    "Spec",
    "GenerationTask",
    "FlowDoc",
    # 社区化
    "CaseStudy",
]
