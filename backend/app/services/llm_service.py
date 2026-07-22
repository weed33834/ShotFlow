"""LLM 调用服务：多 Provider 适配，供编排器 brain 真实生成分镜脚本。

替代 orchestrator._brain() 的硬编码关键词匹配：根据 settings.LLM_PROVIDER 分发到
openai / deepseek / moonshot / ollama（OpenAI 兼容协议）、gemini（原生 generateContent）、
claude（原生 messages）。LLM_PROVIDER 为空时回退原始 OpenAI 兼容直连，保持向后兼容。
统一用 settings.LLM_API_KEY 作认证 Key，LLM_BASE_URL / LLM_MODEL 非空时覆盖 provider 默认值。
"""
import asyncio
import json
import logging
import re
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)
_LLM_TIMEOUT = 90.0  # LLM 调用超时（秒），生成分镜 JSON 较慢需长超时

# Provider 默认配置表：未在 settings 显式配置 base_url/model 时回落到此处，
# 让用户只需设 LLM_PROVIDER + LLM_API_KEY 即可切换厂商，不必逐个填地址。
_PROVIDER_DEFAULTS: dict[str, dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "ollama": {
        "base_url": "http://127.0.0.1:11434/v1",
        "model": "qwen2.5:7b",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-1.5-flash",
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-sonnet-20241022",
    },
}

# 走 OpenAI 兼容协议的 provider 集合（共享 /chat/completions + Bearer 认证），
# 与 gemini/claude 原生 API 区分开，避免为每个厂商重复实现请求逻辑。
_OPENAI_COMPATIBLE_PROVIDERS = {"openai", "deepseek", "moonshot", "ollama"}

_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE)
# 匹配孤立的 <think> 开标签后到结尾（无闭合时的兜底）。
_THINK_OPEN_ONLY_RE = re.compile(r"<think\b[^>]*>.*", re.DOTALL | re.IGNORECASE)
# 匹配 ```json ... ``` / ``` ... ``` 代码围栏，剥离后取裸 JSON。
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
# 兜底抽取第一个 {...} 块（JSON 容错最后手段）。
_FIRST_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def _strip_think_blocks(text: str) -> str:
    """剥离推理模型的 <think>...</think> 块，兼容未闭合的孤立 <think>。"""
    if not text:
        return ""
    # 先剥成对块；若仍有残留的孤立 <think>，把开标签后到结尾全删。
    text = _THINK_RE.sub("", text)
    text = _THINK_OPEN_ONLY_RE.sub("", text)
    return text.strip()


def _strip_code_fences(text: str) -> str:
    """剥离 ```json ... ``` 代码围栏，取围栏内裸内容。"""
    if not text:
        return text
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    """从 OpenAI 兼容响应体提取 choices[0].message.content 文本。"""
    # 兼容少数网关返回字符串或异常结构：取首条 choice 的 message.content。
    choices = payload.get("choices") or []
    if not choices:
        # 某些网关错误时把错误放进 "error" 字段，抛出供上层定位。
        if payload.get("error"):
            raise RuntimeError(f"LLM 返回错误: {payload['error']}")
        raise RuntimeError(f"LLM 响应无 choices 字段: {str(payload)[:200]}")
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if isinstance(content, list):
        # vision/多模态网关可能返回 [{"type":"text","text":"..."}]，拼接文本段。
        content = "".join(seg.get("text", "") for seg in content if isinstance(seg, dict))
    return content


def _parse_json_lenient(text: str) -> dict[str, Any]:
    """容错解析 JSON：先剥 <think>/代码围栏，失败则正则抽首块 {...} 再解析。"""
    cleaned = _strip_think_blocks(text)
    cleaned = _strip_code_fences(cleaned)
    # 直接解析
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    # 兜底：抽首个 {...} 块再解析（LLM 可能前后带散文说明）。
    match = _FIRST_JSON_RE.search(cleaned)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
    raise ValueError(f"无法从 LLM 输出解析 JSON。原始片段: {text[:300]}")


async def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
    """调用 LLM，根据 LLM_PROVIDER 分发到对应适配器，返回纯文本（已剥离 <think>）。

    为什么自实现而非用 openai SDK：项目仅依赖 httpx，不引入 openai 包；
    且 gemini/claude 原生协议各不相同，统一在此适配避免引入多个 SDK。
    所有适配器都返回纯文本字符串，调用方（generate_script_spec）自行解析 JSON。
    """
    # SIMULATE_MODE 是全局硬开关：即使配了 Key，模拟模式下也绝不触发真实网络调用，
    # 交由编排器捕获后回退硬编码脑补，保证沙箱/无网环境不外呼 LLM。
    if settings.SIMULATE_MODE:
        raise RuntimeError("SIMULATE_MODE 开启，禁止调用 LLM")
    if not settings.LLM_API_KEY:
        # 显式错误：编排器据此回退到硬编码 brain，避免静默走错路径。
        raise RuntimeError("LLM_API_KEY 未配置，无法调用 LLM（请在 .env 设置 LLM_API_KEY）")

    provider = (settings.LLM_PROVIDER or "").strip().lower()
    # 用户显式配置优先；否则回落到 provider 注册表默认值，避免每个 provider 都要手填 base_url/model。
    defaults = _PROVIDER_DEFAULTS.get(provider, {})
    base_url = settings.LLM_BASE_URL or defaults.get("base_url", "")
    model = settings.LLM_MODEL or defaults.get("model", "")
    api_key = settings.LLM_API_KEY

    # 统一兜底校验：base_url/model 缺失时直接报错，避免构造出半截请求 URL。
    if not base_url:
        raise RuntimeError(
            f"LLM base_url 未解析到（provider={provider or '未设置'}，请在 .env 配置 LLM_BASE_URL 或 LLM_PROVIDER）"
        )
    if not model:
        raise RuntimeError(
            f"LLM model 未解析到（provider={provider or '未设置'}，请在 .env 配置 LLM_MODEL 或 LLM_PROVIDER）"
        )

    # 向后兼容：LLM_PROVIDER 为空或未知 provider 时，按 OpenAI 兼容协议直连
    # （自建网关/未登记厂商均可走此路径）。
    if provider in _OPENAI_COMPATIBLE_PROVIDERS or not provider:
        return await _chat_openai_compatible(
            api_key, base_url, model, system_prompt, user_prompt, temperature
        )
    if provider == "gemini":
        return await _chat_gemini(
            api_key, base_url, model, system_prompt, user_prompt, temperature
        )
    if provider == "claude":
        return await _chat_claude(
            api_key, base_url, model, system_prompt, user_prompt, temperature
        )
    # 未登记的 provider：同样按 OpenAI 兼容协议兜底，覆盖自建/第三方网关。
    return await _chat_openai_compatible(
        api_key, base_url, model, system_prompt, user_prompt, temperature
    )


def _sync_post(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    """同步 POST 并返回解析后的 JSON；非 200 或解析失败统一抛 RuntimeError。

    为什么用同步 httpx：sandbox 代理对 async httpx 不稳定，同步路径已验证可用。
    各 provider 适配器共享此实现，仅 headers/body/响应提取逻辑各自不同。
    """
    with httpx.Client(timeout=_LLM_TIMEOUT) as client:
        resp = client.post(url, headers=headers, json=body)
    if resp.status_code != 200:
        # 非 2xx：把状态码与响应片段抛出，便于排查（如 401 key 失效、429 限流）。
        raise RuntimeError(
            f"LLM 返回非 200：status={resp.status_code} body={resp.text[:300]}"
        )
    try:
        return resp.json()
    except ValueError as exc:
        raise RuntimeError(f"LLM 响应非 JSON: {resp.text[:300]}") from exc


async def _run_request(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    """把同步 POST 包进 asyncio.to_thread，供 async 调用方使用，不阻塞事件循环。"""
    try:
        return await asyncio.to_thread(_sync_post, url, headers, body)
    except httpx.HTTPError as exc:
        # 网络层失败：超时 / 连接拒绝 / DNS，交由编排器回退。
        raise RuntimeError(f"LLM 请求失败（网络/超时）: {exc}") from exc


async def _chat_openai_compatible(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> str:
    """OpenAI 兼容协议适配器（openai/deepseek/moonshot/ollama/自建网关）。

    POST {base_url}/chat/completions，Bearer 认证，提取 choices[0].message.content。
    """
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
    }
    payload = await _run_request(url, headers, body)
    content = _extract_chat_completion_text(payload)
    # 剥离推理模型的 <think> 块后再返回，调用方拿到纯文本/JSON。
    return _strip_think_blocks(content)


async def _chat_gemini(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> str:
    """Gemini 原生 API 适配器。

    POST {base_url}/models/{model}:generateContent?key={api_key}，body 用
    system_instruction + contents，提取 candidates[0].content.parts[].text。
    """
    url = f"{base_url.rstrip('/')}/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "system_instruction": {"parts": {"text": system_prompt}},
        "contents": [{"role": "user", "parts": {"text": user_prompt}}],
        "generationConfig": {"temperature": temperature},
    }
    payload = await _run_request(url, headers, body)
    candidates = payload.get("candidates") or []
    if not candidates:
        # Gemini 错误时把错误放进 "error" 字段，抛出供上层定位。
        if payload.get("error"):
            raise RuntimeError(f"Gemini 返回错误: {payload['error']}")
        raise RuntimeError(f"Gemini 响应无 candidates: {str(payload)[:200]}")
    parts = (candidates[0].get("content") or {}).get("parts")
    # 官方返回 parts 为列表；个别代理可能返回单 dict，两种都兼容。
    if isinstance(parts, list):
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    elif isinstance(parts, dict):
        text = parts.get("text", "")
    else:
        text = ""
    return _strip_think_blocks(text)


async def _chat_claude(
    api_key: str,
    base_url: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
) -> str:
    """Anthropic Claude 原生 API 适配器。

    POST {base_url}/messages，header 用 x-api-key + anthropic-version，
    system 作为顶层字段，提取 content[].text。
    """
    url = f"{base_url.rstrip('/')}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": 4096,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": temperature,
    }
    payload = await _run_request(url, headers, body)
    content = payload.get("content") or []
    if not content:
        if payload.get("error"):
            raise RuntimeError(f"Claude 返回错误: {payload['error']}")
        raise RuntimeError(f"Claude 响应无 content: {str(payload)[:200]}")
    # content 是 [{"type":"text","text":"..."}]，拼接所有文本段。
    text = "".join(seg.get("text", "") for seg in content if isinstance(seg, dict))
    return _strip_think_blocks(text)


_SYSTEM_PROMPT_TEMPLATE = """你是 ShotFlow AIGC 编排平台的分镜脚本专家。根据用户的一句话需求，生成结构化的分镜编排规格（spec）。

你必须只返回一个合法 JSON 对象，不要输出任何解释性文字，不要使用 Markdown 代码围栏。

JSON 结构如下：
{{
  "title": "短片标题",
  "characters": [
    {{"name": "角色名", "desc": "角色外观与性格描述", "anchor_prompt": "一致性锚定的图像提示词：角色外观+画风，中文，具体描述"}}
  ],
  "scenes": [
    {{
      "name": "场景名",
      "index": 1,
      "description": "场景描述",
      "shots": [
        {{
          "index": 1,
          "duration": 5,
          "image_prompt": "本镜画面描述（文生图用，中文，含构图/光影/角色动作/场景）",
          "video_prompt": "本镜动态描述（图生视频用，中文，含镜头运动与动态）",
          "subtitle": "本镜字幕文本",
          "voice_text": "本镜配音台词",
          "audio": {{"text": "配音台词", "voice": "child_cn", "type": "tts"}}
        }}
      ]
    }}
  ]
}}

要求：
- 生成 1-3 个场景，每个场景 3-5 个镜头。
- 角色一致性：每个角色都要有 anchor_prompt，跨镜头锁定外观。
- image_prompt 要具体、可视化：包含角色外观、场景、构图、光影。
- video_prompt 描述镜头运动（推/拉/摇/移）与角色动态。
- subtitle 与 voice_text 可以相同（旁白）也可以不同（字幕简短、台词完整）。
- audio.voice 取值：child_cn（童声）/ female_cn（女声）/ male_cn（男声）。
- 产出类型为 {output_type}，请据此调整内容：video=短片，image_set=图集，micro_movie=微电影，comic=漫画分镜，vn=视觉小说。
- 仅返回 JSON，不要任何额外文字。"""


def _normalize_spec(spec: dict[str, Any], nl_prompt: str, output_type: str) -> dict[str, Any]:
    """规整 LLM 返回的 spec：补齐编排器下游消费所需的必填字段，保证结构稳定。

    编排器 run() 会访问 characters[0].anchor_prompt、shot.image_prompt /
    video_prompt / duration / audio.text / audio.voice / subtitle，缺一即 KeyError。
    LLM 可能漏字段或返回空结构，这里统一兜底，避免运行时崩。
    """
    # 角色兜底
    chars = spec.get("characters") or []
    if not isinstance(chars, list):
        chars = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        c.setdefault("name", "主角")
        c.setdefault("desc", "")
        c.setdefault("anchor_prompt", f"{c.get('name', '主角')}，圆润卡通风格，高饱和色彩，夸张表情")
        # ref_asset_ids 是 spec.data 里的占位字段，保留空列表保持向后兼容。
        c.setdefault("ref_asset_ids", [])
    if not chars:
        chars = [
            {
                "name": "主角",
                "desc": "",
                "anchor_prompt": "主角，圆润卡通风格，高饱和色彩，夸张表情",
                "ref_asset_ids": [],
            }
        ]
    spec["characters"] = chars

    # 场景/镜头兜底
    scenes = spec.get("scenes") or []
    if not isinstance(scenes, list):
        scenes = []
    for si, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            continue
        sc.setdefault("index", si + 1)
        sc.setdefault("name", f"场景{si + 1}")
        sc.setdefault("description", "")
        shots = sc.get("shots") or []
        if not isinstance(shots, list):
            shots = []
        for shi, sh in enumerate(shots):
            if not isinstance(sh, dict):
                continue
            sh.setdefault("index", shi + 1)
            sh.setdefault("duration", 5)
            sh.setdefault("image_prompt", nl_prompt)
            # video_prompt 缺失时复用 image_prompt，保证图生视频有输入。
            sh.setdefault("video_prompt", sh["image_prompt"])
            # subtitle / voice_text 互为兜底。
            vt = sh.get("voice_text") or sh.get("subtitle") or nl_prompt
            sh.setdefault("voice_text", vt)
            sh.setdefault("subtitle", vt)
            # audio 必须是 dict 且含 text/voice/type，下游 shot["audio"]["text"] 直接取。
            audio = sh.get("audio")
            if not isinstance(audio, dict):
                audio = {}
            audio.setdefault("text", sh.get("voice_text") or sh.get("subtitle") or nl_prompt)
            audio.setdefault("voice", "child_cn")
            audio.setdefault("type", "tts")
            sh["audio"] = audio
        sc["shots"] = shots
    # 完全无场景时给一个占位单镜，保证编排器能走完链路（不至于空迭代后 assemble 拿空字幕）。
    if not scenes:
        scenes = [
            {
                "index": 1,
                "name": "场景1",
                "description": "自动生成场景",
                "shots": [
                    {
                        "index": 1,
                        "duration": 5,
                        "image_prompt": nl_prompt,
                        "video_prompt": nl_prompt,
                        "subtitle": nl_prompt,
                        "voice_text": nl_prompt,
                        "audio": {"text": nl_prompt, "voice": "child_cn", "type": "tts"},
                    }
                ],
            }
        ]
    spec["scenes"] = scenes

    spec.setdefault("title", nl_prompt[:24] if nl_prompt else "未命名")
    return spec


async def generate_script_spec(nl_prompt: str, output_type: str = "video") -> dict[str, Any]:
    """用 LLM 生成编排规格（spec）：场景、镜头、image_prompt、subtitle、配音文本。

    返回格式与当前 _brain() 返回的下游可消费字段一致（characters[].anchor_prompt、
    scenes[].shots[].{image_prompt,video_prompt,subtitle,audio,duration}），
    额外含 title/voice_text 等富字段。编排器据此合并 wrapper 字段后存 spec.data。
    """
    if not nl_prompt:
        nl_prompt = "生成一段短视频"
    system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(output_type=output_type)
    user_prompt = f"用户需求：{nl_prompt}"

    # 脚本生成需一定创造性但又要结构稳定，temperature 取 0.7 平衡。
    raw = await chat_completion(system_prompt, user_prompt, temperature=0.7)

    spec = _parse_json_lenient(raw)
    return _normalize_spec(spec, nl_prompt, output_type)
