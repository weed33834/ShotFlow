"""LLM Provider 注册表 — 移植自 MoneyPrinterTurbo app/models/llm_provider.py。

改造内容：
- dataclass → Pydantic v2 BaseModel
- resolve_model_name / resolve_base_url / normalize_provider_override 保留为模块函数
- 新增 get_active_provider_spec() 从 .env 读取当前 LLM provider
- API key 通过 os.getenv 读取（AI-RULE: keys via os.getenv）
"""

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict


class LLMProviderSpec(BaseModel):
    """单个 LLM provider 的规格定义。

    env_prefix 决定环境变量前缀：{env_prefix}_MODEL / {env_prefix}_BASE_URL /
    {env_prefix}_API_KEY，允许同一 provider 的不同实例用不同前缀覆盖。
    """
    model_config = ConfigDict(frozen=True)

    name: str
    env_prefix: str
    default_model: str
    models: list[str] = []
    base_url: str = ""
    max_tokens: int = 4096
    stream_default: bool = True
    default_temperature: float = 0.7


# --------------------------------------------------------------------------- #
# 注册表：provider 名称 → 规格
# --------------------------------------------------------------------------- #

_REGISTRY: dict[str, LLMProviderSpec] = {
    "openai": LLMProviderSpec(
        name="openai",
        env_prefix="LLM_OPENAI",
        default_model="gpt-4o",
        models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4-vision"],
        base_url="https://api.openai.com/v1",
        max_tokens=4096,
        stream_default=True,
        default_temperature=0.7,
    ),
    "claude": LLMProviderSpec(
        name="claude",
        env_prefix="LLM_CLAUDE",
        default_model="claude-3-7-sonnet-20250219",
        models=[
            "claude-3-7-sonnet-20250219",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
        ],
        base_url="https://api.anthropic.com/v1",
        max_tokens=8192,
        stream_default=True,
        default_temperature=0.7,
    ),
    "gemini": LLMProviderSpec(
        name="gemini",
        env_prefix="LLM_GEMINI",
        default_model="gemini-2.0-flash",
        models=[
            "gemini-2.0-flash", "gemini-2.0-flash-lite",
            "gemini-1.5-flash", "gemini-1.5-pro",
            "gemini-2.5-flash", "gemini-2.5-pro",
        ],
        base_url="https://generativelanguage.googleapis.com/v1beta",
        max_tokens=8192,
        stream_default=True,
        default_temperature=0.7,
    ),
    "deepseek": LLMProviderSpec(
        name="deepseek",
        env_prefix="LLM_DEEPSEEK",
        default_model="deepseek-chat",
        models=["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
        base_url="https://api.deepseek.com/v1",
        max_tokens=8192,
        stream_default=True,
        default_temperature=0.7,
    ),
    "moonshot": LLMProviderSpec(
        name="moonshot",
        env_prefix="LLM_MOONSHOT",
        default_model="moonshot-v1-8k",
        models=["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        base_url="https://api.moonshot.cn/v1",
        max_tokens=4096,
        stream_default=True,
        default_temperature=0.7,
    ),
    "ollama": LLMProviderSpec(
        name="ollama",
        env_prefix="LLM_OLLAMA",
        default_model="qwen2.5:7b",
        models=["llama3.1", "qwen2.5:7b", "qwen2.5:14b"],
        base_url="http://localhost:11434/v1",
        max_tokens=4096,
        stream_default=True,
        default_temperature=0.7,
    ),
}


def list_providers() -> list[str]:
    """返回所有已注册的 provider 名称。"""
    return sorted(_REGISTRY.keys())


def get_provider_spec(provider: str) -> Optional[LLMProviderSpec]:
    """按名称获取 provider 规格，不存在返回 None。"""
    return _REGISTRY.get(provider.lower())


def resolve_model_name(provider: str, override: Optional[str] = None) -> str:
    """解析 provider 对应的模型名称。

    优先级：显式 override > 环境变量 {env_prefix}_MODEL > 注册表默认值。
    """
    spec = _REGISTRY.get(provider.lower())
    if not spec:
        raise ValueError(f"未注册的 LLM provider: {provider}")
    if override:
        return override
    env_model = os.getenv(f"{spec.env_prefix}_MODEL")
    if env_model:
        return env_model
    return spec.default_model


def resolve_base_url(provider: str, override: Optional[str] = None) -> str:
    """解析 provider 对应的 API base URL。

    优先级：显式 override > 环境变量 {env_prefix}_BASE_URL > 注册表默认值。
    """
    spec = _REGISTRY.get(provider.lower())
    if not spec:
        raise ValueError(f"未注册的 LLM provider: {provider}")
    if override:
        return override
    env_url = os.getenv(f"{spec.env_prefix}_BASE_URL")
    if env_url:
        return env_url
    return spec.base_url


def resolve_api_key(provider: str) -> str:
    """从环境变量读取 provider 对应的 API key。

    统一用 os.getenv 而非 settings，保持 key 不被序列化到配置快照中。
    """
    spec = _REGISTRY.get(provider.lower())
    if not spec:
        raise ValueError(f"未注册的 LLM provider: {provider}")
    return os.getenv(f"{spec.env_prefix}_API_KEY", "")


def normalize_provider_override(raw: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """把 "provider[:model]" 格式解析为 (provider, model) 元组。

    支持格式：
    - "openai"          → ("openai", None)
    - "openai:gpt-4o"   → ("openai", "gpt-4o")
    - None / ""         → (None, None)

    冒号分隔的模型名允许包含冒号（如 ollama:qwen2.5:7b），取第一个冒号为分隔符。
    """
    if not raw:
        return None, None
    raw = raw.strip()
    if ":" in raw:
        # 只按第一个冒号分割：模型名内部可能也含冒号（如 qwen2.5:7b）
        provider, model = raw.split(":", 1)
        return provider.strip().lower() or None, model.strip() or None
    return raw.lower(), None


def get_active_provider_spec() -> Optional[LLMProviderSpec]:
    """从 .env 读取当前活跃的 LLM provider 规格。

    读取顺序：LLM_PROVIDER 环境变量 > settings.LLM_PROVIDER > None。
    返回 None 表示未配置 provider，调用方应回退到 LLM_API_KEY + LLM_BASE_URL 直连。
    """
    try:
        from app.core.config import settings
        provider = os.getenv("LLM_PROVIDER") or getattr(settings, "LLM_PROVIDER", "") or ""
    except ImportError:
        provider = os.getenv("LLM_PROVIDER", "")
    if not provider:
        return None
    return get_provider_spec(provider)
