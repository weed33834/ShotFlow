"""工具服务：调用 Provider 生成资产 + 组装成片。

这是 ShotFlow 暴露给外部智能体的「能力中台」核心实现。
所有 generate_* 在 SIMULATE_MODE 下返回占位资产（url=simulate://...），保证无 Key 跑通全链路。
"""

import asyncio
import os
import subprocess

from app.core.config import settings
from app.models import Asset, GenerationTask, Spec
from app.services.providers import get_provider
from app.schemas.spec import AssembleReq, ToolGenerateReq, ToolResult


def _provider_kwargs(provider: str) -> dict:
    """按 provider 名映射配置中的 Key。"""
    s = settings
    mapping = {
        "hunyuan_image": {"secret_id": s.TENCENT_SECRET_ID, "secret_key": s.TENCENT_SECRET_KEY},
        "hunyuan_video": {"secret_id": s.TENCENT_SECRET_ID, "secret_key": s.TENCENT_SECRET_KEY},
        "tencent_tts": {"secret_id": s.TENCENT_SECRET_ID, "secret_key": s.TENCENT_SECRET_KEY},
        "wanx": {"api_key": s.DASHSCOPE_API_KEY},
        "kling": {"api_key": s.KLING_API_KEY, "base_url": s.KLING_BASE_URL},
        "jimeng": {"api_key": s.JIMENG_API_KEY, "base_url": s.JIMENG_BASE_URL},
        "runway": {"api_key": s.RUNWAY_API_KEY},
        "heygen": {"api_key": s.HEYGEN_API_KEY},
        "suno": {"api_key": s.SUNO_API_KEY, "base_url": s.SUNO_BASE_URL},
        "liblib": {"api_key": s.LIBLIB_API_KEY},
        "novelai": {"api_key": s.NOVELAI_API_KEY},
    }
    return mapping.get(provider, {})


async def run_tool(req: ToolGenerateReq, db, tool: str = "generate", spec_id: int | None = None) -> ToolResult:
    """执行一次生成工具，存 GenerationTask + Asset，返回结果。"""
    provider = get_provider(req.provider, simulate=settings.SIMULATE_MODE, **_provider_kwargs(req.provider))
    # 记录任务
    task = GenerationTask(tool=tool, provider=req.provider, params=req.params, status="running", spec_id=spec_id)
    db.add(task)
    db.commit()
    db.refresh(task)

    result = await provider.generate(req.kind, req.params)

    # 存资产
    asset = Asset(
        asset_type=req.kind,
        path=result.url or f"simulate://{req.provider}/{req.kind}",
        filename=result.url.split("/")[-1] or f"{req.provider}_{req.kind}",
        project_id=None,
        tags=[req.provider, req.kind],
        meta=result.meta,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    task.status = "completed" if result.url else "completed"
    task.result_asset_id = asset.id
    db.commit()

    return ToolResult(asset_id=asset.id, url=result.url, provider=result.provider, meta=result.meta)


async def anchor(req: ToolGenerateReq, db, spec_id: int | None = None) -> ToolResult:
    """一致性锚定（角色/风格设定图）。"""
    return await run_tool(req, db, tool="consistency_anchor", spec_id=spec_id)


async def assemble(req: AssembleReq, db) -> ToolResult:
    """组装成片：ffmpeg 拼接 + 混音 + 硬压字幕（SIMULATE 返回占位）。"""
    task = GenerationTask(tool="assemble", provider="ffmpeg", params=req.model_dump(), status="running", spec_id=req.spec_id)
    db.add(task)
    db.commit()
    db.refresh(task)

    if settings.SIMULATE_MODE:
        asset = Asset(
            asset_type="video",
            path="simulate://ffmpeg/assemble",
            filename="assembled.mp4",
            project_id=req.spec_id,
            tags=["assemble", "simulate"],
            meta={"simulate": True, "asset_ids": req.asset_ids, "subtitles": req.subtitles},
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        task.status = "completed"
        task.result_asset_id = asset.id
        db.commit()
        return ToolResult(asset_id=asset.id, url=asset.path, provider="ffmpeg", meta=asset.meta)

    # 真实组装：用 ffmpeg 拼接 asset_ids 对应视频 + 混音 + 字幕
    # TODO(Phase E): 实现 ffmpeg 拼接/混音/字幕硬压，输出到存储并回写 url
    raise NotImplementedError("真实 assemble 在 Phase E 接入 ffmpeg 实现")


def save_spec(req, db) -> Spec:
    spec = Spec(
        project_id=req.project_id,
        output_type=req.output_type,
        intent=req.intent,
        data=req.data,
    )
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec
