"""用户案例展示区路由 — 公开浏览 + 登录管理。"""

from app.api.deps import require_superuser
from app.db.session import get_db
from app.models.case_study import CaseStudy
from app.models.user import User
from app.schemas.case_study import CaseStudyCreate, CaseStudyOut, CaseStudyUpdate
from app.schemas.common import MessageResponse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[CaseStudyOut])
def public_list(
    tag: str | None = Query(default=None, description="按标签过滤"),
    limit: int = Query(default=50, ge=1, le=200, description="返回数量上限"),
    offset: int = Query(default=0, ge=0, description="偏移量，用于分页"),
    db: Session = Depends(get_db),
) -> list[CaseStudy]:
    """公开列表：仅返回已发布案例，按创建时间倒序。

    支持分页（limit/offset）。标签过滤在 Python 层完成，兼容 SQLite（测试）
    与 PostgreSQL（生产），避免 JSON 包含算子在 SQLite 上的方言差异。
    标签过滤在分页前应用，确保跨页不会漏掉匹配项。
    """
    stmt = (
        select(CaseStudy)
        .where(CaseStudy.status == "published")
        .order_by(CaseStudy.created_at.desc())
    )
    cases = list(db.scalars(stmt))
    if tag:
        cases = [c for c in cases if tag in (c.tags or [])]
    return cases[offset : offset + limit]


@router.get("/admin/list", response_model=list[CaseStudyOut])
def admin_list(
    db: Session = Depends(get_db),
    current: User = Depends(require_superuser),
) -> list[CaseStudy]:
    """管理列表：包含 draft/published/archived 全部状态（仅超级管理员）。"""
    stmt = select(CaseStudy).order_by(CaseStudy.created_at.desc())
    return list(db.scalars(stmt))


@router.get("/{slug}", response_model=CaseStudyOut)
def public_get_by_slug(
    slug: str,
    db: Session = Depends(get_db),
) -> CaseStudy:
    """公开详情：按 slug 查询，仅返回已发布案例。"""
    stmt = select(CaseStudy).where(CaseStudy.slug == slug, CaseStudy.status == "published")
    case = db.scalars(stmt).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    return case


@router.post("", response_model=CaseStudyOut, status_code=status.HTTP_201_CREATED)
def create_case_study(
    payload: CaseStudyCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_superuser),
) -> CaseStudy:
    """创建案例（仅超级管理员）。slug 重复返回 400。"""
    case = CaseStudy(**payload.model_dump())
    db.add(case)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="slug 已存在",
        )
    db.refresh(case)
    return case


@router.patch("/{case_id}", response_model=CaseStudyOut)
def update_case_study(
    case_id: int,
    payload: CaseStudyUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_superuser),
) -> CaseStudy:
    """更新案例（仅超级管理员）。"""
    case = db.get(CaseStudy, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(case, k, v)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="slug 已存在",
        )
    db.refresh(case)
    return case


@router.delete("/{case_id}", response_model=MessageResponse)
def delete_case_study(
    case_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_superuser),
) -> MessageResponse:
    """删除案例（仅超级管理员）。"""
    case = db.get(CaseStudy, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    db.delete(case)
    db.commit()
    return MessageResponse(message=f"案例 {case_id} 已删除")
