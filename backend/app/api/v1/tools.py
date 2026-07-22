"""工具路由：暴露给外部智能体（WorkBuddy / 元器 / 百炼 / Dify）直接驱动。

这些路由同时是 MCP server 的底层能力来源（见 services/mcp_server.py）"""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.models import Asset, Spec
from app.schemas.spec import (
    AssembleReq,
    GenerateReq,
    SpecOut,
    SpecSaveReq,
    ToolGenerateReq,
    ToolResult,
)
from app.services import asr_service, tools_service as svc
from app.services.providers import list_providers

router = APIRouter(tags=["tools"])


@router.post("/upload", response_model=ToolResult)
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: str = Form(default=""),
    db: Session = Depends(get_db),
) -> ToolResult:
    """上传本地素材文件（图片/视频/音频），存入 storage/uploads/ 并创建 Asset 记录。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")
    try:
        return await svc.save_upload(file, asset_type, db)
    except ValueError as exc:
        # 文件过大等业务校验失败 → 400，避免被兜底 500 吞掉
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/generate", response_model=ToolResult)
async def generate(req: ToolGenerateReq, db: Session = Depends(get_db)) -> ToolResult:
    """文生图/图生图/文生视频/口型同步等（kind 决定）。"""
    return await svc.run_tool(req, db, tool="generate")


@router.post("/anchor", response_model=ToolResult)
async def consistency_anchor(req: ToolGenerateReq, db: Session = Depends(get_db)) -> ToolResult:
    """一致性锚定：生成角色/风格设定图。"""
    return await svc.anchor(req, db)


@router.post("/assemble", response_model=ToolResult)
async def assemble(req: AssembleReq, db: Session = Depends(get_db)) -> ToolResult:
    """组装成片：拼接 + 混音 + 硬压字幕。"""
    return await svc.assemble(req, db)


@router.post("/transcribe")
async def transcribe_audio(
    asset_id: int,
    language: str = "zh",
    db: Session = Depends(get_db),
) -> dict:
    """对已有音频/视频资产做语音转文字，返回字幕时间轴。"""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")
    result = await asr_service.transcribe(asset.path, language)
    return {
        "text": result.text,
        "segments": result.segments,
        "srt": asr_service.asr_result_to_srt(result),
    }


@router.post("/spec", response_model=SpecOut)
def save_spec(req: SpecSaveReq, db: Session = Depends(get_db)) -> SpecOut:
    """写回中央创意规格。"""
    spec = svc.save_spec(req, db)
    return SpecOut(id=spec.id, output_type=spec.output_type, intent=spec.intent, data=spec.data)


@router.get("/spec/{spec_id}", response_model=SpecOut)
def get_spec(spec_id: int, db: Session = Depends(get_db)) -> SpecOut:
    spec = db.get(Spec, spec_id)
    if not spec:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="spec not found")
    return SpecOut(id=spec.id, output_type=spec.output_type, intent=spec.intent, data=spec.data)


@router.get("/assets", response_model=list[ToolResult])
def list_assets(db: Session = Depends(get_db)) -> list[ToolResult]:
    from app.models import Asset

    assets = db.query(Asset).order_by(Asset.id.desc()).limit(50).all()
    return [
        ToolResult(asset_id=a.id, url=a.path, provider=a.tags[0] if a.tags else "", meta=a.meta)
        for a in assets
    ]


@router.get("/providers")
def get_providers() -> dict:
    """返回已注册的 Provider 列表 + 系统配置状态，供前端渲染生成表单。"""
    providers = list_providers()
    return {
        "providers": providers,
        "simulate_mode": settings.SIMULATE_MODE,
        "llm_configured": bool(settings.LLM_API_KEY),
        "llm_provider": settings.LLM_PROVIDER or "openai",
        "llm_model": settings.LLM_MODEL or "gpt-4o-mini",
        "ffmpeg_available": bool(
            settings.FFMPEG_PATH or shutil.which("ffmpeg") is not None
        ),
    }


# ===== editing_steps JSON 编辑引擎 =====


@router.get("/editing-steps")
def list_editing_steps() -> dict:
    """返回所有可用的编辑步骤模板（ShortGPT 式 JSON 模板）。"""
    from app.services.editing_engine import get_available_steps

    return {"steps": get_available_steps()}


@router.post("/edit")
async def apply_edit(
    asset_id: int,
    steps: list[dict],
    db: Session = Depends(get_db),
) -> dict:
    """对视频资产应用编辑步骤（JSON 模板驱动），返回新资产 ID。

    steps 格式: [{"name": "make_caption", "params": {"text": "Hello"}}, ...]
    """
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")

    from app.services.editing_engine import apply_editing_steps

    if settings.SIMULATE_MODE:
        return {"asset_id": asset_id, "output_path": "simulate://editing/edit", "status": "simulated"}

    output_path = apply_editing_steps(asset.path, steps)

    # 创建新 Asset 记录
    new_asset = Asset(
        asset_type="video",
        path=output_path,
        filename=Path(output_path).name,
        project_id=None,
        tags=["edit", "editing_engine"],
        meta={"source_asset_id": asset_id, "steps": [s.get("name", "") for s in steps]},
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return {"asset_id": new_asset.id, "output_path": output_path, "status": "edited"}


# ===== 自动发布 =====


class PublishReq(BaseModel):
    """发布请求。"""

    asset_id: int
    platform: str = "douyin"  # douyin / bilibili / xiaohongshu
    title: str = ""
    description: str = ""
    tags: list[str] = []
    cover_asset_id: int | None = None


@router.get("/publish/config")
def get_publish_config() -> dict:
    """返回各发布平台的配置状态。"""
    from app.services.publish_service import get_publish_config as _get_cfg

    return _get_cfg()


@router.post("/publish")
def publish_asset(req: PublishReq, db: Session = Depends(get_db)) -> dict:
    """将视频资产发布到指定平台（抖音/B站/小红书）。"""
    asset = db.get(Asset, req.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")

    from app.services.publish_service import publish_video, PublishError

    cover_path = ""
    if req.cover_asset_id:
        cover = db.get(Asset, req.cover_asset_id)
        if cover:
            cover_path = cover.path

    try:
        result = publish_video(
            video_path=asset.path,
            platform=req.platform,
            title=req.title,
            description=req.description,
            tags=req.tags,
            cover_path=cover_path,
        )
    except PublishError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "success": result.success,
        "platform": result.platform,
        "video_url": result.video_url,
        "publish_id": result.publish_id,
        "error": result.error,
    }
