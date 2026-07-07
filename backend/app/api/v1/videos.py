"""视频片段路由。"""

from app.api.deps import get_current_user, require_queue_write_role
from app.db.session import get_db
from app.models.production import VideoClip
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.production import VideoClipCreate, VideoClipOut
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[VideoClipOut])
def list_videos(
    shot_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[VideoClip]:
    stmt = select(VideoClip).order_by(VideoClip.id)
    if shot_id is not None:
        stmt = stmt.where(VideoClip.shot_id == shot_id)
    return list(db.scalars(stmt))


@router.post("", response_model=VideoClipOut, status_code=status.HTTP_201_CREATED)
def create_video(
    payload: VideoClipCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> VideoClip:
    clip = VideoClip(**payload.model_dump())
    db.add(clip)
    db.commit()
    db.refresh(clip)
    return clip


@router.get("/{clip_id}", response_model=VideoClipOut)
def get_video(
    clip_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> VideoClip:
    clip = db.get(VideoClip, clip_id)
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频片段不存在")
    return clip


@router.delete("/{clip_id}", response_model=MessageResponse)
def delete_video(
    clip_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    clip = db.get(VideoClip, clip_id)
    if not clip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="视频片段不存在")
    db.delete(clip)
    db.commit()
    return MessageResponse(message=f"视频片段 {clip_id} 已删除")
