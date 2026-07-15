"""中央创意规格 / 生成任务 / 流程文件 模型。

第一版核心数据模型（PostgreSQL async，兼容 SQLite 开发验证）。
替代旧 pipeline.py 中写死的单视频管线（Workflow/RenderTask）。

- Spec: 系统灵魂，存「一句话→脑补」后的完整创意规格（角色/场景/镜头/风格锚点）。
- GenerationTask: 对应一次工具调用（consistency_anchor / generate_image / ...）。
- FlowDoc: 流程文件(SOP)模板，驱动外部智能体自行编排执行。
"""

from typing import Optional

from app.db.base import Base, IDMixin, JSONType, TimestampMixin
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# 产出类型（一等公民，旧模型只支持单视频）
OUTPUT_TYPES = {"video", "image_set", "micro_movie", "comic", "vn"}
# 生成任务状态
TASK_STATUS = {"pending", "running", "completed", "failed", "cancelled"}


class Spec(Base, IDMixin, TimestampMixin):
    """中央创意规格。"""

    __tablename__ = "specs"

    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # video / image_set / micro_movie / comic / vn
    output_type: Mapped[str] = mapped_column(String(32), index=True, default="video")
    # 用户原话（意图识别输入）
    intent: Mapped[str] = mapped_column(Text, default="")
    # 完整 Spec JSON（角色/场景/镜头/风格锚点/组装），结构见制作方案 §2
    data: Mapped[dict] = mapped_column(JSONType, default=dict)
    # 版权提示开关（主人裁定：用户自担，仅提示不拦截）
    copyright_notice: Mapped[bool] = mapped_column(default=True)


class GenerationTask(Base, IDMixin, TimestampMixin):
    """一次工具调用记录（对应 ShotFlow MCP 工具的一次执行）。"""

    __tablename__ = "generation_tasks"

    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    spec_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("specs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # consistency_anchor / generate_image / generate_video / generate_audio / lip_sync / assemble
    tool: Mapped[str] = mapped_column(String(32), default="", index=True)
    provider: Mapped[str] = mapped_column(String(32), default="")
    # 调用参数（prompt / ref_images / duration / voice ...）
    params: Mapped[dict] = mapped_column(JSONType, default=dict)
    # pending / running / completed / failed / cancelled
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    result_asset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    error: Mapped[str] = mapped_column(Text, default="")
    progress: Mapped[int] = mapped_column(default=0)


class FlowDoc(Base, IDMixin, TimestampMixin):
    """流程文件(SOP)模板，驱动外部智能体自行执行。"""

    __tablename__ = "flow_docs"

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    output_type: Mapped[str] = mapped_column(String(32), index=True, default="video")
    content_md: Mapped[str] = mapped_column(Text, default="")
