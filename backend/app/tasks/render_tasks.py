"""渲染任务定义 — Celery worker 执行入口。

按 task_type 分发到对应 service：
    keyframe                          -> comfyui_service（保持原路径，不涉及 provider 选择）
    video_i2v / video_t2v             -> provider_adapters（extra.provider 优先；缺省时
                                       recommend_provider 按 complexity + HAS_GPU 自动择优）
    kling                             -> kling_service
    tts                               -> audio_service.run_tts_task
    music                             -> audio_service.run_music_task

重试由应用层 mark_failed 控制（按错误分类决定 retryable），Celery 层不做 autoretry，
避免双层计数冲突。acks_late 保证 worker 崩溃时任务不丢。
模拟模式下所有 service 直接返回成功，用于无 GPU 环境联调。
"""

import logging

from app.db.session import SessionLocal
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="render.run",
    bind=True,
    # P5: 去掉 autoretry_for，重试由应用层 mark_failed 全权控制，
    # 按错误分类决定 retryable，避免与 Celery 计数叠加产生语义混乱。
)
def run_render_task(self, task_id: int) -> dict:
    """执行一个渲染任务。

    流程：
        1. 标记 running（含 worker_id 与心跳）
        2. 按 task_type 分发到 service
        3. 成功 -> mark_completed；失败 -> mark_failed（按错误分类决定是否重试）
    """
    # 延迟导入避免循环依赖
    from app.services.queue_service import (
        classify_error,
        mark_completed,
        mark_failed,
        mark_running,
        update_progress,
    )

    db = SessionLocal()
    try:
        task = _get_task(db, task_id)
        if not task:
            logger.error("任务 %s 不存在", task_id)
            return {"task_id": task_id, "status": "not_found"}

        if task.status == "cancelled":
            logger.info("任务 %s 已取消，跳过", task_id)
            return {"task_id": task_id, "status": "cancelled"}

        # 防双执行：已被其他 worker 上锁则直接退出，避免重复执行同一 task_id
        if task.status == "running" and task.worker_id and task.worker_id != self.request.hostname:
            logger.warning(
                "Task %s already running on worker %s, skipping",
                task_id,
                task.worker_id,
            )
            return {"status": "already_running", "task_id": task_id}

        # 已有 checkpoint 说明是断点续跑，标记 running 时保留 checkpoint
        mark_running(db, task_id, checkpoint=task.checkpoint, worker_id=self.request.hostname)
        # mark_running 后立即刷一次进度心跳，避免长任务在 dispatch 内未上报心跳被判僵死
        update_progress(db, task_id, 0)
        logger.info(
            "开始执行任务 %s type=%s worker=%s", task_id, task.task_type, self.request.hostname
        )

        try:
            result = _dispatch(db, task)
            mark_completed(db, task_id, result.get("output_path", ""))
            logger.info("任务 %s 完成", task_id)
            return {"task_id": task_id, "status": "completed", **result}
        except Exception as e:  # noqa: BLE001
            error_class, retryable = classify_error(e)
            mark_failed(db, task_id, str(e), retryable=retryable, error_class=error_class)
            logger.exception("任务 %s 失败(%s): %s", task_id, error_class, e)
            return {
                "task_id": task_id,
                "status": "failed",
                "error_class": error_class,
                "retryable": retryable,
            }
    finally:
        db.close()


def _get_task(db, task_id: int):
    from app.models.pipeline import RenderTask

    return db.get(RenderTask, task_id)


class ProviderFailed(Exception):
    """Provider 执行失败（poll 返回 failed），可回退到次优 provider 重试。

    与其他异常区分：仅此类异常触发回退；get_adapter 抛的 ValueError（未知 provider）
    或网络异常等不回退，直接上抛交由 mark_failed 处理。
    """


def _run_provider_once(adapter, ttype: str, prompt: str, seed: int, extra: dict) -> dict:
    """单次 provider 调用：submit -> poll -> result。

    poll 返回 failed 时抛 ProviderFailed（供回退逻辑捕获）；其余异常直接上抛。
    """
    job_id = adapter.submit(ttype, prompt, seed, extra)
    if adapter.poll(job_id) == "failed":
        raise ProviderFailed(f"provider 任务 {job_id} 执行失败")
    return adapter.result(job_id)


def _dispatch(db, task) -> dict:
    """按 task_type 分发到对应 service。

    video_i2v/video_t2v：
      - extra.provider 优先（显式指定，失败直接抛不回退）；
      - 缺省时基于 complexity + settings.HAS_GPU 调 recommend_provider 自动择优，
        并按 rank_providers 降序队列依次尝试——首选失败回退次优，直至成功或全部失败。
        回退发生时写回 extra._fallback_reason 供事后追溯。
    keyframe 保持走 comfyui_service 原路径（不涉及 provider 选择）。
    """
    from app.core.config import settings
    from app.services.audio_service import run_music_task, run_tts_task
    from app.services.comfyui_service import run_comfyui_task
    from app.services.kling_service import run_kling_task
    from app.services.provider_adapters import get_adapter
    from app.services.provider_scorer import rank_providers, recommend_provider

    ttype = task.task_type
    extra = task.extra or {}
    prompt = task.prompt

    if ttype == "keyframe":
        # keyframe（Flux 角色一致性）保持走 comfyui_service 原路径，不涉及 provider 选择
        return run_comfyui_task(
            task_type=ttype,
            prompt=prompt,
            seed=extra.get("seed", 0),
            extra=extra,
        )
    elif ttype in ("video_i2v", "video_t2v"):
        seed = extra.get("seed", 0)
        if "provider" in extra:
            # 显式 provider：用户明确指定，失败直接抛 RuntimeError 不回退（不擅自换 provider）
            provider = extra["provider"]
            adapter = get_adapter(provider)
            job_id = adapter.submit(ttype, prompt, seed, extra)
            if adapter.poll(job_id) == "failed":
                raise RuntimeError(f"provider {provider} 任务 {job_id} 执行失败")
            return adapter.result(job_id)

        # 自动选择：按评分降序构建候选队列，依次尝试，首选失败回退次优
        complexity = extra.get("complexity", "standard")
        rec = recommend_provider(complexity=complexity, gen_method="auto", has_gpu=settings.HAS_GPU)
        ranked = rank_providers(complexity=complexity, has_gpu=settings.HAS_GPU)
        if not ranked:
            raise RuntimeError("无可用 provider (has_gpu=False 且无云端候选)")

        chosen = rec["recommended"]
        tried: list[str] = []
        last_error: Exception | None = None
        for provider, _score in ranked:
            tried.append(provider)
            # 每次尝试更新 extra.provider 为当前 provider，adapter.submit 透传准确值
            extra = {**extra, "provider": provider, "_provider_source": "auto"}
            try:
                result = _run_provider_once(get_adapter(provider), ttype, prompt, seed, extra)
                # 成功：若发生过回退，记录原因落库供追溯
                if len(tried) > 1:
                    extra = {
                        **extra,
                        "_fallback_reason": (
                            f"首选 {chosen} 失败，回退到 {provider}；已尝试 {tried}"
                        ),
                    }
                task.extra = extra
                db.commit()
                if len(tried) > 1:
                    logger.info(
                        "任务 %s 回退到 provider=%s（首选 %s 失败）",
                        getattr(task, "id", "?"),
                        provider,
                        chosen,
                    )
                else:
                    logger.info(
                        "任务 %s 自动选择 provider=%s (complexity=%s, has_gpu=%s): %s",
                        getattr(task, "id", "?"),
                        provider,
                        complexity,
                        settings.HAS_GPU,
                        rec["reason"],
                    )
                return result
            except ProviderFailed as e:
                last_error = e
                logger.warning(
                    "任务 %s provider %s 失败，尝试下一个候选",
                    getattr(task, "id", "?"),
                    provider,
                )
                continue
        raise RuntimeError(f"所有 provider 均失败，已尝试 {tried}: {last_error}")
    elif ttype == "kling":
        return run_kling_task(
            shot_id=extra.get("shot_id", ""),
            prompt=prompt,
            start_image=extra.get("start_image"),
            end_image=extra.get("end_image"),
        )
    elif ttype == "tts":
        return run_tts_task(
            text=prompt,
            role=extra.get("role", "ava"),
            filename=extra.get("filename", ""),
        )
    elif ttype == "music":
        return run_music_task(
            prompt=prompt,
            title=extra.get("title", ""),
            tags=extra.get("tags", ""),
        )
    else:
        raise ValueError(f"未知任务类型: {ttype}")


@celery_app.task(name="queue.recover")
def recover_stuck_tasks_task() -> dict:
    """定时/启动时任务：崩溃恢复。"""
    from app.services.queue_service import recover_stuck_tasks

    db = SessionLocal()
    try:
        count = recover_stuck_tasks(db)
        return {"recovered": count}
    finally:
        db.close()
