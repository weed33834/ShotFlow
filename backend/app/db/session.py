"""数据库引擎与会话工厂。

根据 settings.DATABASE_URL 自动适配 PostgreSQL(生产) 或 SQLite(开发)。
提供 FastAPI 依赖 get_db。
"""

from collections.abc import Generator

from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _build_engine():
    """根据数据库类型构建引擎。"""
    if settings.is_sqlite:
        # SQLite 需要 check_same_thread=False 以便在多线程/异步上下文使用
        return create_engine(
            settings.DATABASE_URL,
            connect_args={"check_same_thread": False},
            future=True,
        )
    # PostgreSQL
    return create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,  # 1 小时回收，避免云数据库 wait_timeout 断连
        pool_size=10,
        max_overflow=20,
        future=True,
    )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话并自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
