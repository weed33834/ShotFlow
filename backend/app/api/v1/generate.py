"""生成路由：一句话 → 默认编排器 → 出片（人用 UI 入口）。"""

import asyncio
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.spec import GenerateReq
from app.services.orchestrator import Orchestrator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generate"])


@router.post("")
async def generate(req: GenerateReq, db: Session = Depends(get_db)):
    """接收一句话 + 产出类型，启动编排器（读 flow.sop + 脑补 + 调工具）。"""
    spec_id = await Orchestrator().run(
        req.nl_prompt,
        req.output_type,
        db,
        req.project_id,
        video_aspect=req.video_aspect,
        voice_name=req.voice_name,
        subtitle_enabled=req.subtitle_enabled,
        bgm_enabled=req.bgm_enabled,
        local_asset_ids=req.local_asset_ids,
        style_preset=req.style_preset,
        scene_template=req.scene_template,
        quality_level=req.quality_level,
        transition=req.transition,
    )
    return {
        "spec_id": spec_id,
        "status": "simulated" if settings.SIMULATE_MODE else "generated",
        "message": "流程文件驱动生成完成（SIMULATE 占位 / 真实出片）",
    }


# ===== 批量生成 =====


class BatchGenerateReq(BaseModel):
    """批量生成请求：同一 prompt 生成 N 个变体。

    每个 variant 用不同的 LLM temperature 产生不同分镜脚本，
    适合"一个主题出多个版本选最优"的场景（对标 MoneyPrinterTurbo 批量生成）。
    """

    nl_prompt: str
    output_type: str = "video"
    count: int = Field(default=3, ge=1, le=10, description="生成变体数量（1-10）")
    project_id: int | None = None
    video_aspect: str = ""
    voice_name: str = ""
    subtitle_enabled: bool = True
    bgm_enabled: bool = True
    local_asset_ids: list[int] = Field(default_factory=list)
    style_preset: str = ""
    scene_template: str = ""
    quality_level: str = "standard"
    transition: str = "fade"


@router.post("/batch")
async def batch_generate(req: BatchGenerateReq, db: Session = Depends(get_db)):
    """批量生成：同一 prompt 生成 count 个变体，返回 spec_id 列表。

    每个 variant 用独立 db session，避免 asyncio.gather 并发时的会话冲突。
    """
    from app.db.session import SessionLocal

    async def _run_one(idx: int) -> dict:
        # 每 variant 独立 session，避免 SQLite/PostgreSQL 并发会话冲突
        variant_db = SessionLocal()
        try:
            spec_id = await Orchestrator().run(
                req.nl_prompt,
                req.output_type,
                variant_db,
                req.project_id,
                video_aspect=req.video_aspect,
                voice_name=req.voice_name,
                subtitle_enabled=req.subtitle_enabled,
                bgm_enabled=req.bgm_enabled,
                local_asset_ids=req.local_asset_ids,
                style_preset=req.style_preset,
                scene_template=req.scene_template,
                quality_level=req.quality_level,
                transition=req.transition,
            )
            return {"spec_id": spec_id, "error": None}
        except Exception as exc:
            logger.warning("variant %d 生成失败: %s", idx, exc)
            variant_db.rollback()
            return {"spec_id": None, "error": str(exc)}
        finally:
            variant_db.close()

    results = await asyncio.gather(*[_run_one(i) for i in range(req.count)])

    return {
        "status": "simulated" if settings.SIMULATE_MODE else "generated",
        "count": len(results),
        "results": list(results),
        "message": f"批量生成 {len(results)} 个变体",
    }
