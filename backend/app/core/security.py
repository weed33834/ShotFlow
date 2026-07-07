"""安全工具 — 密码哈希与 JWT 签发/校验。

P0 阶段提供基础实现，P3 阶段接入完整用户认证流程。

直接使用 bcrypt 库（而非 passlib），避免 passlib 1.7.x 与 bcrypt 4.x 的兼容问题。
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from app.core.config import settings
from jose import JWTError, jwt

# bcrypt 算法限制：密码最长 72 字节
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """对明文密码做 bcrypt 哈希。"""
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """校验明文密码与哈希是否匹配。

    任何校验失败（包括损坏的哈希、None 入参）都返回 False，
    让登录流程统一走"用户名或密码错误"分支，避免 500。
    """
    try:
        if not plain or not hashed:
            return False
        pw_bytes = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject: str | int, expires_minutes: Optional[int] = None) -> str:
    """签发 JWT access token。

    payload 含 iat（签发时间），支持"改密后旧 token 失效"逻辑：
    _resolve_user 可校验 iat > user.password_changed_at。
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {"sub": str(subject), "iat": now, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """解码 JWT，返回 subject；失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
