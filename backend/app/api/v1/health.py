"""健康检查路由。"""

from datetime import datetime, timezone

from app.core.config import settings
from app.db.session import get_db
from app.schemas.common import HealthResponse
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter()


def _check_redis() -> str:
    """检查 Redis 连通性。用 with 确保 client 关闭，避免连接泄漏。"""
    try:
        import redis

        with redis.from_url(settings.REDIS_URL, socket_connect_timeout=2) as client:
            client.ping()
        return "ok"
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}"


def _check_db(db: Session) -> str:
    """检查数据库连通性。"""
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception as e:  # noqa: BLE001
        return f"error: {type(e).__name__}"


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    """综合健康检查：应用 + 数据库 + Redis。"""
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        db=_check_db(db),
        redis=_check_redis(),
        timestamp=datetime.now(timezone.utc),
    )
