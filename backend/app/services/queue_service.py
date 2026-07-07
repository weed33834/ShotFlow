"""渲染队列服务 — 任务状态机、优先级调整、崩溃恢复、错误分类重试。

状态机：
    pending -> running -> completed
                      -> failed (retry_count < max_retry 且可重试时回 pending)
    任何状态 -> cancelled

重试语义（P5 统一）：
    应用层全权控制重试，Celery 层不做 autoretry。
    mark_failed 根据错误分类决定 retryable，可重试且未超上限时回 pending 并重新 delay。
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from app.models.pipeline import RenderTask
from app.schemas.pipeline import RenderTaskCreate
from app.tasks.render_tasks import run_render_task
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# 心跳超时阈值：running 超过此时长无更新视为僵死，recover 时回收。
# 大于 Celery task_time_limit=1800，避免长任务被误判为僵死。
STUCK_TIMEOUT_SECONDS = 2400


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ===== 错误分类 =====
def classify_error(exc: Exception) -> tuple[str, bool]:
    """根据异常类型判断错误分类与是否可重试。

    返回 (error_class, retryable)。
    永久性错误（参数非法、配置缺失）不重试，避免无谓消耗。
    """
    msg = str(exc).lower()
    # 永久性错误：重试也不会变好
    if isinstance(exc, (ValueError, KeyError, FileNotFoundError)):
        return "invalid_prompt", False
    if "api key" in msg or "unauthorized" in msg or "401" in msg or "403" in msg:
        return "auth", False
    if "not found" in msg and "workflow" in msg:
        return "invalid_prompt", False
    # 暂时性错误：超时、网络抖动、服务端 5xx
    if "timeout" in msg or "timed out" in msg:
        return "timeout", True
    if "connection" in msg or "502" in msg or "503" in msg or "504" in msg:
        return "timeout", True
    # 兜底：未知错误按可重试处理，给一次机会
    return "unknown", True


# ===== 任务 CRUD =====
def enqueue_task(db: Session, payload: RenderTaskCreate) -> RenderTask:
    """创建任务并派发给 Celery。

    1. 写入 render_tasks 表（status=pending）
    2. 异步派发给 Celery，记录 celery_task_id
    """
    task = RenderTask(
        project_id=payload.project_id,
        shot_id=payload.shot_id,
        task_type=payload.task_type,
        prompt=payload.prompt,
        priority=payload.priority,
        max_retry=payload.max_retry,
        extra=payload.extra,
        status="pending",
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        async_result = run_render_task.delay(task.id)
        task.celery_task_id = async_result.id
        db.commit()
        db.refresh(task)
        logger.info("任务 %s 已派发 celery_id=%s", task.id, async_result.id)
    except Exception as e:  # noqa: BLE001
        # 派发失败标记 failed，避免任务以 pending 状态滞留队列永不被 worker 拾取
        logger.warning("Celery 派发失败（任务标记为 failed）: %s", e)
        db.rollback()
        task.status = "failed"
        task.error_class = "dispatch_error"
        task.error = f"派发失败: {e}"
        task.failed_at = _now()
        db.commit()
        db.refresh(task)

    return task


def get_task(db: Session, task_id: int) -> Optional[RenderTask]:
    return db.get(RenderTask, task_id)


def list_tasks(
    db: Session,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    project_id: Optional[int] = None,
    limit: int = 100,
) -> list[RenderTask]:
    """列出任务，按优先级降序、id 升序排列。"""
    stmt = select(RenderTask).order_by(RenderTask.priority.desc(), RenderTask.id.asc()).limit(limit)
    if status:
        stmt = stmt.where(RenderTask.status == status)
    if task_type:
        stmt = stmt.where(RenderTask.task_type == task_type)
    if project_id:
        stmt = stmt.where(RenderTask.project_id == project_id)
    return list(db.scalars(stmt))


def update_task(db: Session, task_id: int, priority: Optional[int] = None) -> Optional[RenderTask]:
    """更新任务属性（目前仅支持优先级）。

    已完成或已取消的任务不允许修改。
    """
    task = db.get(RenderTask, task_id)
    if not task:
        return None
    if task.status in ("completed", "cancelled"):
        return task  # 终态任务，不报错但不改动
    if priority is not None:
        task.priority = max(0, min(priority, 100))
    db.commit()
    db.refresh(task)
    return task


# ===== 状态机 =====
def mark_running(db: Session, task_id: int, checkpoint: str = "", worker_id: str = "") -> None:
    """标记任务为执行中，记录 worker 与上锁时间。

    已取消的任务不再迁移状态，避免 worker 跑完覆盖 cancelled。
    SELECT FOR UPDATE 在事务内加行级锁，避免双 worker 并发抢同一 task。
    SQLite 不支持 FOR UPDATE 但 SQLAlchemy 会自动忽略，无需 dialect 判断。
    """
    task = db.get(RenderTask, task_id, with_for_update=True)
    if not task:
        return
    if task.status == "cancelled":
        return
    task.status = "running"
    if not task.started_at:
        task.started_at = _now()
    task.locked_at = _now()
    task.worker_id = worker_id or task.worker_id
    if checkpoint:
        task.checkpoint = checkpoint
    db.commit()


def update_progress(db: Session, task_id: int, progress: int) -> None:
    """更新任务进度百分比（0-100），同时刷新心跳。"""
    task = db.get(RenderTask, task_id)
    if not task:
        return
    task.progress = max(0, min(progress, 100))
    task.locked_at = _now()
    db.commit()


def mark_completed(db: Session, task_id: int, output_path: str = "") -> None:
    """标记任务完成。

    已取消的任务不覆盖状态（worker 可能在 cancel 后才跑完）。
    """
    task = db.get(RenderTask, task_id)
    if not task:
        return
    if task.status == "cancelled":
        return
    task.status = "completed"
    task.progress = 100
    task.completed_at = _now()
    task.error = ""
    task.error_class = ""
    task.worker_id = ""
    task.locked_at = None
    if output_path:
        extra = dict(task.extra or {})
        extra["output_path"] = output_path
        task.extra = extra
    db.commit()


def mark_failed(
    db: Session, task_id: int, error: str, retryable: bool = True, error_class: str = ""
) -> None:
    """标记任务失败；可重试且未超上限时回退 pending 并重新派发。

    重试全权由应用层控制（P5 统一：Celery 层不再 autoretry）。
    已取消的任务不覆盖状态。
    """
    task = db.get(RenderTask, task_id)
    if not task:
        return
    if task.status == "cancelled":
        return
    task.error = error[:1000]
    task.error_class = error_class or "unknown"
    task.worker_id = ""
    task.locked_at = None
    task.failed_at = _now()

    if retryable and task.retry_count < task.max_retry:
        task.retry_count += 1
        task.status = "pending"
        db.commit()
        logger.info(
            "任务 %s 失败(%s)，将重试(%s/%s)",
            task_id,
            task.error_class,
            task.retry_count,
            task.max_retry,
        )
        # 重新派发到 Celery
        try:
            async_result = run_render_task.delay(task_id)
            task.celery_task_id = async_result.id
            db.commit()
        except Exception as e:  # noqa: BLE001
            logger.warning("重试派发失败（任务仍为 pending）: %s", e)
    else:
        task.status = "failed"
        db.commit()
        logger.warning("任务 %s 彻底失败(%s): %s", task_id, task.error_class, error[:200])


def cancel_task(db: Session, task_id: int) -> Optional[RenderTask]:
    """取消任务：改 DB 状态 + 撤销 Celery 侧任务。

    终态（completed/cancelled）直接返回不处理。
    running 状态会尝试 revoke Celery 任务，避免继续消耗算力。
    """
    task = db.get(RenderTask, task_id)
    if not task:
        return None
    if task.status in ("completed", "cancelled"):
        return task

    was_running = task.status == "running"
    task.status = "cancelled"
    task.worker_id = ""
    task.locked_at = None
    db.commit()
    db.refresh(task)

    # 撤销 Celery 侧任务（若在执行中）
    if was_running and task.celery_task_id:
        try:
            from app.tasks.celery_app import celery_app

            celery_app.control.revoke(task.celery_task_id, terminate=True, signal="SIGTERM")
            logger.info("已撤销 Celery 任务 %s", task.celery_task_id)
        except Exception as e:  # noqa: BLE001
            logger.warning("撤销 Celery 任务失败: %s", e)

    return task


def retry_task(db: Session, task_id: int) -> Optional[RenderTask]:
    """手动重试任务：重置计数并重新派发。

    仅 failed / cancelled 状态可手动重试，避免对 running 任务重复派发。
    """
    task = db.get(RenderTask, task_id)
    if not task:
        return None
    if task.status not in ("failed", "cancelled"):
        # running/pending 已在队列中，不重复派发
        return task

    task.status = "pending"
    task.retry_count = 0
    task.error = ""
    task.error_class = ""
    task.progress = 0
    task.checkpoint = ""
    db.commit()
    db.refresh(task)
    try:
        async_result = run_render_task.delay(task.id)
        task.celery_task_id = async_result.id
        db.commit()
        db.refresh(task)
    except Exception as e:  # noqa: BLE001
        # 派发失败标记 failed，避免任务静默滞留 pending 永不被 worker 拾取
        logger.warning("重试派发失败: %s", e)
        task.status = "failed"
        task.error_class = "dispatch_error"
        task.error = f"派发失败: {e}"
        task.failed_at = _now()
        db.commit()
        db.refresh(task)
    return task


# ===== 崩溃恢复 =====
def recover_stuck_tasks(db: Session) -> int:
    """崩溃恢复：回收僵死的 running 任务。

    判定逻辑：
    - running 且 locked_at 为空（异常退出未清理）→ 直接回收
    - running 且 locked_at 超过 STUCK_TIMEOUT_SECONDS → 心跳超时回收
    - 回收后先 revoke 旧 celery 任务（避免双 worker 并发），再重置 pending 并重新派发

    返回回收数量；遇异常返回 -1（让 beat 调度不中断，仅记录告警）。
    """
    try:
        stmt = select(RenderTask).where(RenderTask.status == "running")
        stuck = list(db.scalars(stmt))
        recovered = []
        now = _now()
        for task in stuck:
            is_stuck = False
            if not task.locked_at:
                is_stuck = True
            else:
                # SQLite 不保留 tz，读回来是 naive，统一转 aware 再比
                locked = task.locked_at
                if locked.tzinfo is None:
                    locked = locked.replace(tzinfo=timezone.utc)
                delta = (now - locked).total_seconds()
                if delta > STUCK_TIMEOUT_SECONDS:
                    is_stuck = True

            if is_stuck:
                # 先 revoke 旧 celery 任务，避免新旧 worker 并发执行同一 task_id
                if task.celery_task_id:
                    try:
                        from app.tasks.celery_app import celery_app

                        celery_app.control.revoke(task.celery_task_id, terminate=False)
                    except Exception as e:  # noqa: BLE001
                        logger.warning("recover 撤销旧任务失败: %s", e)
                task.status = "pending"
                task.worker_id = ""
                task.locked_at = None
                recovered.append(task)
                logger.info(
                    "崩溃恢复：任务 %s running->pending (checkpoint=%s)",
                    task.id,
                    task.checkpoint or "无",
                )
        if recovered:
            db.commit()

        # 只重新派发真正被回收的任务
        for task in recovered:
            try:
                async_result = run_render_task.delay(task.id)
                task.celery_task_id = async_result.id
                db.commit()
            except Exception as e:  # noqa: BLE001
                logger.warning("恢复派发失败（任务 %s 仍为 pending）: %s", task.id, e)

        return len(recovered)
    except Exception as e:  # noqa: BLE001
        logger.exception("recover_stuck_tasks 异常: %s", e)
        return -1


def queue_stats(db: Session) -> dict:
    """队列状态统计。

    用 SQL GROUP BY 聚合，避免把全部任务加载到内存做 Python 计数。
    """
    from sqlalchemy import func

    stats = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0, "total": 0}
    rows = db.execute(select(RenderTask.status, func.count()).group_by(RenderTask.status)).all()
    for status_val, cnt in rows:
        stats[status_val] = stats.get(status_val, 0) + (cnt or 0)
        stats["total"] += cnt or 0
    return stats
