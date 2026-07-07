"""工作流配置 + Provider 评分路由。

工作流配置：读取 workflows.yaml 参数化定义，支持预览参数与注入。
Provider 评分：为镜头推荐最优生成 provider。
"""

from app.api.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.provider_scorer import recommend_provider
from app.services.workflow_config_service import (
    get_default_params,
    get_workflow,
    inject_params,
    list_workflows,
    validate_params,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


@router.get("/configs")
def list_workflow_configs(
    current: User = Depends(get_current_user),
) -> list[dict]:
    """列出所有工作流参数化配置。"""
    return list_workflows()


@router.get("/configs/{name}")
def get_workflow_config(
    name: str,
    current: User = Depends(get_current_user),
) -> dict:
    """获取单个工作流配置及其默认参数。"""
    wf = get_workflow(name)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流配置不存在")
    return {**wf, "defaults": get_default_params(wf)}


class InjectRequest(BaseModel):
    name: str
    params: dict


@router.post("/configs/{name}/inject")
def inject_workflow_params(
    name: str,
    payload: InjectRequest,
    current: User = Depends(get_current_user),
) -> dict:
    """将参数注入工作流 JSON，返回可提交给 ComfyUI 的完整工作流。

    会先校验参数，校验失败返回 422。
    """
    wf = get_workflow(name)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流配置不存在")
    errors = validate_params(wf, payload.params)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="; ".join(errors)
        )
    injected = inject_params(wf, payload.params)
    return {"name": name, "workflow": injected, "param_count": len(payload.params)}


@router.get("/provider/recommend")
def provider_recommend(
    complexity: str = "standard",
    gen_method: str = "wan_i2v",
    has_gpu: bool | None = Query(
        default=None, description="是否本地有 GPU，默认读 settings.HAS_GPU"
    ),
    current: User = Depends(get_current_user),
) -> dict:
    """为镜头推荐最优生成 provider。

    has_gpu 不传时回退到 settings.HAS_GPU，保证推荐结果与实际派发时一致。
    """
    effective_gpu = settings.HAS_GPU if has_gpu is None else has_gpu
    return recommend_provider(complexity=complexity, gen_method=gen_method, has_gpu=effective_gpu)
