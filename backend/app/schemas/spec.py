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
    # 画面比例（16:9/9:16/1:1），空则用首个资产分辨率
    video_aspect: str = ""
    # 是否包含背景音乐（False 时 assemble 跳过 BGM 轨）
    bgm_enabled: bool = True
    # 转场效果（xfade 滤镜名）：fade/wipeleft/wiperight/slideup/slidedown/
    # circleopen/circleclose/distance/zoomin 等，空或 none 则不用转场
    transition: str = ""
    # 是否对静态图片启用 Ken Burns（zoompan 缓慢推拉）效果
    ken_burns: bool = True
    # 色彩分级预设：none/vintage/cross_process/teal_orange/high_contrast/warm_film
    color_grading: str = "none"


class GenerateReq(ORMBase):
    """一句话生成请求（人用 UI 入口 → 默认编排器）。"""

    nl_prompt: str
    output_type: str = "video"  # video/image_set/micro_movie/comic/vn
    project_id: Optional[int] = None
    # 视频参数（可选，前端表单传入，缺省走编排器默认值）
    video_aspect: str = ""  # 16:9 / 9:16 / 1:1，空则由编排器决定
    voice_name: str = ""  # TTS 声音（child_cn/female_cn/male_cn/female_en 等）
    subtitle_enabled: bool = True  # 是否硬压字幕
    bgm_enabled: bool = True  # 是否添加背景音乐
    # 用户上传的本地素材 asset_id 列表（图片/视频/音频），
    # S5 组装时会追加到生成资产之后参与拼接/混音
    local_asset_ids: list[int] = Field(default_factory=list)
    # 电影级提示词参数（前端选择，注入 LLM System Prompt）
    # 风格预设：cinematic/cyberpunk/anime/ink_wash/ghibli/oil_painting/realistic/
    #           watercolor/documentary/wes_anderson/scifi/fantasy/noir
    style_preset: str = ""
    # 场景模板：product/food/travel/knowledge/story/city/nature/action/interview/tutorial
    scene_template: str = ""
    # 质量等级：standard(1080p) / hd(1080p+bokeh) / 4k(4K HDR) / 8k(8K HDR Dolby Vision)
    quality_level: str = "standard"
    # 转场效果：fade/wipeleft/slideright/circleopen/distance 等 xfade 效果名
    transition: str = "fade"


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
