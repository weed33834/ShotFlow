"""流水线模型：工作流、渲染任务、质检报告、日报。"""

from datetime import date, datetime
from typing import Optional

from app.db.base import Base, IDMixin, JSONType, TimestampMixin
from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 任务类型常量
TASK_TYPES = {"keyframe", "video_i2v", "video_t2v", "kling", "tts", "music"}
# 任务状态常量
TASK_STATUSES = {"pending", "running", "completed", "failed", "cancelled"}


class Workflow(Base, IDMixin, TimestampMixin):
    """ComfyUI 工作流 JSON 模板。"""

    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    # 相对于仓库根的工作流文件路径（如 03_Workflows/api/Flux_Character_Consistency_api.json）
    file_path: Mapped[str] = mapped_column(String(512), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # 可调参数模板（参数名、类型、默认值、范围）
    parameters: Mapped[dict] = mapped_column(JSONType, default=dict)
    # 节点依赖说明
    node_dependencies: Mapped[list] = mapped_column(JSONType, default=list)


class RenderTask(Base, IDMixin, TimestampMixin):
    """渲染队列中的任务（替代原 render_queue.json 的内存态）。

    支持优先级、断点续跑、指数退避重试。
    """

    __tablename__ = "render_tasks"
    # 复合索引：list_tasks 按 status 过滤 + priority DESC 排序，覆盖热点查询
    __table_args__ = (Index("ix_render_tasks_status_priority", "status", "priority"),)

    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    shot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # keyframe / video_i2v / video_t2v / kling / tts / music
    task_type: Mapped[str] = mapped_column(String(16), index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    # 数字越大越先执行
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    # pending / running / completed / failed / cancelled
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retry: Mapped[int] = mapped_column(Integer, default=3)
    # Celery 返回的异步任务 ID
    celery_task_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    # 附加参数（seed / 角色 / 文件名 / 首尾帧路径等）
    extra: Mapped[dict] = mapped_column(JSONType, default=dict)
    error: Mapped[str] = mapped_column(Text, default="")
    # 断点续跑：上次进度检查点（如 ComfyUI prompt_id）
    checkpoint: Mapped[str] = mapped_column(String(128), default="")
    # 执行进度 0-100，前端展示与 SSE 推送
    progress: Mapped[int] = mapped_column(Integer, default=0)
    # 当前占用该任务的 worker 标识，配合 locked_at 做心跳判定
    worker_id: Mapped[str] = mapped_column(String(64), default="")
    # 任务被 worker 拾起的时间，用于判定僵死（超过阈值无心跳则回收）
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # 错误分类（timeout / auth / invalid_prompt / unknown），决定是否可重试
    error_class: Mapped[str] = mapped_column(String(32), default="")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    shot: Mapped[Optional["Shot"]] = relationship(back_populates="render_tasks")
    project: Mapped[Optional["Project"]] = relationship()


class QaReport(Base, IDMixin, TimestampMixin):
    """镜头质检报告。"""

    __tablename__ = "qa_reports"

    shot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # 缺陷清单：[{type, severity, description, fixed}]
    defects: Mapped[list] = mapped_column(JSONType, default=list)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # info / warning / critical
    # open / in_progress / resolved / wontfix
    fix_status: Mapped[str] = mapped_column(String(16), default="open")
    fix_note: Mapped[str] = mapped_column(Text, default="")
    report_md: Mapped[str] = mapped_column(Text, default="")


class DailyBrief(Base, IDMixin, TimestampMixin):
    """每日站会简报。"""

    __tablename__ = "daily_briefs"

    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    brief_date: Mapped[date] = mapped_column(Date, index=True)
    author: Mapped[str] = mapped_column(String(64), default="")
    content: Mapped[str] = mapped_column(Text, default="")

    project: Mapped[Optional["Project"]] = relationship(back_populates="daily_briefs")
