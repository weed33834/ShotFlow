"""生成路由：一句话 → 默认编排器 → 出片（人用 UI 入口）。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.spec import GenerateReq
from app.services.orchestrator import Orchestrator

router = APIRouter(tags=["generate"])


@router.post("")
async def generate(req: GenerateReq, db: Session = Depends(get_db)):
    """接收一句话 + 产出类型，启动编排器（读 flow.sop + 脑补 + 调工具）。"""
    spec_id = await Orchestrator().run(req.nl_prompt, req.output_type, db, req.project_id)
    return {
        "spec_id": spec_id,
        "status": "simulated" if settings.SIMULATE_MODE else "generated",
        "message": "流程文件驱动生成完成（SIMULATE 占位 / 真实出片）",
    }
