"""音频/对白路由。"""

from app.api.deps import get_current_user, require_queue_write_role
from app.db.session import get_db
from app.models.production import Dialogue
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.production import DialogueCreate, DialogueOut
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[DialogueOut])
def list_dialogues(
    shot_id: int | None = Query(default=None),
    role: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Dialogue]:
    stmt = select(Dialogue).order_by(Dialogue.start_time, Dialogue.id)
    if shot_id is not None:
        stmt = stmt.where(Dialogue.shot_id == shot_id)
    if role:
        stmt = stmt.where(Dialogue.role == role)
    return list(db.scalars(stmt))


@router.post("", response_model=DialogueOut, status_code=status.HTTP_201_CREATED)
def create_dialogue(
    payload: DialogueCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Dialogue:
    dlg = Dialogue(**payload.model_dump())
    db.add(dlg)
    db.commit()
    db.refresh(dlg)
    return dlg


@router.get("/{dialogue_id}", response_model=DialogueOut)
def get_dialogue(
    dialogue_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Dialogue:
    dlg = db.get(Dialogue, dialogue_id)
    if not dlg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对白不存在")
    return dlg


@router.delete("/{dialogue_id}", response_model=MessageResponse)
def delete_dialogue(
    dialogue_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    dlg = db.get(Dialogue, dialogue_id)
    if not dlg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对白不存在")
    db.delete(dlg)
    db.commit()
    return MessageResponse(message=f"对白 {dialogue_id} 已删除")
