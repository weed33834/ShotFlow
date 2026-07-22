"""Provider 注册表与工厂。

第一版把所有「生成能力」抽象为统一 Provider，由各厂商 adapter 实现。
Brain（意图识别/脑补）不在此层 —— 交给外部智能体（WorkBuddy/元器/百炼）自带 LLM 完成，
ShotFlow 只负责「真正出图/出视频/出音频」这一步，通过 MCP 工具暴露给智能体调用。
"""

from app.services.providers.base import AssetResult, BaseProvider
from app.services.providers.cosyvoice_provider import CosyVoiceProvider
from app.services.providers.heygen_provider import HeygenProvider
from app.services.providers.hunyuan_image import HunyuanImageProvider
from app.services.providers.hunyuan_video_provider import HunyuanVideoProvider
from app.services.providers.jimeng_provider import JimengProvider
from app.services.providers.kling_provider import KlingProvider
from app.services.providers.liblib_provider import LiblibProvider
from app.services.providers.novelai_provider import NovelaiProvider
from app.services.providers.runway_provider import RunwayProvider
from app.services.providers.suno_provider import SunoProvider
from app.services.providers.tencent_tts_provider import TencentTtsProvider
from app.services.providers.wanx_provider import WanxProvider

# 已注册的 Provider 实现。新增厂商只需在此登记 + 实现对应 *_provider.py。
# key 必须与 backend/app/services/tools_service.py 中 _provider_kwargs 的 key 一致。
_PROVIDERS: dict[str, type[BaseProvider]] = {
    "hunyuan_image": HunyuanImageProvider,   # 腾讯混元生图 3.0 (image / anchor)
    "hunyuan_video": HunyuanVideoProvider,   # 腾讯混元视频 (video)
    "tencent_tts": TencentTtsProvider,       # 腾讯云语音合成 (audio)
    "wanx": WanxProvider,                     # 阿里通义万相 (image / video)
    "cosyvoice": CosyVoiceProvider,            # 阿里 CosyVoice 语音克隆 (audio)
    "kling": KlingProvider,                   # 可灵 (video / anchor / lipsync)
    "jimeng": JimengProvider,                 # 即梦 (image / video)
    "runway": RunwayProvider,                 # Runway (video)
    "heygen": HeygenProvider,                 # HeyGen (lipsync / video)
    "suno": SunoProvider,                     # Suno (audio)
    "liblib": LiblibProvider,                 # LiblibAI (image)
    "novelai": NovelaiProvider,               # NovelAI (image)
}


def register_provider(name: str, cls: type[BaseProvider]) -> None:
    """运行时注册 Provider（供动态加载第三方 adapter 用）。"""
    _PROVIDERS[name] = cls


def get_provider(name: str, simulate: bool = False, **kwargs) -> BaseProvider:
    """按名称取 Provider 实例。"""
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"未知 provider: {name}（已注册: {sorted(_PROVIDERS)}）")
    return cls(simulate=simulate, **kwargs)


def list_providers() -> list[str]:
    return sorted(_PROVIDERS)
