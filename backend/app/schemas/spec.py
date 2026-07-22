"""第一版 Schemas：工具调用 / 生成请求 / Spec 读写。"""

from typing import Any, Optional

from app.schemas.common import ORMBase
from pydantic import Field


class ToolGenerateReq(ORMBase):
    """工具调用请求（智能体直接驱动）。"""

    provider: str
    # image / video / audio / lipsync / anchor
    kind: str
    params: dict = Field(default_factory=dict)


class ToolResult(ORMBase):
    asset_id: Optional[int] = None
    url: str = ""
    provider: str = ""
    meta: dict = Field(default_factory=dict)


class AssembleReq(ORMBase):
    """组装成片请求。"""

    spec_id: Optional[int] = None
    asset_ids: list[int] = Field(default_factory=list)
    subtitles: list[str] = Field(default_factory=list)
    # 每条字幕时长（秒），来自 edge-tts WordBoundary 精确时间轴；
    # 缺失时 ffmpeg_service 按视频总时长均分。
    subtitle_durations: list[float] = Field(default_factory=list)


class GenerateReq(ORMBase):
    """一句话生成请求（人用 UI 入口 → 默认编排器）。"""

    nl_prompt: str
    output_type: str = "video"  # video/image_set/micro_movie/comic/vn
    project_id: Optional[int] = None


class SpecSaveReq(ORMBase):
    project_id: Optional[int] = None
    output_type: str = "video"
    intent: str = ""
    data: dict = Field(default_factory=dict)


class SpecOut(ORMBase):
    id: int
    output_type: str
    intent: str
    data: dict
