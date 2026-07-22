"""工具路由：暴露给外部智能体（WorkBuddy / 元器 / 百炼 / Dify）直接驱动。

这些路由同时是 MCP server 的底层能力来源（见 services/mcp_server.py）"""

import asyncio
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


# ===== 提示词预设管理 =====


@router.get("/prompts/styles")
def list_style_presets() -> dict:
    """返回所有可用的风格预设，供前端风格选择器渲染。"""
    from app.prompts import get_style_presets

    presets = get_style_presets()
    return {
        "styles": [
            {"key": k, **v}
            for k, v in presets.items()
        ]
    }


@router.get("/prompts/scenes")
def list_scene_templates() -> dict:
    """返回所有可用的场景模板，供前端场景选择器渲染。"""
    from app.prompts import get_scene_templates

    templates = get_scene_templates()
    return {
        "scenes": [
            {"key": k, **v}
            for k, v in templates.items()
        ]
    }


@router.get("/prompts/keywords")
def list_cinematic_keywords() -> dict:
    """返回镜头语言词库，供前端提示词增强预览/手动编辑使用。"""
    from app.prompts import get_cinematic_keywords

    return get_cinematic_keywords()


@router.get("/prompts/quality-levels")
def list_quality_levels() -> dict:
    """返回可选的质量等级列表。"""
    return {
        "levels": [
            {"key": "standard", "label": "标准 1080p", "desc": "高清画质"},
            {"key": "hd", "label": "高清 1080p+", "desc": "高清画质 + 浅景深"},
            {"key": "4k", "label": "4K HDR", "desc": "超高细节 + 电影级调色 + ACES"},
            {"key": "8k", "label": "8K HDR", "desc": "极清 + Dolby Vision + 光追"},
        ]
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


# ===== 视频增强（Real-ESRGAN 超分 + RIFE 补帧）=====


class EnhanceReq(BaseModel):
    """视频增强请求。"""

    asset_id: int
    # 超分倍数（2/3/4），仅 Real-ESRGAN 可用时生效
    scale: int = 2
    # 目标帧率（如 60），仅 RIFE 可用时生效
    fps_target: int = 60
    # 输出路径（空则落到 STORAGE_DIR/enhanced/）
    output_path: str = ""


@router.post("/enhance")
async def enhance_video_asset(
    req: EnhanceReq,
    db: Session = Depends(get_db),
) -> dict:
    """对视频资产应用超分辨率 + 帧插值增强，返回新资产 ID。

    管线：ffmpeg 抽帧 → Real-ESRGAN 超分 → RIFE 补帧 → ffmpeg 重编码。
    任一开源工具缺失时优雅跳过该步骤（仅告警），仍产出有效视频。
    """
    asset = db.get(Asset, req.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="asset not found")

    # SIMULATE 模式返回占位，避免在无 ffmpeg/工具的纯测试环境真正调起外部进程
    if settings.SIMULATE_MODE:
        return {
            "asset_id": req.asset_id,
            "output_path": "simulate://enhance/video",
            "status": "simulated",
            "scale": req.scale,
            "fps_target": req.fps_target,
        }

    # 延迟导入：避免无增强工具环境 import 期触发不必要的副作用
    from app.services.enhance_service import enhance_video, is_enhance_available

    # 资产路径校验：enhance 仅支持本地文件，simulate:// 占位资产直接拒绝
    src_path = asset.path or ""
    if src_path.startswith("simulate://") or not src_path:
        raise HTTPException(
            status_code=400,
            detail="资产路径无效（simulate:// 占位或为空），enhance 需要本地视频文件",
        )

    # 工具完全不可用时给出明确提示（而非默默返回原视频），便于调用方决策
    if not is_enhance_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "视频增强工具不可用：未检测到 realesrgan-ncnn-vulkan / rife-ncnn-vulkan，"
                "或 ffmpeg 缺失。请安装对应工具或在 .env 配置 "
                "REALESRGAN_PATH / RIFE_PATH，或开启 SIMULATE_MODE 走模拟流程。"
            ),
        )

    # enhance_video 是同步阻塞的 subprocess 管线（超分/补帧很耗时），
    # 放线程池执行避免阻塞 FastAPI 事件循环
    try:
        output_path = await asyncio.to_thread(
            enhance_video,
            src_path,
            req.output_path,
            req.scale,
            req.fps_target,
        )
    except (FileNotFoundError, ValueError) as exc:
        # 资产路径/参数问题 → 400
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # ffmpeg/外部工具执行失败 → 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # 创建增强后的新 Asset 记录，关联来源资产
    new_asset = Asset(
        asset_type="video",
        path=output_path,
        filename=Path(output_path).name,
        project_id=None,
        tags=["enhance", "realesrgan", "rife"],
        meta={
            "source_asset_id": req.asset_id,
            "scale": req.scale,
            "fps_target": req.fps_target,
        },
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    return {
        "asset_id": new_asset.id,
        "output_path": output_path,
        "status": "enhanced",
        "scale": req.scale,
        "fps_target": req.fps_target,
    }


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
