"""镜头路由。"""

from app.api.deps import get_current_user, require_queue_write_role
from app.db.session import get_db
from app.models.production import Shot
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.production import ShotCreate, ShotOut, ShotUpdate
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[ShotOut])
def list_shots(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Shot]:
    stmt = select(Shot).order_by(Shot.order, Shot.id)
    if project_id is not None:
        stmt = stmt.where(Shot.project_id == project_id)
    return list(db.scalars(stmt))


@router.post("", response_model=ShotOut, status_code=status.HTTP_201_CREATED)
def create_shot(
    payload: ShotCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Shot:
    shot = Shot(**payload.model_dump())
    db.add(shot)
    db.commit()
    db.refresh(shot)
    return shot


@router.get("/{shot_id}", response_model=ShotOut)
def get_shot(
    shot_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Shot:
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")
    return shot


@router.patch("/{shot_id}", response_model=ShotOut)
def update_shot(
    shot_id: int,
    payload: ShotUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Shot:
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(shot, k, v)
    db.commit()
    db.refresh(shot)
    return shot


@router.delete("/{shot_id}", response_model=MessageResponse)
def delete_shot(
    shot_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    shot = db.get(Shot, shot_id)
    if not shot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="镜头不存在")
    db.delete(shot)
    db.commit()
    return MessageResponse(message=f"镜头 {shot_id} 已删除")
