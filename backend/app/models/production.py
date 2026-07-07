"""生产内容模型：镜头、关键帧、视频片段、对白。"""

from typing import List, Optional

from app.db.base import Base, IDMixin, JSONType, TimestampMixin
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Shot(Base, IDMixin, TimestampMixin):
    """分镜表中的一个镜头（如 S01_01）。"""

    __tablename__ = "shots"
    # 同项目内 shot_code 唯一，跨项目可重复
    __table_args__ = (UniqueConstraint("project_id", "shot_code", name="uq_shot_project_code"),)

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    # 业务镜头编号，如 S01_01
    shot_code: Mapped[str] = mapped_column(String(32), index=True)
    scene: Mapped[str] = mapped_column(String(128), default="")
    # 时长（秒）
    duration: Mapped[float] = mapped_column(Float, default=5.0)
    # 景别：extreme_closeup / closeup / medium / wide / extreme_wide
    shot_type: Mapped[str] = mapped_column(String(32), default="medium")
    # 复杂度：standard / complex
    complexity: Mapped[str] = mapped_column(String(16), default="standard")
    # 生成方式：wan_i2v / wan_t2v / kling
    gen_method: Mapped[str] = mapped_column(String(16), default="wan_i2v")
    # 运镜描述
    camera: Mapped[str] = mapped_column(String(64), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    # 排序序号
    order: Mapped[int] = mapped_column(Integer, default=0)

    keyframes: Mapped[List["Keyframe"]] = relationship(
        back_populates="shot", cascade="all, delete-orphan"
    )
    video_clips: Mapped[List["VideoClip"]] = relationship(
        back_populates="shot", cascade="all, delete-orphan"
    )
    dialogues: Mapped[List["Dialogue"]] = relationship(
        back_populates="shot", cascade="all, delete-orphan"
    )
    render_tasks: Mapped[List["RenderTask"]] = relationship(
        back_populates="shot", cascade="all, delete-orphan"
    )

    project: Mapped["Project"] = relationship(back_populates="shots")


class Keyframe(Base, IDMixin, TimestampMixin):
    """关键帧（Flux 生成的静态图，含首尾帧拆分）。"""

    __tablename__ = "keyframes"

    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id", ondelete="CASCADE"), index=True)
    # 关键帧标签，如 S01_01 / S01_04_start / S01_04_end
    label: Mapped[str] = mapped_column(String(32), index=True)
    prompt: Mapped[str] = mapped_column(Text, default="")
    negative_prompt: Mapped[str] = mapped_column(Text, default="")
    seed: Mapped[int] = mapped_column(Integer, default=0)
    has_ava: Mapped[bool] = mapped_column(Boolean, default=True)
    # pending / submitted / completed / failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    output_path: Mapped[str] = mapped_column(String(512), default="")
    # pending / approved / rejected / needs_redraw
    review_status: Mapped[str] = mapped_column(String(16), default="pending")
    review_note: Mapped[str] = mapped_column(Text, default="")

    shot: Mapped["Shot"] = relationship(back_populates="keyframes")


class VideoClip(Base, IDMixin, TimestampMixin):
    """视频片段（Wan2.2 或可灵生成）。"""

    __tablename__ = "video_clips"

    shot_id: Mapped[int] = mapped_column(ForeignKey("shots.id", ondelete="CASCADE"), index=True)
    # wan_i2v / wan_t2v / kling
    provider: Mapped[str] = mapped_column(String(16), default="wan_i2v", index=True)
    is_complex: Mapped[bool] = mapped_column(Boolean, default=False)
    # 生成参数（CFG / Denoise / 首尾帧路径等）
    params: Mapped[dict] = mapped_column(JSONType, default=dict)
    # pending / running / completed / failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    output_path: Mapped[str] = mapped_column(String(512), default="")
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str] = mapped_column(Text, default="")

    shot: Mapped["Shot"] = relationship(back_populates="video_clips")


class Dialogue(Base, IDMixin, TimestampMixin):
    """对白条目（含配音状态）。"""

    __tablename__ = "dialogues"

    shot_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("shots.id", ondelete="CASCADE"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(32), default="ava")  # ava / core / narrator
    text: Mapped[str] = mapped_column(Text, default="")
    emotion: Mapped[str] = mapped_column(String(32), default="")
    # 时间码（秒）
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    # pending / completed / failed
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    audio_path: Mapped[str] = mapped_column(String(512), default="")

    shot: Mapped[Optional["Shot"]] = relationship(back_populates="dialogues")
