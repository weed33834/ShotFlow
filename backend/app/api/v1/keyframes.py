"""关键帧路由 — 含触发生成。"""

from app.api.deps import get_current_user, require_queue_write_role
from app.db.session import get_db
from app.models.production import Keyframe
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.production import KeyframeCreate, KeyframeOut
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[KeyframeOut])
def list_keyframes(
    shot_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Keyframe]:
    stmt = select(Keyframe).order_by(Keyframe.id)
    if shot_id is not None:
        stmt = stmt.where(Keyframe.shot_id == shot_id)
    return list(db.scalars(stmt))


@router.post("", response_model=KeyframeOut, status_code=status.HTTP_201_CREATED)
def create_keyframe(
    payload: KeyframeCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Keyframe:
    kf = Keyframe(**payload.model_dump())
    db.add(kf)
    db.commit()
    db.refresh(kf)
    return kf


@router.get("/{kf_id}", response_model=KeyframeOut)
def get_keyframe(
    kf_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Keyframe:
    kf = db.get(Keyframe, kf_id)
    if not kf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关键帧不存在")
    return kf


@router.delete("/{kf_id}", response_model=MessageResponse)
def delete_keyframe(
    kf_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    kf = db.get(Keyframe, kf_id)
    if not kf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关键帧不存在")
    db.delete(kf)
    db.commit()
    return MessageResponse(message=f"关键帧 {kf_id} 已删除")
