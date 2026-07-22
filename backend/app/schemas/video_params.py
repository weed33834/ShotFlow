"""视频参数模型 — 移植自 MoneyPrinterTurbo app/models/schema.py。

Pydantic v2 兼容改造：
- class Config → model_config = ConfigDict(...)
- pydantic.dataclasses → BaseModel
- config.ui.get(...) → 硬编码默认值（原 config 来源同样是静态默认值）
- VideoTransitionMode.none 从 None 改为 "none"（str Enum 不允许 None 值）
"""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class VideoConcatMode(str, Enum):
    """视频拼接模式。"""
    random = "random"
    sequential = "sequential"


class VideoTransitionMode(str, Enum):
    """视频转场效果。

    none 改用字符串 "none" 而非 None：str Enum 不允许 None 值，
    且 Pydantic v2 序列化 None 成员时会出错。
    """
    none = "none"
    shuffle = "shuffle"
    fade_in = "fade_in"
    fade_out = "fade_out"
    slide_in = "slide_in"
    slide_out = "slide_out"
    zoom_in = "zoom_in"
    zoom_out = "zoom_out"


class VideoAspect(str, Enum):
    """视频宽高比。

    landscape = 16:9, portrait = 9:16, square = 1:1。
    to_resolution() 返回对应像素分辨率，供 ffmpeg scale/pad 滤镜使用。
    """
    landscape = "16:9"
    portrait = "9:16"
    square = "1:1"

    def to_resolution(self) -> tuple[int, int]:
        """返回 (width, height) 像素值。"""
        if self == VideoAspect.landscape:
            return 1920, 1080
        elif self == VideoAspect.portrait:
            return 1080, 1920
        elif self == VideoAspect.square:
            return 1080, 1080
        return 1920, 1080

    def __str__(self) -> str:
        return self.value


class MaterialInfo(BaseModel):
    """素材信息（图片或视频）。"""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    provider: str = "pexels"
    url: str = ""
    duration: int = 0


class VideoParams(BaseModel):
    """视频生成参数。

    覆盖从文案到成片的全部可调参数：文案、画面、语音、字幕、BGM、
    拼接策略和输出格式。字段名与 MoneyPrinterTurbo 保持一致以降低迁移成本。
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # 文案
    video_subject: str = ""
    video_script: str = ""  # 脚本（可选，优先于 video_subject 自动生成）
    video_keywords: str = ""
    video_aspect: VideoAspect = VideoAspect.landscape

    # 拼接与转场
    video_concat_mode: VideoConcatMode = VideoConcatMode.random
    video_transition_mode: VideoTransitionMode = VideoTransitionMode.none

    # 素材
    video_materials: list[MaterialInfo] = []
    video_source: str = "pexels"

    # 配音
    voice_name: str = ""
    voice_volume: float = 1.0
    voice_rate: float = 1.0
    bgm_type: str = "random"
    bgm_volume: float = 0.2

    # 字幕
    subtitle_enabled: bool = False
    subtitle_position: str = "bottom"
    custom_position: float = 70.0
    font_name: str = "STHeiti Medium.ttc"
    font_size: int = 60
    text_fore_color: str = "#FFFFFF"
    text_back_color: Union[bool, str] = False
    stroke_color: str = "#000000"
    stroke_width: float = 1.5

    # 输出
    video_clip_duration: int = 5
    max_clip_duration: int = 5
    video_count: int = 1
    video_language: str = ""  # 空字符串表示自动检测
    video_duration: int = 60
    n_threads: int = 2
    max_duration: Optional[float] = None
    no_warmup: bool = False
