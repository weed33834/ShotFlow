"""Provider 评分器 — 在 ComfyUI(本地 Wan2.2) 与 云端 API(可灵) 之间智能选择。

评分维度（权重可调）：
  - quality  质量（0-10）
  - speed     速度（0-10，越大越快）
  - cost      成本（0-10，越大越便宜）
  - capability 复杂镜头能力（0-10）

总分 = quality*wq + speed*ws + cost*wc + capability*wcaps
默认权重偏向"质量优先 + 成本敏感"。

使用场景：
  - 标准镜头（gen_method=wan_i2v）-> 直接用 Wan2.2 本地
  - 复杂镜头（complexity=complex）-> 评分后选最优 provider
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ProviderProfile:
    """单个 provider 的能力画像。"""

    name: str
    quality: float  # 0-10
    speed: float  # 0-10
    cost: float  # 0-10（越大越便宜）
    capability: float  # 0-10（处理复杂镜头的能力）
    supports_i2v: bool = True
    supports_t2v: bool = False
    requires_gpu: bool = True


# 内置 provider 画像（基于项目实践经验）
_PROVIDERS: dict[str, ProviderProfile] = {
    # 本地 Wan2.2 I2V 14B 双专家：质量高、成本零、需 GPU
    "wan_i2v": ProviderProfile(
        name="wan_i2v",
        quality=8.5,
        speed=6.0,  # 81 帧 / 约 4-6 分钟
        cost=10.0,  # 仅电费，无 API 费用
        capability=7.0,
        supports_i2v=True,
        supports_t2v=True,
        requires_gpu=True,
    ),
    # 云端可灵 2.5 Turbo：首尾帧复杂镜头能力强、有 API 费用
    "kling": ProviderProfile(
        name="kling",
        quality=8.0,
        speed=7.5,  # 云端推理较快
        cost=5.0,  # 按次计费
        capability=9.5,  # 复杂运镜/首尾帧最强
        supports_i2v=True,
        supports_t2v=False,
        requires_gpu=False,
    ),
    # 本地 HunyuanVideo：高质量、慢、需 GPU（P6-A 新增）
    "hunyuan_video": ProviderProfile(
        name="hunyuan_video",
        quality=9.0,
        speed=5.0,  # 高质量本地推理，较慢
        cost=8.0,  # 仅电费
        capability=9.0,
        supports_i2v=True,
        supports_t2v=True,
        requires_gpu=True,
    ),
    # 本地 LTX-Video：轻量快速、需 GPU（P6-A 新增）
    "ltx_video": ProviderProfile(
        name="ltx_video",
        quality=7.0,
        speed=8.5,  # 轻量模型，推理快
        cost=9.0,  # 仅电费，显存占用低
        capability=6.0,
        supports_i2v=True,
        supports_t2v=True,
        requires_gpu=True,
    ),
    # 云端 CogVideoX：无需本地 GPU（P6-A 新增）
    "cogvideox": ProviderProfile(
        name="cogvideox",
        quality=8.0,
        speed=6.5,
        cost=7.0,  # 云端按次计费
        capability=8.0,
        supports_i2v=True,
        supports_t2v=True,
        requires_gpu=False,  # 云端，无 GPU 环境也可用
    ),
}


@dataclass
class ScoreWeights:
    """评分权重。"""

    quality: float = 0.4
    speed: float = 0.2
    cost: float = 0.25
    capability: float = 0.15


def score_provider(provider: ProviderProfile, weights: ScoreWeights) -> float:
    """计算单个 provider 的综合得分。"""
    return (
        provider.quality * weights.quality
        + provider.speed * weights.speed
        + provider.cost * weights.cost
        + provider.capability * weights.capability
    )


def rank_providers(
    complexity: str = "standard",
    weights: Optional[ScoreWeights] = None,
    has_gpu: bool = True,
) -> list[tuple[str, float]]:
    """返回按综合分数降序排列的 (provider_name, score) 候选队列，已按 has_gpu 过滤。

    供 Provider 失败回退使用：首选 provider 执行失败时，按此队列依次尝试次优。
    """
    weights = weights or ScoreWeights()
    candidates = [p for p in _PROVIDERS.values() if has_gpu or not p.requires_gpu]
    scored = [(p.name, round(score_provider(p, weights), 2)) for p in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def recommend_provider(
    complexity: str = "standard",
    gen_method: str = "wan_i2v",
    weights: Optional[ScoreWeights] = None,
    has_gpu: bool = True,
) -> dict:
    """为镜头推荐最优 provider。

    决策逻辑：
      1. 标准镜头 + 有 GPU -> 直接用 Wan2.2 本地（成本零）
      2. 复杂镜头 -> 评分对比，可灵通常胜出
      3. 无 GPU -> 只能选云端 provider
      4. 强制 gen_method 时优先尊重

    Returns:
        {
            "recommended": "wan_i2v" | "kling",
            "reason": str,
            "scores": {provider: score},
            "profiles": {provider: {...}},
        }
    """
    weights = weights or ScoreWeights()
    candidates = list(_PROVIDERS.values())

    # 无 GPU 过滤掉本地 provider
    if not has_gpu:
        candidates = [p for p in candidates if not p.requires_gpu]

    # 强制 gen_method 优先
    if gen_method in _PROVIDERS and (has_gpu or not _PROVIDERS[gen_method].requires_gpu):
        chosen = _PROVIDERS[gen_method]
        reason = f"按指定生成方式 {gen_method} 选择"
    elif complexity == "complex":
        # 复杂镜头：评分对比
        scored = {p.name: score_provider(p, weights) for p in candidates}
        chosen_name = max(scored, key=scored.get)  # type: ignore
        chosen = _PROVIDERS[chosen_name]
        reason = f"复杂镜头评分择优：{chosen_name} 得分 {scored[chosen_name]:.2f}"
    else:
        # 标准镜头：优先本地（成本最低）
        local = [p for p in candidates if p.requires_gpu]
        chosen = local[0] if local else candidates[0]
        reason = f"标准镜头优先本地：{chosen.name}"

    all_scores = {p.name: round(score_provider(p, weights), 2) for p in _PROVIDERS.values()}
    profiles = {
        name: {
            "quality": p.quality,
            "speed": p.speed,
            "cost": p.cost,
            "capability": p.capability,
            "requires_gpu": p.requires_gpu,
        }
        for name, p in _PROVIDERS.items()
    }

    return {
        "recommended": chosen.name,
        "reason": reason,
        "scores": all_scores,
        "profiles": profiles,
    }
