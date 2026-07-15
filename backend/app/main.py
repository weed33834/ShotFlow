"""FastAPI 应用入口。

启动开发服务器:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

生产部署由 docker-compose 中的 backend 服务承担。
"""

import logging
from contextlib import asynccontextmanager

# 导入所有模型，确保 Base.metadata 收集全部表（供 Alembic / create_all 使用）
import app.models  # noqa: F401
from app.api.v1 import api_router
from app.core.config import settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _mask_db_url(url: str) -> str:
    """脱敏数据库 URL，隐藏密码。"""
    if "://" in url and "@" in url:
        scheme = url.split("://")[0]
        rest = url.split("://")[1]
        if ":" in rest.split("@")[0]:
            user = rest.split("@")[0].split(":")[0]
            return f"{scheme}://{user}:***@{rest.split('@')[1]}"
    return url


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动与关闭钩子。"""
    logger.info("启动 %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("数据库: %s", _mask_db_url(settings.DATABASE_URL))
    if settings.SIMULATE_MODE and not settings.DEBUG:
        logger.warning(
            "SIMULATE_MODE=true 且非 DEBUG 模式：所有生成 service 返回模拟结果。"
            "生产 GPU 主机请设置 SIMULATE_MODE=false。"
        )
    yield
    logger.info("关闭 %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AIGC 视频工业化生产流水线 — 后端 API",
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """添加安全 HTTP 头，缓解 MIME 嗅探与点击劫持风险。"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """数据库唯一性/约束冲突：返回 400，不暴露 SQL 细节。"""
    logger.warning("IntegrityError on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=400,
        content={"detail": "数据冲突或违反唯一约束"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理：返回 500 通用信息，完整堆栈写入 logger。"""
    logger.exception("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "内部错误"},
    )


@app.get("/", tags=["root"])
def root() -> dict:
    """根路径，返回服务基本信息。"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_prefix": settings.API_V1_PREFIX,
    }
