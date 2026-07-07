#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发用建表脚本 — 直接根据模型创建所有表。

适用于开发/测试环境快速初始化。生产环境请使用 Alembic:
    cd backend && alembic upgrade head

用法:
    cd backend
    python init_db.py            # 仅建表
    python init_db.py --seed     # 建表并写入示例项目与超级用户

超级用户密码通过环境变量 INIT_ADMIN_PASSWORD 注入（推荐）；
未设置时回退到开发占位密码 change-me-now 并打印警告，生产环境必须覆盖。
"""

import argparse
import os
import sys

import app.models  # noqa: F401
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine


def create_tables() -> None:
    """根据模型元数据创建所有表。"""
    Base.metadata.create_all(bind=engine)
    print(f"[OK] 已创建所有表于: {settings.DATABASE_URL}")


def seed() -> None:
    """写入示例数据：超级用户 + 示例项目。"""
    from app.models.project import Project
    from app.models.user import User
    from sqlalchemy import select

    # 密码来源优先级：环境变量 INIT_ADMIN_PASSWORD > 开发占位（打印警告）
    admin_password = os.environ.get("INIT_ADMIN_PASSWORD")
    if admin_password:
        password_source = "INIT_ADMIN_PASSWORD 环境变量"
    else:
        admin_password = "change-me-now"
        password_source = "默认占位（生产必须用 INIT_ADMIN_PASSWORD 覆盖）"
        print(
            "[WARN] 未设置 INIT_ADMIN_PASSWORD 环境变量，使用开发占位密码。"
            "生产部署请通过 -e INIT_ADMIN_PASSWORD=xxx 注入强密码。"
        )

    db = SessionLocal()
    try:
        # 使用 SQLAlchemy 2.0 select 风格，避免 legacy db.query() 的 deprecation warning
        existing_admin = db.execute(
            select(User).where(User.username == "admin")
        ).scalar_one_or_none()
        if not existing_admin:
            db.add(
                User(
                    username="admin",
                    email="admin@shotflow.local",
                    hashed_password=hash_password(admin_password),
                    full_name="管理员",
                    role="admin",
                    is_superuser=True,
                )
            )
            print(f"[OK] 创建超级用户: admin (密码来源: {password_source})")
        else:
            print("[OK] 超级用户 admin 已存在，跳过")

        existing_project = db.execute(select(Project)).first()
        if not existing_project:
            db.add(
                Project(
                    title="奇点回响",
                    subtitle="ShotFlow",
                    status="pre_production",
                    description="AIGC 原创科幻微短剧示例项目。",
                )
            )
            print("[OK] 创建示例项目: 奇点回响")

        db.commit()
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化数据库（开发用）")
    parser.add_argument("--seed", action="store_true", help="写入示例数据")
    args = parser.parse_args()

    create_tables()
    if args.seed:
        seed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
