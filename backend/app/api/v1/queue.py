"""渲染队列路由 — 提交/查询/重试/取消/统计 + SSE 实时推送。"""

import asyncio
import json

from app.api.deps import get_current_user, get_current_user_from_query, require_queue_write_role
from app.db.session import SessionLocal, get_db
from app.models.user import User
from app.schemas.pipeline import (
    RenderTaskCreate,
    RenderTaskOut,
    RenderTaskStatusOut,
    RenderTaskUpdate,
)
from app.services.queue_service import (
    cancel_task,
    enqueue_task,
    get_task,
    list_tasks,
    queue_stats,
    retry_task,
    update_task,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

router = APIRouter()


@router.get("", response_model=list[RenderTaskOut])
def list_queue(
    task_status: str | None = Query(default=None, alias="status"),
    task_type: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list:
    return list_tasks(
        db, status=task_status, task_type=task_type, project_id=project_id, limit=limit
    )


@router.post("", response_model=RenderTaskOut, status_code=status.HTTP_201_CREATED)
def submit_task(
    payload: RenderTaskCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
):
    return enqueue_task(db, payload)


@router.get("/stats", response_model=dict)
def get_stats(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> dict:
    return queue_stats(db)


@router.get("/{task_id}", response_model=RenderTaskStatusOut)
def get_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    task = get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.post("/{task_id}/retry", response_model=RenderTaskOut)
def retry(
    task_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
):
    task = retry_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.post("/{task_id}/cancel", response_model=RenderTaskOut)
def cancel(
    task_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
):
    task = cancel_task(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.patch("/{task_id}", response_model=RenderTaskOut)
def update_task_priority(
    task_id: int,
    payload: RenderTaskUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
):
    """更新任务属性（目前仅支持优先级调整）。

    已完成/已取消的任务返回原值不改动。
    """
    task = update_task(db, task_id, priority=payload.priority)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return task


@router.get("/stream/events")
async def stream_events(
    current: User = Depends(get_current_user_from_query),
):
    """SSE 端点：每 2 秒推送一次队列状态摘要。

    客户端断开时自动清理（sse-starlette 处理）。
    P3 阶段可升级为 Redis pub/sub 精准推送单任务变更。

    会话治理：每次循环用独立 SessionLocal 短连接，避免单 session 长期占用、
    连接老化与脏读积压；不在签名中注入 db，防止请求级 session 被无限复用。
    """

    async def event_generator():
        while True:
            with SessionLocal() as db:
                stats = queue_stats(db)
            yield {"event": "stats", "data": json.dumps(stats, ensure_ascii=False)}
            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())
