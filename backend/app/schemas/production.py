"""生产内容 schemas：镜头、关键帧、视频片段、对白。"""

from datetime import datetime
from typing import Optional

from app.schemas.common import ORMBase


class ShotBase(ORMBase):
    shot_code: str
    scene: str = ""
    duration: float = 5.0
    shot_type: str = "medium"
    complexity: str = "standard"
    gen_method: str = "wan_i2v"
    camera: str = ""
    description: str = ""
    order: int = 0


class ShotCreate(ShotBase):
    project_id: int


class ShotUpdate(ORMBase):
    shot_code: Optional[str] = None
    scene: Optional[str] = None
    duration: Optional[float] = None
    shot_type: Optional[str] = None
    complexity: Optional[str] = None
    gen_method: Optional[str] = None
    camera: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None


class ShotOut(ShotBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime


class KeyframeBase(ORMBase):
    label: str
    prompt: str = ""
    negative_prompt: str = ""
    seed: int = 0
    has_ava: bool = True


class KeyframeCreate(KeyframeBase):
    shot_id: int


class KeyframeOut(KeyframeBase):
    id: int
    shot_id: int
    status: str
    output_path: str
    review_status: str
    review_note: str
    created_at: datetime
    updated_at: datetime


class VideoClipBase(ORMBase):
    provider: str = "wan_i2v"
    is_complex: bool = False
    params: dict = {}


class VideoClipCreate(VideoClipBase):
    shot_id: int


class VideoClipOut(VideoClipBase):
    id: int
    shot_id: int
    status: str
    output_path: str
    duration: float
    error: str
    created_at: datetime
    updated_at: datetime


class DialogueBase(ORMBase):
    role: str = "ava"
    text: str = ""
    emotion: str = ""
    start_time: float = 0.0


class DialogueCreate(DialogueBase):
    shot_id: Optional[int] = None


class DialogueOut(DialogueBase):
    id: int
    shot_id: Optional[int]
    status: str
    audio_path: str
    created_at: datetime
    updated_at: datetime
