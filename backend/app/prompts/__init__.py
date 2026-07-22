"""电影级提示词系统 — 风格预设、场景模板、镜头语言词库。

加载方式：YAML 文件 → Python dict，供 llm_service 注入到 System Prompt。
LLM 生成 image_prompt / video_prompt 时自动追加专业术语，实现电影级画面描述。
"""

import random
from pathlib import Path
from typing import Any

import yaml

_PROMPTS_DIR = Path(__file__).parent

# 缓存：首次加载后常驻内存
_cache: dict[str, dict] = {}


def _load_yaml(filename: str) -> dict:
    """加载 YAML 文件，带缓存。"""
    if filename in _cache:
        return _cache[filename]
    path = _PROMPTS_DIR / filename
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _cache[filename] = data
    return data


def get_style_presets() -> dict[str, dict]:
    """返回所有风格预设。"""
    return _load_yaml("styles/presets.yaml")


def get_scene_templates() -> dict[str, dict]:
    """返回所有场景模板。"""
    return _load_yaml("scenes/templates.yaml")


def get_cinematic_keywords() -> dict[str, list[str]]:
    """返回镜头语言词库（光影/景别/运镜/氛围/技术参数）。"""
    lighting = _load_yaml("cinematic/lighting.yaml")
    angles = _load_yaml("cinematic/camera_angles.yaml")
    movement = _load_yaml("cinematic/camera_movement.yaml")
    mood = _load_yaml("cinematic/mood.yaml")
    return {
        "lighting": lighting.get("lighting", []),
        "camera_angles": angles.get("camera_angles", []),
        "camera_movement": movement.get("camera_movement", []),
        "mood": mood.get("mood", []),
    }


def get_style_preset(name: str) -> dict[str, Any]:
    """按名称获取单个风格预设。"""
    presets = get_style_presets()
    return presets.get(name, {})


def get_scene_template(name: str) -> dict[str, Any]:
    """按名称获取单个场景模板。"""
    templates = get_scene_templates()
    return templates.get(name, {})


def build_enhanced_system_prompt(
    style_preset: str = "",
    scene_template: str = "",
    quality_level: str = "standard",
) -> str:
    """构建增强版 LLM System Prompt，注入风格预设和镜头语言要求。

    Args:
        style_preset: 风格预设名（cinematic/cyberpunk/anime/ink_wash/ghibli...）
        scene_template: 场景模板名（product/food/travel/knowledge/story/city/nature...）
        quality_level: 质量等级（standard/hd/4k/8k）
    Returns:
        增强后的 System Prompt 字符串
    """
    # 加载风格预设
    style = get_style_preset(style_preset) if style_preset else {}
    style_keywords = style.get("image_suffix", "")
    style_video = style.get("video_suffix", "")
    style_negative = style.get("negative_prompt", "")
    style_name = style.get("name", style_preset or "默认")

    # 加载场景模板
    scene = get_scene_template(scene_template) if scene_template else {}
    shot_rhythm = scene.get("shot_rhythm", "中节奏，每镜 3-5 秒")
    shot_sequence = scene.get("shot_sequence", "远景→中景→特写")
    lighting_advice = scene.get("lighting", "自然光")

    # 质量参数
    quality_map = {
        "standard": "1080p, 高清画质",
        "hd": "1080p, 高清画质, 浅景深 bokeh",
        "4k": "4K HDR, 超高细节, 浅景深 bokeh, 电影级调色, ACES 色彩空间",
        "8k": "8K HDR, 超高细节, 极浅景深, 电影级调色, Dolby Vision, ray tracing",
    }
    quality_str = quality_map.get(quality_level, quality_map["standard"])

    prompt = f"""你是 ShotFlow AIGC 编排平台的分镜脚本专家，具备专业电影摄影知识。
根据用户的一句话需求，生成结构化的分镜编排规格（spec）。

## 风格预设：{style_name}
本次生成采用「{style_name}」风格。在每个 image_prompt 末尾必须追加以下描述词：
{style_keywords}
{"负向提示词（避免出现的元素）：" + style_negative if style_negative else ""}

## 场景模板：{scene.get("name", scene_template or "通用")}
镜头节奏：{shot_rhythm}
推荐景别组合：{shot_sequence}
光影建议：{lighting_advice}

## 画面描述要求（image_prompt 必须包含以下维度，按顺序）
1. 光影描述：选择合适的光影（如 golden hour sunlight / volumetric lighting / cinematic lighting / rim light / chiaroscuro lighting 等）
2. 景别构图：选择合适的景别（如 wide establishing shot / medium shot / close-up / extreme close-up / aerial shot / macro shot 等）
3. 主体描述：角色外观、服装、表情、姿态（具体到颜色、材质、纹理）
4. 场景环境：地点、时间、天气、氛围细节
5. 氛围词：选择合适的氛围（如 epic / dramatic / ethereal / moody / cinematic / serene / mysterious 等）
6. 技术参数：{quality_str}

## 视频描述要求（video_prompt 必须包含以下维度）
1. 镜头运动：选择合适的运镜（如 slow dolly in / tracking shot / crane shot / orbit shot / handheld / aerial drone shot 等）
2. 主体动态：具体的动作描述（不是"做出动作"，而是具体的肢体运动）
3. 速度控制：慢动作(slow motion 120fps) / 实时 / 延时(time-lapse) / 一镜到底(continuous take)
4. 环境动态：风吹、水波、光影变化等环境元素的运动

## 输出格式（严格 JSON）
{{
  "title": "影片标题（中文）",
  "intent": "创作意图简述",
  "characters": [
    {{
      "name": "角色名",
      "appearance": "外观描述（发色/肤色/服装/体型）",
      "anchor_prompt": "角色设定图生成提示词（含光影+景别+外观+{quality_str}）"
    }}
  ],
  "style_anchor": {{
    "visual_style": "{style_name}",
    "color_palette": "主色调描述",
    "negative_prompt": "{style_negative}"
  }},
  "scenes": [
    {{
      "title": "场景标题",
      "shots": [
        {{
          "image_prompt": "光影 + 景别 + 主体动作 + 场景 + 氛围 + 技术参数（完整描述，50-100字）",
          "video_prompt": "运镜 + 主体动态 + 速度控制 + 环境动态（完整描述，30-80字）",
          "duration": 5,
          "audio": {{
            "text": "配音文本（口语化，适合朗读）",
            "voice": "zh-CN-YunxiNeural"
          }}
        }}
      ]
    }}
  ],
  "assembly": {{
    "transition": "fade",
    "bgm": false,
    "subtitle": true
  }}
}}

## 约束
1. 场景数 2-4 个，每场景 2-4 个镜头，总镜头数 4-12 个
2. image_prompt 必须是完整的画面描述，不能是简单短句
3. 镜头之间要有叙事逻辑（远景建立环境→中景交代关系→特写传递情绪）
4. 配音文本要口语化、有感情、适合 TTS 朗读
5. duration 根据 audio.text 长度估算（约 4 字/秒）
6. 角色跨镜头外观必须一致
7. 只返回 JSON，不要加 markdown 代码块标记"""
    return prompt


def enhance_fallback_prompt(subject: str, shot_index: int, style_preset: str = "") -> str:
    """增强版 fallback 提示词（无 LLM 时用词库生成专业画面描述）。"""
    keywords = get_cinematic_keywords()
    style = get_style_preset(style_preset) if style_preset else {}
    style_suffix = style.get("image_suffix", "cinematic lighting, shallow depth of field, 4K")

    # 随机选择专业术语，避免每次相同
    lighting = random.choice(keywords.get("lighting", ["cinematic lighting"]))
    angle = random.choice(keywords.get("camera_angles", ["medium shot"]))
    mood = random.choice(keywords.get("mood", ["cinematic"]))

    return (
        f"{lighting}, {angle}, {subject}, "
        f"{mood}氛围, {style_suffix}"
    )
