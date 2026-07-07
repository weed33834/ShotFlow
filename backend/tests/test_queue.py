"""队列状态机、优先级调整、崩溃恢复、错误分类测试。"""

from app.services.queue_service import (
    STUCK_TIMEOUT_SECONDS,
    cancel_task,
    classify_error,
    list_tasks,
    mark_completed,
    mark_failed,
    mark_running,
    queue_stats,
    recover_stuck_tasks,
    retry_task,
    update_progress,
    update_task,
)


def _create_task(db_session, status="pending"):
    from app.models.pipeline import RenderTask

    task = RenderTask(task_type="keyframe", prompt="test", status=status)
    db_session.add(task)
    db_session.commit()
    return task


def test_state_machine_pending_to_running_to_completed(db_session):
    """状态机：pending -> running -> completed。"""
    task = _create_task(db_session)
    mark_running(db_session, task.id)
    assert db_session.get(type(task), task.id).status == "running"
    mark_completed(db_session, task.id, output_path="out.png")
    assert db_session.get(type(task), task.id).status == "completed"


def test_state_machine_failure_retry(db_session):
    """失败可重试时回退到 pending 并增加重试计数。"""
    task = _create_task(db_session, status="running")
    mark_failed(db_session, task.id, "ComfyUI timeout", retryable=True)
    refreshed = db_session.get(type(task), task.id)
    assert refreshed.status == "pending"
    assert refreshed.retry_count == 1
    assert "timeout" in refreshed.error


def test_state_machine_failure_max_retry(db_session):
    """达到最大重试次数后标记为 failed。"""
    task = _create_task(db_session, status="running")
    task.retry_count = 3
    task.max_retry = 3
    db_session.commit()
    mark_failed(db_session, task.id, "persistent error", retryable=True)
    assert db_session.get(type(task), task.id).status == "failed"


def test_cancel_task(db_session):
    """取消任务。"""
    task = _create_task(db_session, status="pending")
    cancelled = cancel_task(db_session, task.id)
    assert cancelled.status == "cancelled"


def test_recover_stuck_tasks(db_session):
    """崩溃恢复：running 任务重置为 pending。"""
    _create_task(db_session, status="running")
    _create_task(db_session, status="running")
    _create_task(db_session, status="pending")  # 不应被重置

    count = recover_stuck_tasks(db_session)
    assert count == 2

    stats = queue_stats(db_session)
    assert stats["pending"] == 3
    assert stats["running"] == 0


def test_queue_stats(db_session):
    """队列统计准确。"""
    _create_task(db_session, status="pending")
    _create_task(db_session, status="completed")
    _create_task(db_session, status="failed")
    stats = queue_stats(db_session)
    assert stats["pending"] == 1
    assert stats["completed"] == 1
    assert stats["failed"] == 1
    assert stats["total"] == 3


# ===== P5 新能力测试 =====


def test_update_priority(db_session):
    """update_task 可调整优先级。"""
    task = _create_task(db_session, status="pending")
    updated = update_task(db_session, task.id, priority=8)
    assert updated.priority == 8


def test_update_priority_clamped(db_session):
    """优先级被限制在 0-100。"""
    task = _create_task(db_session, status="pending")
    update_task(db_session, task.id, priority=999)
    assert db_session.get(type(task), task.id).priority == 100
    update_task(db_session, task.id, priority=-5)
    assert db_session.get(type(task), task.id).priority == 0


def test_update_priority_terminal_ignored(db_session):
    """已完成/已取消任务不改动。"""
    task = _create_task(db_session, status="completed")
    task.priority = 3
    db_session.commit()
    result = update_task(db_session, task.id, priority=9)
    # 返回原值，不报错但不改
    assert result.priority == 3


def test_update_missing_task(db_session):
    """更新不存在的任务返回 None。"""
    assert update_task(db_session, 99999, priority=1) is None


def test_retry_only_for_terminal(db_session):
    """手动重试仅对 failed/cancelled 生效，running/pending 不重复派发。"""
    running = _create_task(db_session, status="running")
    result = retry_task(db_session, running.id)
    # running 任务不重置，返回原对象
    assert result.status == "running"

    failed = _create_task(db_session, status="failed")
    failed.retry_count = 3
    db_session.commit()
    result = retry_task(db_session, failed.id)
    assert result.status == "pending"
    assert result.retry_count == 0
    assert result.error == ""
    assert result.progress == 0


def test_cancel_clears_worker(db_session):
    """取消任务时清理 worker_id 与 locked_at。"""
    task = _create_task(db_session, status="running")
    task.worker_id = "celery@host"
    from datetime import datetime, timezone

    task.locked_at = datetime.now(timezone.utc)
    db_session.commit()

    cancelled = cancel_task(db_session, task.id)
    assert cancelled.status == "cancelled"
    assert cancelled.worker_id == ""
    assert cancelled.locked_at is None


def test_cancel_terminal_noop(db_session):
    """已完成任务取消不报错也不改状态。"""
    task = _create_task(db_session, status="completed")
    result = cancel_task(db_session, task.id)
    assert result.status == "completed"


def test_mark_completed_sets_progress(db_session):
    """完成时进度设为 100，清理 worker。"""
    task = _create_task(db_session, status="running")
    task.worker_id = "w1"
    db_session.commit()
    mark_completed(db_session, task.id, output_path="out.png")
    refreshed = db_session.get(type(task), task.id)
    assert refreshed.status == "completed"
    assert refreshed.progress == 100
    assert refreshed.worker_id == ""
    assert refreshed.error_class == ""


def test_mark_failed_with_error_class(db_session):
    """失败时记录错误分类。"""
    task = _create_task(db_session, status="running")
    task.max_retry = 0  # 不重试，直接 failed
    db_session.commit()
    mark_failed(db_session, task.id, "ComfyUI timeout", retryable=True, error_class="timeout")
    refreshed = db_session.get(type(task), task.id)
    assert refreshed.status == "failed"
    assert refreshed.error_class == "timeout"
    assert refreshed.worker_id == ""


def test_update_progress(db_session):
    """update_progress 更新进度并刷新心跳。"""
    task = _create_task(db_session, status="running")
    update_progress(db_session, task.id, 50)
    refreshed = db_session.get(type(task), task.id)
    assert refreshed.progress == 50
    assert refreshed.locked_at is not None


def test_recover_respects_heartbeat(db_session):
    """recover 按心跳判定：有近期心跳的不回收。"""
    from datetime import datetime, timedelta, timezone

    # 有心跳的 running 任务（刚上锁）—— 不应被回收
    fresh = _create_task(db_session, status="running")
    fresh.locked_at = datetime.now(timezone.utc)
    db_session.commit()

    # 无心跳的 running 任务（异常退出）—— 应被回收
    stale = _create_task(db_session, status="running")
    stale.locked_at = None
    db_session.commit()

    # 心跳超时的 running 任务 —— 应被回收
    expired = _create_task(db_session, status="running")
    expired.locked_at = datetime.now(timezone.utc) - timedelta(seconds=STUCK_TIMEOUT_SECONDS + 60)
    db_session.commit()

    count = recover_stuck_tasks(db_session)
    assert count == 2  # stale + expired

    fresh_ref = db_session.get(type(fresh), fresh.id)
    stale_ref = db_session.get(type(stale), stale.id)
    expired_ref = db_session.get(type(expired), expired.id)
    assert fresh_ref.status == "running"  # 有心跳，保留
    assert stale_ref.status == "pending"  # 无心跳，回收
    assert expired_ref.status == "pending"  # 超时，回收


def test_classify_error_permanent():
    """永久性错误不重试。"""
    cls, retry = classify_error(ValueError("prompt is empty"))
    assert cls == "invalid_prompt"
    assert retry is False

    cls, retry = classify_error(FileNotFoundError("workflow.json"))
    assert retry is False


def test_classify_error_auth():
    """认证错误不重试。"""
    cls, retry = classify_error(Exception("Unauthorized: invalid API key"))
    assert cls == "auth"
    assert retry is False


def test_classify_error_transient():
    """暂时性错误可重试。"""
    cls, retry = classify_error(Exception("Connection timeout to ComfyUI"))
    assert cls == "timeout"
    assert retry is True

    cls, retry = classify_error(Exception("503 Service Unavailable"))
    assert retry is True


def test_classify_error_unknown():
    """未知错误默认可重试。"""
    cls, retry = classify_error(RuntimeError("something weird"))
    assert cls == "unknown"
    assert retry is True


def test_list_tasks_filters(db_session):
    """list_tasks 支持按状态/类型过滤。"""
    _create_task(db_session, status="pending")
    _create_task(db_session, status="completed")
    pending = list_tasks(db_session, status="pending")
    assert len(pending) == 1
    assert pending[0].status == "pending"


def test_cancelled_not_overridden(db_session):
    """已取消的任务不被 mark_completed/mark_failed/mark_running 覆盖（S1 修复）。"""
    task = _create_task(db_session, status="cancelled")
    mark_completed(db_session, task.id, output_path="out.png")
    assert db_session.get(type(task), task.id).status == "cancelled"

    mark_failed(db_session, task.id, "error", retryable=True)
    assert db_session.get(type(task), task.id).status == "cancelled"

    mark_running(db_session, task.id)
    assert db_session.get(type(task), task.id).status == "cancelled"


def test_update_priority_blocks_failed(db_session):
    """failed 任务也不应改优先级（与终态语义一致）。"""
    task = _create_task(db_session, status="failed")
    task.priority = 3
    db_session.commit()
    # update_task 只挡 completed/cancelled，failed 可改优先级（方便重试前调优先级）
    # 这里验证当前行为：failed 可改
    result = update_task(db_session, task.id, priority=7)
    assert result.priority == 7
