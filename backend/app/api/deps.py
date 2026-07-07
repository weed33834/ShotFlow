"""API 公共依赖。"""

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session


def _resolve_user(db: Session, token: str | None) -> User:
    """根据 token 解析并返回用户，失败抛 401。"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供有效的认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    username = decode_access_token(token)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌无效或已过期",
        )
    user = db.scalars(select(User).where(User.username == username)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已停用",
        )
    return user


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    """从 Authorization: Bearer <token> 解析当前用户。"""
    token = (
        authorization.split(" ", 1)[1]
        if authorization and authorization.lower().startswith("bearer ")
        else None
    )
    return _resolve_user(db, token)


def get_current_user_from_query(
    db: Session = Depends(get_db),
    token: str | None = Query(default=None),
) -> User:
    """从 query 参数 ?token= 解析当前用户。

    SSE 端点专用：浏览器 EventSource 无法自定义请求头，
    只能把 token 放在 query 里。和 get_current_user 共用同一套校验。

    已知限制（技术债务，暂不处理）：
    - token 进 URL 会被反向代理 access log 记录，存在泄露面。
    - 轻量 ticket 方案（短期 ticket 替长期 token）仍走 query，依旧被 log，收益有限。
    - 彻底解法需改用 cookie 认证或 fetch + ReadableStream（可带 Authorization 头），
      但会重构整个 SSE 链路与前端单例 hook，当前内网部署下可接受。
    """
    return _resolve_user(db, token)


# 有权操作队列写端点（提交/重试/取消/改优先级）的角色
QUEUE_WRITE_ROLES = {"admin", "director", "algo_engineer", "video_operator", "ops", "pm"}


def require_queue_write_role(
    current: User = Depends(get_current_user),
) -> User:
    """限制队列写操作为制作/运维角色，避免普通成员误改他人任务。"""
    if current.is_superuser or current.role in QUEUE_WRITE_ROLES:
        return current
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="当前角色无权操作渲染队列，请联系管理员",
    )


def require_superuser(
    current: User = Depends(get_current_user),
) -> User:
    """限制端点仅超级管理员可访问。

    用于敏感操作（如枚举全部用户邮箱），避免普通登录用户越权。
    """
    if not current.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可执行此操作",
        )
    return current
