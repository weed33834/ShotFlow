"""资产路由 — 列表 + 元数据 + 按类型过滤。

资产记录在 assets 表；本路由同时支持扫描磁盘上的实际文件补充元数据。
"""

import os
from pathlib import Path

from app.api.deps import get_current_user
from app.core.config import PROJECT_ROOT
from app.db.session import get_db
from app.models.project import Asset
from app.models.user import User
from app.schemas.project import AssetOut
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()

# 允许扫描的资产目录（相对仓库根）
ASSET_DIRS = {
    "image": ["01_Assets/Characters", "01_Assets/Scenes"],
    "video": ["05_Output/Rough_Cuts", "05_Output/Final"],
    "audio": ["01_Assets/Audio"],
    "doc": ["docs"],
}

# 单次扫描文件数上限，防止数十万文件时 OOM
_SCAN_MAX_LIMIT = 1000


@router.get("", response_model=list[AssetOut])
def list_assets(
    asset_type: str | None = Query(default=None),
    project_id: int | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Asset]:
    """列出资产记录，支持按类型/项目过滤。"""
    stmt = select(Asset).order_by(Asset.id.desc()).limit(limit)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if project_id:
        stmt = stmt.where(Asset.project_id == project_id)
    return list(db.scalars(stmt))


@router.get("/scan/{asset_type}")
def scan_assets(
    asset_type: str,
    limit: int = Query(default=_SCAN_MAX_LIMIT, le=_SCAN_MAX_LIMIT),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> dict:
    """扫描磁盘资产目录，返回文件清单（不入库，仅展示）。

    用于资产画廊页快速浏览实际文件。limit 控制单次返回上限，防止 OOM。
    """
    if asset_type not in ASSET_DIRS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的资产类型: {asset_type}",
        )
    files = []
    for rel_dir in ASSET_DIRS[asset_type]:
        abs_dir = PROJECT_ROOT / rel_dir
        if not abs_dir.exists():
            continue
        for root, _, names in os.walk(abs_dir):
            for name in names:
                # 跳过隐藏文件
                if name.startswith("."):
                    continue
                abs_path = Path(root) / name
                rel = str(abs_path.relative_to(PROJECT_ROOT))
                files.append(
                    {
                        "path": rel,
                        "filename": name,
                        "size": abs_path.stat().st_size,
                        "dir": rel_dir,
                    }
                )
                if len(files) >= limit:
                    return {"asset_type": asset_type, "count": len(files), "files": files}
    return {"asset_type": asset_type, "count": len(files), "files": files}


@router.get("/{asset_id}", response_model=AssetOut)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Asset:
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资产不存在")
    return asset
