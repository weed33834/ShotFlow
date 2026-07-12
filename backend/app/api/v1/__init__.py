"""API v1 路由聚合。"""

from app.api.v1 import (
    assets,
    audio,
    auth,
    case_studies,
    generate,
    health,
    keyframes,
    misc,
    projects,
    queue,
    shots,
    tools,
    videos,
    workflow_configs,
)
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(shots.router, prefix="/shots", tags=["shots"])
api_router.include_router(keyframes.router, prefix="/keyframes", tags=["keyframes"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"])
api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])
api_router.include_router(
    workflow_configs.router, prefix="/workflows-cfg", tags=["workflow-configs"]
)
api_router.include_router(misc.workflow_router, prefix="/workflows", tags=["workflows"])
api_router.include_router(misc.qa_router, prefix="/qa", tags=["qa"])
api_router.include_router(misc.daily_router, prefix="/daily-briefs", tags=["daily-briefs"])
api_router.include_router(case_studies.router, prefix="/case-studies", tags=["case-studies"])
# 第一版：流程文件驱动的能力中台
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
