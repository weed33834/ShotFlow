"""工作流、质检、日报路由。"""

from app.api.deps import get_current_user, require_queue_write_role
from app.db.session import get_db
from app.models.pipeline import DailyBrief, QaReport, Workflow
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.pipeline import (
    DailyBriefCreate,
    DailyBriefOut,
    QaReportCreate,
    QaReportOut,
    WorkflowCreate,
    WorkflowOut,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

# ===== 工作流 =====
workflow_router = APIRouter()


@workflow_router.get("", response_model=list[WorkflowOut])
def list_workflows(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[Workflow]:
    return list(db.scalars(select(Workflow).order_by(Workflow.id)))


@workflow_router.post("", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
def create_workflow(
    payload: WorkflowCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> Workflow:
    wf = Workflow(**payload.model_dump())
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@workflow_router.get("/{wf_id}", response_model=WorkflowOut)
def get_workflow(
    wf_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> Workflow:
    wf = db.get(Workflow, wf_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    return wf


@workflow_router.delete("/{wf_id}", response_model=MessageResponse)
def delete_workflow(
    wf_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    wf = db.get(Workflow, wf_id)
    if not wf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="工作流不存在")
    db.delete(wf)
    db.commit()
    return MessageResponse(message=f"工作流 {wf_id} 已删除")


# ===== 质检 =====
qa_router = APIRouter()


@qa_router.get("", response_model=list[QaReportOut])
def list_qa_reports(
    shot_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[QaReport]:
    stmt = select(QaReport).order_by(QaReport.id.desc())
    if shot_id is not None:
        stmt = stmt.where(QaReport.shot_id == shot_id)
    stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt))


@qa_router.post("", response_model=QaReportOut, status_code=status.HTTP_201_CREATED)
def create_qa_report(
    payload: QaReportCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> QaReport:
    qa = QaReport(**payload.model_dump())
    db.add(qa)
    db.commit()
    db.refresh(qa)
    return qa


@qa_router.delete("/{qa_id}", response_model=MessageResponse)
def delete_qa_report(
    qa_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    qa = db.get(QaReport, qa_id)
    if not qa:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="质检报告不存在")
    db.delete(qa)
    db.commit()
    return MessageResponse(message=f"质检报告 {qa_id} 已删除")


# ===== 日报 =====
daily_router = APIRouter()


@daily_router.get("", response_model=list[DailyBriefOut])
def list_daily_briefs(
    project_id: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[DailyBrief]:
    stmt = select(DailyBrief).order_by(DailyBrief.brief_date.desc())
    if project_id is not None:
        stmt = stmt.where(DailyBrief.project_id == project_id)
    stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt))


@daily_router.post("", response_model=DailyBriefOut, status_code=status.HTTP_201_CREATED)
def create_daily_brief(
    payload: DailyBriefCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> DailyBrief:
    brief = DailyBrief(**payload.model_dump())
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return brief


@daily_router.delete("/{brief_id}", response_model=MessageResponse)
def delete_daily_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_queue_write_role),
) -> MessageResponse:
    brief = db.get(DailyBrief, brief_id)
    if not brief:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="日报不存在")
    db.delete(brief)
    db.commit()
    return MessageResponse(message=f"日报 {brief_id} 已删除")
