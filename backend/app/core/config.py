"""应用配置 — 从环境变量读取。

支持 PostgreSQL(生产) 与 SQLite(开发) 两种数据库。
通过 DATABASE_URL 环境变量切换，例如：
    生产: postgresql+psycopg://shotflow:secret@postgres:5432/shotflow
    开发: sqlite:///./shotflow.db
"""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# 项目根目录（backend/ 的上一级，即仓库根）
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# 公开默认密钥占位串，仅用于开发/测试，生产环境必须覆盖。
# 这里保留常量引用，便于在启动期做"是否仍是默认值"的断言。
_DEFAULT_SECRET_PLACEHOLDER = "change-me-in-production-please-use-a-long-random-string"


class Settings(BaseSettings):
    """全局配置，优先读取 .env。"""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用 =====
    APP_NAME: str = "ShotFlow API"
    APP_VERSION: str = "0.2.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    # 模拟模式：开启后所有生成 service 直接返回模拟结果，不调用 ComfyUI/云端 API
    # 用于无 GPU 的开发/测试环境跑通全链路
    SIMULATE_MODE: bool = True
    # 当前环境是否具备本地 GPU。影响 video_i2v/video_t2v 的 provider 自动选择：
    # 无 GPU 时仅候选云端 provider（kling / cogvideox），避免派发到本地 ComfyUI 后卡死。
    # 生产环境通常 True；纯 CI / 无卡沙箱可设 False。
    HAS_GPU: bool = True

    # ===== 数据库 =====
    # 默认指向 docker-compose 中的 postgres 服务
    DATABASE_URL: str = "postgresql+psycopg://shotflow:shotflow@postgres:5432/shotflow"

    # ===== Redis / Celery =====
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # ===== 安全 =====
    # 生产部署务必通过 .env 覆盖为一个足够长的随机串（openssl rand -hex 32）
    # 启动期会校验：非 DEBUG 模式下若仍是下面的占位串，应用直接拒绝启动。
    SECRET_KEY: str = _DEFAULT_SECRET_PLACEHOLDER
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 默认 24 小时

    # ===== 跨域 =====
    # 前端开发服务器地址，生产环境通过 .env 收紧。
    # 用 str 接收：pydantic-settings 对复杂类型（list）会先按 JSON 预解析，
    # 导致 .env 中的逗号串 "a,b,c" 直接报 SettingsError。改为 str 后自行 split，
    # 兼容逗号串与 JSON 数组串两种写法。
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        """解析 CORS_ORIGINS 为列表，兼容逗号串与 JSON 数组串。"""
        raw = self.CORS_ORIGINS
        if isinstance(raw, list):
            return raw
        raw = raw.strip()
        if raw.startswith("["):
            import json

            try:
                return [o for o in json.loads(raw) if o]
            except Exception:
                pass
        return [o.strip() for o in raw.split(",") if o.strip()]

    @model_validator(mode="after")
    def _guard_secret_key(self):
        """生产环境拒绝使用公开默认/空/过短的密钥。

        默认占位串在源码与 .env.example 中可见，若不覆盖，任何人都能
        用它本地签发 JWT 冒充任意用户。这里在非 DEBUG 模式下硬性拦截
        占位串、空串与长度不足 32 的密钥，迫使部署方显式设置。
        开发/测试环境设 DEBUG=true 即可放过。
        """
        if self.DEBUG:
            return self
        key = self.SECRET_KEY
        if not key or key == _DEFAULT_SECRET_PLACEHOLDER or len(key) < 32:
            raise ValueError(
                "SECRET_KEY 不合规（为空/仍是公开默认值/长度不足 32），生产环境必须覆盖。"
                "生成随机串: openssl rand -hex 32，写入 .env 的 SECRET_KEY。"
                "若确需在开发环境运行，可设置 DEBUG=true。"
            )
        return self

    # ===== 外部服务（第一版：全部厂商 adapter，SIMULATE 兜底）=====
    # 本地模型（二期）：ComfyUI / Ollama。第一版不启用。
    COMFYUI_URL: str = "http://127.0.0.1:8188"
    COMFYUI_DIR: str = str(Path.home() / "ComfyUI")

    # 腾讯：混元生图 / 混元视频 / 腾讯云 TTS（SecretId + SecretKey）
    TENCENT_SECRET_ID: str = ""
    TENCENT_SECRET_KEY: str = ""
    TENCENT_TTS_APP_ID: str = ""

    # 阿里：通义万相（图/视频）/ 通义千问（Brain 备选）
    DASHSCOPE_API_KEY: str = ""

    # 可灵 Kling
    KLING_API_KEY: str = ""
    KLING_BASE_URL: str = "https://api.piapi.ai"

    # 即梦（字节火山引擎 Ark）
    JIMENG_API_KEY: str = ""
    JIMENG_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    # 可覆盖模型名（如指向其他 OpenAI 兼容网关时用 step-image-edit-2 等）
    JIMENG_IMAGE_MODEL: str = ""
    JIMENG_VIDEO_MODEL: str = ""

    # Runway
    RUNWAY_API_KEY: str = ""

    # HeyGen（口型同步）
    HEYGEN_API_KEY: str = ""

    # Suno（BGM）
    SUNO_API_KEY: str = ""
    SUNO_BASE_URL: str = "https://api.sunoaiapi.com"

    # 自动发布平台（各平台需配置对应 access_token / cookie 后才能真实发布）
    DOUYIN_ACCESS_TOKEN: str = ""
    BILIBILI_SESSDATA: str = ""

    # Liblib（图，LoRA 生态）
    LIBLIB_API_KEY: str = ""

    # NovelAI（动漫专精图）
    NOVELAI_API_KEY: str = ""

    # ===== LLM（Brain 脚本/分镜生成，多 Provider 适配）=====
    # 用于 orchestrator 的真实 brain，替代硬编码关键词匹配。
    # 认证 Key 统一走 LLM_API_KEY；base_url/model 未显式配置时按 LLM_PROVIDER 回落默认值。
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    # LLM provider 名称，决定 llm_service.chat_completion 走哪条适配协议：
    #   openai / deepseek / moonshot / ollama → OpenAI 兼容协议（/chat/completions + Bearer）
    #   gemini  → Google 原生 generateContent（key 拼在 query，body 用 contents）
    #   claude  → Anthropic 原生 messages（header x-api-key + anthropic-version）
    # 留空则回退原始 OpenAI 兼容直连（向后兼容：依赖 LLM_BASE_URL + LLM_MODEL 显式配置）。
    # LLM_BASE_URL / LLM_MODEL 非空时覆盖对应 provider 的默认 base_url / model。
    LLM_PROVIDER: str = ""

    # 编排器使用的默认 Provider（可通过 .env 覆盖切换厂商）
    IMAGE_PROVIDER: str = "hunyuan_image"
    VIDEO_PROVIDER: str = "wanx"
    ANCHOR_PROVIDER: str = "hunyuan_image"

    # ===== 资产存储 =====
    # 真实模式下生成资产落地于此目录下（按 task_id 隔离）
    STORAGE_DIR: str = str(PROJECT_ROOT / "storage")

    # ===== ffmpeg =====
    # ffmpeg 二进制路径，空则从 PATH 查找
    FFMPEG_PATH: str = ""

    # ===== 开源增强工具（二期，可选依赖，缺失时优雅降级）=====
    # Real-ESRGAN 超分二进制（realesrgan-ncnn-vulkan）路径，空则从 PATH 查找；
    # 未安装时 enhance_service 会跳过超分步骤并告警，不中断主链路。
    REALESRGAN_PATH: str = ""
    # RIFE 帧插值二进制（rife-ncnn-vulkan）路径，空则从 PATH 查找；
    # 未安装时跳过补帧步骤并告警，不中断主链路。
    RIFE_PATH: str = ""

    # ===== ASR 语音识别 Provider 选择 =====
    # funasr: 优先用本地 FunASR（paraformer）模型
    # whisper: 优先用本地 faster-whisper
    # openai: 强制走 OpenAI Whisper API
    # auto: FunASR → faster-whisper → OpenAI API 逐级回落（默认，最稳）
    ASR_PROVIDER: str = "auto"

    # ===== GPT-SoVITS 语音克隆本地 API 服务 =====
    # GPT-SoVITS 以独立 API 服务形式部署（默认 http://127.0.0.1:9880），
    # 留空时 provider 走 simulate 占位，不阻断链路。
    GPTSOVITS_API_URL: str = ""

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
