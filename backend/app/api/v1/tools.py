"""工具路由：暴露给外部智能体（WorkBuddy / 元器 / 百炼 / Dify）直接驱动。

这些路由同时是 MCP server 的底层能力来源（见 services/mcp_server.py）。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.spec import (
    AssembleReq,
    GenerateReq,
    SpecOut,
    SpecSaveReq,
    ToolGenerateReq,
    ToolResult,
)
from app.services import tools_service as svc

router = APIRouter(tags=["tools"])


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
