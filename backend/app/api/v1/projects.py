"""项目路由 — 使用正式 schemas。"""

from app.api.deps import get_current_user, require_queue_write_role
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Project]:
    return list(db.scalars(select(Project).order_by(Project.id.desc())))


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(project, k, v)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
    db.delete(project)
    db.commit()
    return MessageResponse(message=f"项目 {project_id} 已删除")
