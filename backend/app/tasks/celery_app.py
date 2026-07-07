"""Celery 应用配置。

worker 启动（单进程同时跑任务和定时调度）:
    celery -A app.tasks.celery_app worker --beat --loglevel=info

render_tasks.py 实现生成任务，调用 08_Automation 下现有 Python 脚本
完成 ComfyUI / 云端 API 调用。
"""

from app.core.config import settings
from celery import Celery

celery_app = Celery(
    "shotflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.render_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务级超时与重试策略
    task_time_limit=60 * 30,  # 单任务硬超时 30 分钟
    task_soft_time_limit=60 * 25,  # 软超时 25 分钟，便于正常收尾
    task_acks_late=True,  # 任务执行完才确认，支持断点续跑
    task_reject_on_worker_lost=True,  # worker 崩溃时任务重回队列
    worker_prefetch_multiplier=1,  # 长任务一次只取一个，避免堆积
    # 定时任务：每 60 秒跑一次崩溃恢复，把卡死的 running 任务重置为 pending
    beat_schedule={
        "recover-stuck-tasks": {
            "task": "queue.recover",
            "schedule": 60.0,
        },
    },
)
